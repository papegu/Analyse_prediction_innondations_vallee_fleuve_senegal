"""Complete exploratory and predictive analysis for the Senegal River Valley."""
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

import analyse_exploratoire_modeles as base


ARTICLE_DIR = Path(__file__).resolve().parent
DATA_DIR = ARTICLE_DIR.parent
OUT_DIR = ARTICLE_DIR / "resultats_inondations"
RANDOM_STATE = 42
N_SPATIAL_BLOCKS = 5
MODEL_NAMES = [
    "Prevalence baseline",
    "Balanced logistic regression",
    "Balanced random forest",
    "XGBoost",
    "CatBoost",
]
MODEL_FEATURES = [name for name in base.FEATURES if name != "eau_ref_seche"]


def save_csv(frame: pd.DataFrame, name: str, **kwargs: object) -> None:
    frame.to_csv(OUT_DIR / name, index=False, encoding="utf-8-sig", **kwargs)


def benjamini_hochberg(values: pd.Series) -> np.ndarray:
    p_values = values.to_numpy(dtype=float)
    adjusted = np.full(p_values.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(p_values))
    if not len(valid):
        return adjusted
    order = valid[np.argsort(p_values[valid])]
    ranked = p_values[order] * len(order) / np.arange(1, len(order) + 1)
    adjusted[order] = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1)
    return adjusted


def correlation_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    variables = [*base.FEATURES, "inondation_S1", base.TARGET]
    numeric = frame[variables].apply(pd.to_numeric, errors="coerce")
    pearson_matrix = numeric.corr(method="pearson", min_periods=3)
    spearman_matrix = numeric.corr(method="spearman", min_periods=3)
    pearson_matrix.to_csv(OUT_DIR / "matrice_correlation_pearson.csv", encoding="utf-8-sig")
    spearman_matrix.to_csv(OUT_DIR / "matrice_correlation_spearman.csv", encoding="utf-8-sig")
    fig, axes = plt.subplots(1, 2, figsize=(18, 8), constrained_layout=True)
    for ax, matrix, title in zip(axes, [pearson_matrix, spearman_matrix], ["Pearson r", "Spearman rho"]):
        image = ax.imshow(matrix.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(np.arange(len(matrix.columns)), matrix.columns, rotation=90, fontsize=6)
        ax.set_yticks(np.arange(len(matrix.index)), matrix.index, fontsize=6)
        ax.set_title(title)
    fig.colorbar(image, ax=axes, shrink=0.75, label="Correlation")
    fig.savefig(OUT_DIR / "08_matrices_correlation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    target_rows = []
    for target in ["inondation_S1", base.TARGET]:
        for feature in base.FEATURES:
            pair = numeric[[feature, target]].dropna()
            if len(pair) < 3 or pair[feature].nunique() < 2 or pair[target].nunique() < 2:
                continue
            pearson = pearsonr(pair[feature], pair[target])
            spearman = spearmanr(pair[feature], pair[target])
            target_rows.append({
                "cible": target,
                "variable": feature,
                "n": len(pair),
                "pearson_r": pearson.statistic,
                "pearson_p": pearson.pvalue,
                "spearman_rho": spearman.statistic,
                "spearman_p": spearman.pvalue,
            })
    correlations = pd.DataFrame(target_rows)
    correlations["pearson_q_bh"] = correlations.groupby("cible")["pearson_p"].transform(benjamini_hochberg)
    correlations["spearman_q_bh"] = correlations.groupby("cible")["spearman_p"].transform(benjamini_hochberg)
    save_csv(correlations.sort_values(["cible", "spearman_q_bh", "spearman_p"]),
             "correlations_avec_cibles.csv")

    long_rows = []
    for i, left in enumerate(variables):
        for right in variables[i + 1:]:
            pair = numeric[[left, right]].dropna()
            if len(pair) < 3 or pair[left].nunique() < 2 or pair[right].nunique() < 2:
                continue
            pr = pearsonr(pair[left], pair[right])
            sr = spearmanr(pair[left], pair[right])
            long_rows.append({
                "variable_1": left, "variable_2": right, "n": len(pair),
                "pearson_r": pr.statistic, "pearson_p": pr.pvalue,
                "spearman_rho": sr.statistic, "spearman_p": sr.pvalue,
            })
    all_pairs = pd.DataFrame(long_rows)
    all_pairs["pearson_q_bh"] = benjamini_hochberg(all_pairs["pearson_p"])
    all_pairs["spearman_q_bh"] = benjamini_hochberg(all_pairs["spearman_p"])
    save_csv(all_pairs, "correlations_toutes_variables.csv")

    target_corr = correlations.loc[correlations["cible"] == base.TARGET].copy()
    top = target_corr.assign(abs_rho=lambda x: x["spearman_rho"].abs()).nlargest(12, "abs_rho")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = np.where(top["spearman_rho"] >= 0, "#287c8e", "#d97941")
    ax.barh(top["variable"], top["spearman_rho"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.invert_yaxis()
    ax.set(xlabel="Spearman correlation (rho)", title="Predictor associations with next-period flood label")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "07_correlations_cible.png", dpi=220)
    plt.close(fig)
    return correlations


def assign_spatial_blocks(frame: pd.DataFrame) -> pd.DataFrame:
    sites = frame[["point_id", "lon", "lat"]].drop_duplicates("point_id").copy()
    if sites[["lon", "lat"]].isna().any().any() or len(sites) < N_SPATIAL_BLOCKS:
        raise ValueError("Not enough valid site coordinates for spatial block validation.")
    coordinates = sites[["lon", "lat"]].to_numpy(dtype=float)
    center = coordinates.mean(axis=0)
    scale = coordinates.std(axis=0)
    scale[scale == 0] = 1
    standardized = (coordinates - center) / scale
    sites["bloc_spatial"] = KMeans(
        n_clusters=N_SPATIAL_BLOCKS, random_state=RANDOM_STATE, n_init=20
    ).fit_predict(standardized)
    save_csv(sites.sort_values("point_id"), "points_echantillonnage_blocs.csv")
    return frame.merge(sites[["point_id", "bloc_spatial"]], on="point_id", how="left", validate="many_to_one")


def build_model(name: str, target: pd.Series) -> Pipeline:
    positives = max(int(target.sum()), 1)
    negatives = max(len(target) - positives, 1)
    if name == "Prevalence baseline":
        estimator = DummyClassifier(strategy="prior")
        steps = [("imputer", SimpleImputer(strategy="median")), ("model", estimator)]
    elif name == "Balanced logistic regression":
        steps = [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(
                class_weight="balanced", C=1.0, solver="liblinear", max_iter=1500,
                random_state=RANDOM_STATE,
            )),
        ]
    elif name == "Balanced random forest":
        steps = [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=400, min_samples_leaf=4, max_features="sqrt",
                class_weight="balanced_subsample", n_jobs=4, random_state=RANDOM_STATE,
            )),
        ]
    elif name == "XGBoost":
        steps = [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBClassifier(
                n_estimators=350, max_depth=4, learning_rate=0.04,
                subsample=0.85, colsample_bytree=0.85, min_child_weight=4,
                reg_lambda=2.0, scale_pos_weight=negatives / positives,
                objective="binary:logistic", eval_metric="aucpr", tree_method="hist",
                n_jobs=4, random_state=RANDOM_STATE,
            )),
        ]
    elif name == "CatBoost":
        steps = [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", CatBoostClassifier(
                iterations=350, depth=6, learning_rate=0.04,
                loss_function="Logloss", eval_metric="PRAUC",
                auto_class_weights="Balanced", verbose=False,
                allow_writing_files=False, thread_count=4, random_seed=RANDOM_STATE,
            )),
        ]
    else:
        raise ValueError(f"Unknown model: {name}")
    return Pipeline(steps)


def score_predictions(actual: pd.Series, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    return {
        "precision_seuil_0_5": precision_score(actual, prediction, zero_division=0),
        "rappel_seuil_0_5": recall_score(actual, prediction, zero_division=0),
        "f1_seuil_0_5": f1_score(actual, prediction, zero_division=0),
        "balanced_accuracy_seuil_0_5": balanced_accuracy_score(actual, prediction),
        "roc_auc": roc_auc_score(actual, probability) if actual.nunique() == 2 else np.nan,
        "average_precision": average_precision_score(actual, probability),
        "brier_score": brier_score_loss(actual, probability),
    }


def fit_probability(
    name: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str] | None = None,
) -> np.ndarray:
    features = features or MODEL_FEATURES
    model = build_model(name, train[base.TARGET].astype(int))
    model.fit(train[features], train[base.TARGET].astype(int))
    return model.predict_proba(test[features])[:, 1]


def compare_models(frame: pd.DataFrame) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    eligible = frame.loc[frame[base.TARGET].isin([0, 1])].copy()
    train_history = eligible.loc[eligible["annee"] < 2024].copy()
    temporal_test = eligible.loc[eligible["annee"] == 2024].copy()
    if train_history.empty or temporal_test[base.TARGET].nunique() < 2:
        raise ValueError("Chronological train/test split is empty or has a single test class.")

    spatial_predictions = train_history[["point_id", "annee", "date_debut", "bloc_spatial", base.TARGET]].copy()
    fold_metric_rows = []
    for name in MODEL_NAMES:
        spatial_predictions[f"proba_{name}"] = np.nan
        for block in sorted(train_history["bloc_spatial"].unique()):
            validation = train_history["bloc_spatial"] == block
            fold_train = train_history.loc[~validation]
            fold_valid = train_history.loc[validation]
            probability = fit_probability(name, fold_train, fold_valid)
            spatial_predictions.loc[validation, f"proba_{name}"] = probability
            fold_metric_rows.append({
                "modele": name,
                "bloc_spatial": int(block),
                "n_validation": len(fold_valid),
                "positifs_validation": int(fold_valid[base.TARGET].sum()),
                **score_predictions(fold_valid[base.TARGET].astype(int), probability),
            })

    baseline_spatial_rows = []
    for block in sorted(train_history["bloc_spatial"].unique()):
        validation = train_history["bloc_spatial"] == block
        fold_train = train_history.loc[~validation]
        fold_valid = train_history.loc[validation]
        prior = float(fold_train[base.TARGET].mean())
        site_rate = fold_train.groupby("point_id")[base.TARGET].mean()
        probabilities = {
            "Persistence": fold_valid["inondation_S1"].fillna(prior).to_numpy(dtype=float),
            "Historical site frequency": fold_valid["point_id"].map(site_rate).fillna(prior).to_numpy(dtype=float),
        }
        for baseline, probability in probabilities.items():
            baseline_spatial_rows.append({
                "validation": "spatiale_2019_2023",
                "reference": baseline,
                "bloc_spatial": int(block),
                "n": len(fold_valid),
                **score_predictions(fold_valid[base.TARGET].astype(int), probability),
            })
    save_csv(pd.DataFrame(baseline_spatial_rows), "performances_baselines_spatiales.csv")
    save_csv(spatial_predictions, "predictions_validation_spatiale.csv", date_format="%Y-%m-%d")
    fold_metrics = pd.DataFrame(fold_metric_rows)
    save_csv(fold_metrics, "performances_par_bloc_spatial.csv")
    spatial_metrics = []
    score_names = [
        "precision_seuil_0_5", "rappel_seuil_0_5", "f1_seuil_0_5",
        "balanced_accuracy_seuil_0_5", "roc_auc", "average_precision", "brier_score",
    ]
    for name, rows in fold_metrics.groupby("modele", sort=False):
        summary = {
            "modele": name,
            "n_oof": int(rows["n_validation"].sum()),
            "positifs_oof": int(rows["positifs_validation"].sum()),
            "nombre_blocs": int(rows["bloc_spatial"].nunique()),
        }
        for metric in score_names:
            summary[metric] = float(rows[metric].mean())
            summary[f"{metric}_sd_blocs"] = float(rows[metric].std(ddof=1))
        spatial_metrics.append(summary)
    spatial_performance = pd.DataFrame(spatial_metrics).sort_values("average_precision", ascending=False)
    save_csv(spatial_performance, "performances_validation_spatiale.csv")
    best_name = str(spatial_performance.iloc[0]["modele"])

    temporal_rows = temporal_test[["point_id", "lon", "lat", "annee", "date_debut", "periode",
                                   "bloc_spatial", base.TARGET]].copy()
    temporal_metrics = []
    confusion_rows = []
    final_models: dict[str, Pipeline] = {}
    for name in MODEL_NAMES:
        model = build_model(name, train_history[base.TARGET].astype(int))
        model.fit(train_history[MODEL_FEATURES], train_history[base.TARGET].astype(int))
        probability = model.predict_proba(temporal_test[MODEL_FEATURES])[:, 1]
        temporal_rows[f"proba_{name}"] = probability
        temporal_rows[f"prediction_{name}"] = (probability >= 0.5).astype(int)
        prediction = temporal_rows[f"prediction_{name}"].to_numpy(dtype=int)
        actual = temporal_test[base.TARGET].to_numpy(dtype=int)
        for observed in [0, 1]:
            for predicted in [0, 1]:
                confusion_rows.append({
                    "modele": name,
                    "observation": observed,
                    "prediction": predicted,
                    "n": int(np.sum((actual == observed) & (prediction == predicted))),
                })
        temporal_metrics.append({
            "modele": name,
            "selectionne_par_validation_spatiale": name == best_name,
            "n_entrainement": len(train_history),
            "positifs_entrainement": int(train_history[base.TARGET].sum()),
            "n_test_2024": len(temporal_test),
            "positifs_test_2024": int(temporal_test[base.TARGET].sum()),
            "prevalence_test_pct": float(temporal_test[base.TARGET].mean() * 100),
            **score_predictions(temporal_test[base.TARGET].astype(int), probability),
        })
        if name == best_name:
            final_models[name] = model
        if name == "Balanced random forest":
            rf = model.named_steps["model"]
            importance = pd.DataFrame({"variable": MODEL_FEATURES, "importance_gini": rf.feature_importances_})
            save_csv(importance.sort_values("importance_gini", ascending=False),
                     "importance_variables_random_forest.csv")

    prior = float(train_history[base.TARGET].mean())
    site_rate = train_history.groupby("point_id")[base.TARGET].mean()
    temporal_baselines = {
        "Persistence": temporal_test["inondation_S1"].fillna(prior).to_numpy(dtype=float),
        "Historical site frequency": temporal_test["point_id"].map(site_rate).fillna(prior).to_numpy(dtype=float),
        "Prevalence baseline": np.full(len(temporal_test), prior),
    }
    save_csv(pd.DataFrame([
        {
            "validation": "temporelle_2024",
            "reference": baseline,
            "n": len(temporal_test),
            **score_predictions(temporal_test[base.TARGET].astype(int), probability),
        }
        for baseline, probability in temporal_baselines.items()
    ]), "performances_baselines_2024.csv")

    no_s1_features = [
        feature for feature in MODEL_FEATURES
        if feature not in {"n_images_S1", "S1_VV", "S1_VH", "eau_S1", "eau_ref_seche", "observation_S1_valide"}
    ]
    no_s1_spatial_rows = []
    for block in sorted(train_history["bloc_spatial"].unique()):
        validation = train_history["bloc_spatial"] == block
        fold_train = train_history.loc[~validation]
        fold_valid = train_history.loc[validation]
        probability = fit_probability(best_name, fold_train, fold_valid, no_s1_features)
        no_s1_spatial_rows.append({
            "validation": "spatiale_2019_2023",
            "n": len(fold_valid),
            "bloc_spatial": int(block),
            **score_predictions(fold_valid[base.TARGET].astype(int), probability),
        })
    no_s1_temporal_probability = fit_probability(best_name, train_history, temporal_test, no_s1_features)
    no_s1_rows = [
        {"validation": "spatiale_2019_2023", **{
            metric: float(pd.DataFrame(no_s1_spatial_rows)[metric].mean())
            for metric in ["average_precision", "roc_auc", "brier_score"]
        }},
        {
            "validation": "temporelle_2024",
            **score_predictions(temporal_test[base.TARGET].astype(int), no_s1_temporal_probability),
        },
    ]
    no_s1_spacetime = temporal_test[["point_id", "bloc_spatial", base.TARGET]].copy()
    no_s1_spacetime["probabilite"] = np.nan
    for block in sorted(temporal_test["bloc_spatial"].unique()):
        held_out = temporal_test["bloc_spatial"] == block
        fold_train = train_history.loc[train_history["bloc_spatial"] != block]
        fold_test = temporal_test.loc[held_out]
        probability = fit_probability(best_name, fold_train, fold_test, no_s1_features)
        no_s1_spacetime.loc[held_out, "probabilite"] = probability
    no_s1_rows.append({
        "validation": "espace_temps_2024",
        **score_predictions(no_s1_spacetime[base.TARGET].astype(int),
                            no_s1_spacetime["probabilite"].to_numpy(dtype=float)),
    })
    save_csv(pd.DataFrame(no_s1_rows), "ablation_sans_sentinel1_contemporain.csv")
    save_csv(no_s1_spacetime, "predictions_sans_sentinel1_contemporain_2024.csv")

    temporal_performance = pd.DataFrame(temporal_metrics).sort_values("average_precision", ascending=False)
    save_csv(temporal_performance, "performances_modeles_2024.csv")
    save_csv(temporal_rows, "predictions_test_2024.csv", date_format="%Y-%m-%d")
    save_csv(pd.DataFrame(confusion_rows), "matrices_confusion_2024.csv")

    combined_predictions = temporal_test[["point_id", "bloc_spatial", base.TARGET]].copy()
    combined_predictions["probabilite"] = np.nan
    for block in sorted(temporal_test["bloc_spatial"].unique()):
        held_out_sites = temporal_test["bloc_spatial"] == block
        fold_train = train_history.loc[train_history["bloc_spatial"] != block]
        fold_test = temporal_test.loc[held_out_sites]
        probability = fit_probability(best_name, fold_train, fold_test)
        combined_predictions.loc[held_out_sites, "probabilite"] = probability
    save_csv(combined_predictions, "predictions_generalisation_espace_temps_2024.csv")
    combined_scores = score_predictions(
        combined_predictions[base.TARGET].astype(int),
        combined_predictions["probabilite"].to_numpy(dtype=float),
    )
    combined_result = pd.DataFrame([{
        "modele": best_name,
        "train_annees": "2019-2023",
        "test_annee": 2024,
        "sites_test_inconnus": int(combined_predictions["point_id"].nunique()),
        "blocs_spatiaux": N_SPATIAL_BLOCKS,
        "n_test": len(combined_predictions),
        "positifs_test": int(combined_predictions[base.TARGET].sum()),
        **combined_scores,
    }])
    save_csv(combined_result, "performance_generalisation_espace_temps_2024.csv")

    features_without_reference = [name for name in base.FEATURES if name != "eau_ref_seche"]
    ablation_rows = []
    for label, features in [("All predictors", base.FEATURES),
                            ("Without dry-reference indicator", features_without_reference)]:
        spatial_fold_rows = []
        for block in sorted(train_history["bloc_spatial"].unique()):
            validation = train_history["bloc_spatial"] == block
            fold_train = train_history.loc[~validation]
            fold_valid = train_history.loc[validation]
            probability = fit_probability(best_name, fold_train, fold_valid, features)
            spatial_fold_rows.append(average_precision_score(fold_valid[base.TARGET].astype(int), probability))
        temporal_probability = fit_probability(best_name, train_history, temporal_test, features)
        ablation_rows.append({
            "modele": best_name,
            "ablation": label,
            "n_features": len(features),
            "spatial_oof_average_precision_mean": float(np.mean(spatial_fold_rows)),
            "spatial_oof_average_precision_sd": float(np.std(spatial_fold_rows, ddof=1)),
            "temporal_2024_average_precision": average_precision_score(
                temporal_test[base.TARGET].astype(int), temporal_probability
            ),
            "temporal_2024_roc_auc": roc_auc_score(
                temporal_test[base.TARGET].astype(int), temporal_probability
            ),
        })
    save_csv(pd.DataFrame(ablation_rows), "ablation_reference_seche.csv")

    fig, ax = plt.subplots(figsize=(8, 5))
    metric_names = ["Prevalence baseline", "Balanced logistic regression", "Balanced random forest", "XGBoost", "CatBoost"]
    x = np.arange(len(metric_names))
    width = 0.36
    temporal_lookup = temporal_performance.set_index("modele")
    spatial_lookup = spatial_performance.set_index("modele")
    ax.bar(x - width / 2, [temporal_lookup.loc[n, "average_precision"] for n in metric_names],
           width, label="Temporal hold-out 2024")
    ax.bar(x + width / 2, [spatial_lookup.loc[n, "average_precision"] for n in metric_names],
           width, label="Spatial OOF 2019--2023")
    ax.set_xticks(x, ["Baseline", "Logistic", "Random\nForest", "XGBoost", "CatBoost"])
    ax.set(ylabel="Average precision", title="Model comparison under temporal and spatial validation", ylim=(0, 1))
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "09_comparaison_modeles.png", dpi=220)
    plt.close(fig)
    return temporal_performance, best_name, spatial_performance


def shap_analysis(frame: pd.DataFrame, best_name: str) -> pd.DataFrame:
    train = frame.loc[frame[base.TARGET].isin([0, 1]) & (frame["annee"] < 2024)].copy()
    test = frame.loc[frame[base.TARGET].isin([0, 1]) & (frame["annee"] == 2024)].copy()
    model = build_model(best_name, train[base.TARGET].astype(int))
    model.fit(train[MODEL_FEATURES], train[base.TARGET].astype(int))
    if best_name == "Prevalence baseline":
        warnings.warn("The selected prevalence baseline has no meaningful feature SHAP values.")
        return pd.DataFrame()

    imputer = model.named_steps["imputer"]
    estimator = model.named_steps["model"]
    x_train = imputer.transform(train[MODEL_FEATURES])
    x_test = imputer.transform(test[MODEL_FEATURES])
    if "scale" in model.named_steps:
        x_train = model.named_steps["scale"].transform(x_train)
        x_test = model.named_steps["scale"].transform(x_test)
    feature_names = MODEL_FEATURES
    rng = np.random.default_rng(RANDOM_STATE)
    background_size = min(100, len(x_train))
    explanation_size = min(600, len(x_test))
    background = x_train[rng.choice(len(x_train), size=background_size, replace=False)]
    explain_index = rng.choice(len(x_test), size=explanation_size, replace=False)
    x_explain = x_test[explain_index]
    if best_name == "Balanced logistic regression":
        explainer = shap.LinearExplainer(estimator, background)
    else:
        explainer = shap.TreeExplainer(estimator, data=background)
    raw_values = explainer.shap_values(x_explain, check_additivity=False) if best_name != "Balanced logistic regression" else explainer.shap_values(x_explain)
    if isinstance(raw_values, list):
        shap_values = np.asarray(raw_values[-1])
    else:
        shap_values = np.asarray(raw_values)
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, -1]

    importance = pd.DataFrame({
        "variable": feature_names,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0),
        "mean_shap": shap_values.mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)
    save_csv(importance, "importance_variables_shap.csv")
    selected_rows = test.iloc[explain_index][["point_id", "date_debut", base.TARGET]].reset_index(drop=True)
    shap_frame = pd.DataFrame(shap_values, columns=[f"shap_{name}" for name in feature_names])
    save_csv(pd.concat([selected_rows, shap_frame], axis=1), "valeurs_shap_test_2024.csv", date_format="%Y-%m-%d")

    shap.summary_plot(shap_values, x_explain, feature_names=feature_names,
                      max_display=15, show=False, plot_size=(9, 6))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "10_shap_summary.png", dpi=220, bbox_inches="tight")
    plt.close()
    top_feature = str(importance.iloc[0]["variable"])
    shap.dependence_plot(top_feature, shap_values, x_explain,
                         feature_names=feature_names, interaction_index=None, show=False)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "11_shap_dependance.png", dpi=220, bbox_inches="tight")
    plt.close()
    return importance


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, annual, area_year = base.analyze_input()
    base.analyze_agricultural_exposure()
    base.create_figures(frame, annual, area_year)
    frame = assign_spatial_blocks(frame)
    correlation_analysis(frame)
    temporal_performance, best_name, spatial_performance = compare_models(frame)
    shap_importance = shap_analysis(frame, best_name)

    summary = pd.DataFrame([{
        "n_rows": len(frame),
        "n_sites": frame["point_id"].nunique(),
        "n_years": frame["annee"].nunique(),
        "valid_next_period_labels": int(frame[base.TARGET].notna().sum()),
        "positive_next_period_labels": int(frame[base.TARGET].sum()),
        "positive_rate_pct": float(frame[base.TARGET].mean() * 100),
        "coordinates_constant_within_site": bool(frame.groupby("point_id")[["lon", "lat"]].nunique().max().max() == 1),
        "selected_model_spatial_cv": best_name,
        "selection_metric": "average_precision",
        "spatial_cv_average_precision": float(spatial_performance.set_index("modele").loc[best_name, "average_precision"]),
        "temporal_2024_average_precision": float(temporal_performance.set_index("modele").loc[best_name, "average_precision"]),
        "top_shap_variable": str(shap_importance.iloc[0]["variable"]) if not shap_importance.empty else "not_available",
    }])
    save_csv(summary, "resume_analyse_complete.csv")
    print(f"Rows: {len(frame):,}; sites: {frame['point_id'].nunique():,}")
    print(f"Selected model by spatial OOF average precision: {best_name}")
    print("\nSpatial validation 2019-2023:")
    print(spatial_performance.to_string(index=False))
    print("\nTemporal hold-out 2024:")
    print(temporal_performance.to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()