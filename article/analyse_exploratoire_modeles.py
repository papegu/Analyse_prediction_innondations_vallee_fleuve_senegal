"""EDA and chronological baseline models for Senegal River Valley flood data."""
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ARTICLE_DIR = Path(__file__).resolve().parent
DATA_DIR = ARTICLE_DIR.parent
OUT_DIR = ARTICLE_DIR / "resultats_inondations"
MAIN_CSV = DATA_DIR / "dataset_vfs_ml_2019_2024.csv"
STUDY_ROI_COORDS = [
    [-16.60, 16.35], [-15.50, 16.80], [-14.90, 16.90], [-13.80, 16.45],
    [-13.00, 15.75], [-12.20, 15.20], [-11.90, 14.40], [-12.50, 14.10],
    [-13.20, 15.00], [-14.30, 15.55], [-15.30, 15.70], [-16.00, 15.70],
    [-16.60, 15.85],
]
TARGET = "inondation_S1_suivante"
FEATURES = [
    "lon", "lat", "annee", "mois", "jour_annee", "periode",
    "n_images_S1", "S1_VV", "S1_VH", "eau_S1", "eau_ref_seche",
    "JRC_max_extent", "n_images_S2", "NDVI", "EVI", "MSAVI", "NDWI",
    "n_jours_chirps", "P_10d", "P_max_jour", "P_jours_pluie",
    "P_10d_lag1", "P_10d_cum2", "P_10d_cum3", "P_30d", "P_90d",
    "SPI_30d", "SPI_90d", "observation_S1_valide",
]


def save_csv(frame: pd.DataFrame, name: str, **kwargs: object) -> None:
    frame.to_csv(OUT_DIR / name, index=False, encoding="utf-8-sig", **kwargs)


def analyze_input() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not MAIN_CSV.exists():
        raise FileNotFoundError(f"Main CSV not found: {MAIN_CSV}")
    frame = pd.read_csv(MAIN_CSV, low_memory=False)
    frame.columns = frame.columns.str.strip()
    required = {"point_id", "annee", "date_debut", "periode", "inondation_S1", TARGET}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Required columns missing: {sorted(missing)}")

    frame["date_debut"] = pd.to_datetime(frame["date_debut"], errors="coerce")
    for column in frame.select_dtypes(include="object").columns:
        if column != "point_id":
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    profile = pd.DataFrame({
        "variable": frame.columns,
        "type": [str(frame[c].dtype) for c in frame.columns],
        "n_missing": [int(frame[c].isna().sum()) for c in frame.columns],
        "missing_pct": [round(float(frame[c].isna().mean() * 100), 3) for c in frame.columns],
        "n_unique": [int(frame[c].nunique(dropna=True)) for c in frame.columns],
    })
    save_csv(profile, "profil_variables.csv")
    save_csv(frame.describe(include="all").transpose().reset_index(names="variable"),
             "statistiques_descriptives.csv")

    valid = frame.loc[frame["inondation_S1"].isin([0, 1])].copy()
    next_valid = frame.loc[frame[TARGET].isin([0, 1])].copy()
    global_summary = pd.DataFrame([{
        "lignes": len(frame),
        "points": frame["point_id"].nunique(),
        "annees": frame["annee"].nunique(),
        "periodes_par_annee_max": int(frame.groupby("annee")["periode"].nunique().max()),
        "doublons_point_date": int(frame.duplicated(["point_id", "date_debut"]).sum()),
        "cible_inondation_valide": len(valid),
        "taux_inondation_observations_pct": round(float(valid["inondation_S1"].mean() * 100), 4),
        "cible_suivante_valide": len(next_valid),
        "taux_cible_suivante_pct": round(float(next_valid[TARGET].mean() * 100), 4),
        "cible_suivante_manquante_pct": round(float(frame[TARGET].isna().mean() * 100), 4),
    }])
    save_csv(global_summary, "statistiques_globales.csv")

    annual = next_valid.groupby("annee").agg(
        observations_cible_valides=(TARGET, "size"),
        periodes_inondees_suivantes=(TARGET, "sum"),
        taux_cible_suivante_pct=(TARGET, lambda s: s.mean() * 100),
        points_distincts=("point_id", "nunique"),
    ).reset_index()
    annual["taux_cible_suivante_pct"] = annual["taux_cible_suivante_pct"].round(4)
    save_csv(annual, "statistiques_cible_par_annee.csv")

    period = next_valid.groupby(["annee", "periode", "date_debut"]).agg(
        observations_valides=(TARGET, "size"),
        points_inondes_suivants=(TARGET, "sum"),
        taux_points_inondes_suivants_pct=(TARGET, lambda s: s.mean() * 100),
    ).reset_index().sort_values(["annee", "periode"])
    period["taux_points_inondes_suivants_pct"] = period["taux_points_inondes_suivants_pct"].round(4)
    save_csv(period, "statistiques_cible_par_periode.csv")

    point_frequency = valid.groupby("point_id").agg(
        periodes_valides=("inondation_S1", "size"),
        periodes_inondees=("inondation_S1", "sum"),
        frequence_inondation_pct=("inondation_S1", lambda s: s.mean() * 100),
    ).reset_index()
    coordinates = frame.groupby("point_id")[["lon", "lat"]].first().reset_index()
    point_frequency = point_frequency.merge(coordinates, on="point_id", how="left")
    point_frequency["frequence_inondation_pct"] = point_frequency["frequence_inondation_pct"].round(4)
    save_csv(point_frequency, "frequence_inondations_par_point.csv")

    area_parts = []
    for path in sorted(DATA_DIR.glob("stats_inondations_*.csv")):
        part = pd.read_csv(path)
        if "date_debut" not in part or "superficie_inondee_ha" not in part:
            warnings.warn(f"Skipping unexpected area file: {path.name}")
            continue
        part["date_debut"] = pd.to_datetime(part["date_debut"], errors="coerce")
        part["annee"] = pd.to_numeric(part["annee"], errors="coerce")
        part["superficie_inondee_ha"] = pd.to_numeric(part["superficie_inondee_ha"], errors="coerce")
        area_parts.append(part[["annee", "date_debut", "periode", "n_images_S1", "superficie_inondee_ha"]])
    area_period = pd.concat(area_parts, ignore_index=True) if area_parts else pd.DataFrame()
    if not area_period.empty:
        area_period["n_images_S1"] = pd.to_numeric(area_period["n_images_S1"], errors="coerce")
        area_period.loc[area_period["n_images_S1"].le(0), "superficie_inondee_ha"] = np.nan
        area_period = area_period.sort_values(["annee", "date_debut"])
        save_csv(area_period, "superficie_inondee_par_periode.csv", date_format="%Y-%m-%d")
        area_year = area_period.groupby("annee").agg(
            periodes=("superficie_inondee_ha", "count"),
            superficie_moyenne_par_periode_ha=("superficie_inondee_ha", "mean"),
            superficie_mediane_par_periode_ha=("superficie_inondee_ha", "median"),
            maximum_observe_par_periode_ha=("superficie_inondee_ha", "max"),
            somme_hectares_periodes=("superficie_inondee_ha", "sum"),
        ).reset_index()
        area_year.iloc[:, 1:] = area_year.iloc[:, 1:].round(2)
        save_csv(area_year, "superficie_inondee_resume_annuel.csv")
    else:
        area_year = pd.DataFrame()

    numeric = frame.select_dtypes(include=np.number)
    save_csv(numeric.corr(method="spearman").reset_index(names="variable"), "correlations_spearman.csv")
    return frame, annual, area_year


def analyze_agricultural_exposure() -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "annee", "periode", "date_debut", "n_images_S1",
        "superficie_agricole_inondee_ha", "superficie_agricole_observee_ha",
    }
    annual_parts = []
    for path in sorted(DATA_DIR.glob("impact_agricole_inondations_*.csv")):
        part = pd.read_csv(path, low_memory=False)
        missing = required - set(part.columns)
        if missing:
            warnings.warn(f"Skipping {path.name}; missing columns: {sorted(missing)}")
            continue
        part = part.copy()
        for column in required - {"date_debut"}:
            part[column] = pd.to_numeric(part[column], errors="coerce")
        part["date_debut"] = pd.to_datetime(part["date_debut"], errors="coerce")
        annual_parts.append(part)

    if not annual_parts:
        warnings.warn("No usable annual agricultural-exposure exports were found.")
        return pd.DataFrame(), pd.DataFrame()

    exposure = pd.concat(annual_parts, ignore_index=True)
    exposure = exposure.sort_values(["annee", "periode"])
    if exposure.duplicated(["annee", "periode"]).any():
        raise ValueError("Agricultural exports contain duplicate year-period rows.")

    valid_radar = exposure["n_images_S1"].gt(0)
    exposure.loc[~valid_radar, [
        "superficie_agricole_inondee_ha", "superficie_agricole_observee_ha",
    ]] = np.nan
    observed_area = exposure["superficie_agricole_observee_ha"]
    exposure["pourcentage_surface_agricole_touchee_recalcule"] = np.where(
        observed_area.gt(0),
        exposure["superficie_agricole_inondee_ha"] / observed_area * 100,
        np.nan,
    )
    save_csv(exposure, "exposition_agricole_par_periode.csv", date_format="%Y-%m-%d")

    annual_rows = []
    for year, rows in exposure.groupby("annee", sort=True):
        valid = rows.loc[rows["n_images_S1"].gt(0)]
        observed = valid["superficie_agricole_observee_ha"].sum(min_count=1)
        flooded = valid["superficie_agricole_inondee_ha"].sum(min_count=1)
        annual_rows.append({
            "annee": int(year),
            "periodes_total": int(len(rows)),
            "periodes_avec_image_S1": int(len(valid)),
            "surface_agricole_inondee_moyenne_ha": valid["superficie_agricole_inondee_ha"].mean(),
            "surface_agricole_inondee_max_ha": valid["superficie_agricole_inondee_ha"].max(),
            "somme_hectares_periodes_inondes": flooded,
            "surface_agricole_observee_moyenne_ha": valid["superficie_agricole_observee_ha"].mean(),
            "pourcentage_agricole_touche_pondere": flooded / observed * 100 if observed > 0 else np.nan,
        })
    annual_exposure = pd.DataFrame(annual_rows)
    save_csv(annual_exposure, "exposition_agricole_resume_annuel.csv")
    analyze_rice_loss_scenarios()

    if not annual_exposure.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        years = annual_exposure["annee"].astype(int)
        ax.plot(years, annual_exposure["surface_agricole_inondee_moyenne_ha"],
                marker="o", color="#287c8e", label="Mean per valid period")
        ax.plot(years, annual_exposure["surface_agricole_inondee_max_ha"],
                marker="s", color="#d97941", label="Maximum valid period")
        ax.set(xlabel="Year", ylabel="Potentially inundated cropland (ha)",
               title="Mapped cropland exposure by year")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(OUT_DIR / "12_exposition_agricole.png", dpi=220)
        plt.close(fig)

    return exposure, annual_exposure


def analyze_rice_loss_scenarios() -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = pd.DataFrame([
        {"scenario": "Optimiste (hypothese)", "surface_affectee_ha": 1500,
         "rendement_t_ha": 4.4, "prix_paddy_fcfa_t": 128000, "coefficient_destruction": 0.25},
        {"scenario": "Central (hypothese)", "surface_affectee_ha": 1500,
         "rendement_t_ha": 5.5, "prix_paddy_fcfa_t": 160000, "coefficient_destruction": 0.50},
        {"scenario": "Pessimiste (hypothese)", "surface_affectee_ha": 1500,
         "rendement_t_ha": 6.6, "prix_paddy_fcfa_t": 192000, "coefficient_destruction": 1.00},
        {"scenario": "Reference, destruction totale", "surface_affectee_ha": 1500,
         "rendement_t_ha": 5.5, "prix_paddy_fcfa_t": 160000, "coefficient_destruction": 1.00},
    ])
    scenarios["production_perdue_t"] = (
        scenarios["surface_affectee_ha"]
        * scenarios["rendement_t_ha"]
        * scenarios["coefficient_destruction"]
    )
    scenarios["perte_brute_fcfa"] = (
        scenarios["production_perdue_t"] * scenarios["prix_paddy_fcfa_t"]
    )
    scenarios["production_perdue_t"] = scenarios["production_perdue_t"].round(2)
    scenarios["perte_brute_fcfa"] = scenarios["perte_brute_fcfa"].round().astype("int64")
    save_csv(scenarios, "simulation_pertes_riz_scenarios.csv")

    sensitivity_rows = []
    sensitivity_cases = [
        ("rendement_t_ha", [4.4, 5.5, 6.6], 5.5, 160000, 0.50),
        ("prix_paddy_fcfa_t", [128000, 160000, 192000], 5.5, 160000, 0.50),
        ("coefficient_destruction", [0.25, 0.50, 1.00], 5.5, 160000, 0.50),
    ]
    for parameter, values, base_yield, base_price, base_damage in sensitivity_cases:
        for value in values:
            yield_rate = value if parameter == "rendement_t_ha" else base_yield
            price = value if parameter == "prix_paddy_fcfa_t" else base_price
            damage = value if parameter == "coefficient_destruction" else base_damage
            lost_production = 1500 * yield_rate * damage
            sensitivity_rows.append({
                "parametre_varie": parameter,
                "valeur_testee": value,
                "surface_affectee_ha_hypothetique": 1500,
                "rendement_t_ha": yield_rate,
                "prix_paddy_fcfa_t": price,
                "coefficient_destruction": damage,
                "production_perdue_t": lost_production,
                "perte_brute_fcfa": lost_production * price,
            })
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity["production_perdue_t"] = sensitivity["production_perdue_t"].round(2)
    sensitivity["perte_brute_fcfa"] = sensitivity["perte_brute_fcfa"].round().astype("int64")
    save_csv(sensitivity, "sensibilite_pertes_riz.csv")
    return scenarios, sensitivity


def create_figures(frame: pd.DataFrame, annual: pd.DataFrame, area_year: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "figure.dpi": 150})

    missing = frame.isna().mean().mul(100).sort_values(ascending=False).head(18).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    missing.plot.barh(ax=ax, color="#287c8e")
    ax.set(xlabel="Missing values (%)", ylabel="", title="Data completeness by variable")
    ax.set_xlim(0, 105)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_missingness.png", dpi=220)
    plt.close(fig)

    if not area_year.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(area_year["annee"].astype(int), area_year["superficie_moyenne_par_periode_ha"],
                marker="o", color="#287c8e", label="Mean per period")
        ax.plot(area_year["annee"].astype(int), area_year["maximum_observe_par_periode_ha"],
                marker="s", color="#d97941", label="Maximum period")
        ax.set(xlabel="Year", ylabel="Mapped inundated area (ha)",
               title="Period-level inundated area by year")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(OUT_DIR / "02_superficie_annuelle.png", dpi=220)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    for year, rows in frame.groupby("annee"):
        rows = rows.groupby("periode")["inondation_S1_suivante"].mean().dropna()
        ax.plot(rows.index, rows.values * 100, marker="o", markersize=3, label=str(int(year)))
    ax.set(xlabel="Ten-day period", ylabel="Positive next-period labels (%)",
           title="Next-period inundation label prevalence")
    ax.legend(ncol=3, frameon=False, title="Year")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_frequence_temporelle.png", dpi=220)
    plt.close(fig)

    points = frame.loc[frame["inondation_S1"].isin([0, 1])].groupby("point_id").agg(
        lon=("lon", "first"), lat=("lat", "first"), freq=("inondation_S1", "mean")
    ).reset_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    scatter = ax.scatter(points["lon"], points["lat"], c=points["freq"] * 100,
                         cmap="YlOrRd", s=28, edgecolors="none")
    fig.colorbar(scatter, ax=ax, label="Observed inundated periods (%)")
    ax.set(xlabel="Longitude", ylabel="Latitude", title="Inundation frequency at sampled points")
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "04_frequence_spatiale_points.png", dpi=220)
    plt.close(fig)

    sites = frame[["point_id", "lon", "lat"]].drop_duplicates("point_id").dropna()
    if not sites.empty:
        roi = np.asarray(STUDY_ROI_COORDS, dtype=float)
        figure, ax = plt.subplots(figsize=(7.5, 6))
        ax.fill(roi[:, 0], roi[:, 1], color="#e7eee8", edgecolor="#52695b",
                linewidth=1.2, label="Project analysis ROI")
        ax.scatter(sites["lon"], sites["lat"], s=13, color="#c65d3a",
                   edgecolors="white", linewidths=0.25, label=f"Sample sites (n={len(sites)})")
        ax.set_xlim(roi[:, 0].min() - 0.2, roi[:, 0].max() + 0.2)
        ax.set_ylim(roi[:, 1].min() - 0.2, roi[:, 1].max() + 0.2)
        ax.set_aspect(1 / np.cos(np.deg2rad(sites["lat"].median())), adjustable="box")
        ax.set(xlabel="Longitude (degrees)", ylabel="Latitude (degrees)",
               title="Senegal River Valley study ROI and sampled sites")
        ax.grid(color="#8b948e", alpha=0.25, linewidth=0.5)
        ax.legend(frameon=False, loc="lower left")
        ax.annotate("N", xy=(0.93, 0.88), xytext=(0.93, 0.76), xycoords="axes fraction",
                ha="center", arrowprops={"arrowstyle": "-|>", "color": "#303a33"})
        scale_km = 50
        scale_degrees = scale_km / (111.32 * np.cos(np.deg2rad(sites["lat"].median())))
        scale_x = roi[:, 0].min() + 0.35
        scale_y = roi[:, 1].min() + 0.3
        ax.plot([scale_x, scale_x + scale_degrees], [scale_y, scale_y],
                color="#303a33", linewidth=2)
        ax.text(scale_x + scale_degrees / 2, scale_y + 0.08, f"{scale_km} km",
                ha="center", va="bottom", fontsize=8)
        figure.tight_layout()
        figure.savefig(OUT_DIR / "13_zone_etude_sites.png", dpi=240, bbox_inches="tight")
        plt.close(figure)

    if not area_year.empty:
        area_period = pd.concat(
            [pd.read_csv(p, parse_dates=["date_debut"]) for p in sorted(DATA_DIR.glob("stats_inondations_*.csv"))],
            ignore_index=True,
        )
        area_period["n_images_S1"] = pd.to_numeric(area_period["n_images_S1"], errors="coerce")
        area_period.loc[area_period["n_images_S1"].le(0), "superficie_inondee_ha"] = np.nan
        fig, ax = plt.subplots(figsize=(9, 4))
        for year, rows in area_period.groupby("annee"):
            ax.plot(rows["periode"], rows["superficie_inondee_ha"], marker="o", markersize=2, label=str(year))
        ax.set(xlabel="Ten-day period", ylabel="Mapped inundated area (ha)",
               title="Period-level mapped inundated area")
        ax.legend(ncol=3, frameon=False, title="Year")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "05_superficie_par_periode.png", dpi=220)
        plt.close(fig)


def evaluate_models(frame: pd.DataFrame) -> pd.DataFrame:
    missing_features = set(FEATURES) - set(frame.columns)
    if missing_features:
        raise ValueError(f"Predictor columns missing: {sorted(missing_features)}")
    eligible = frame.loc[frame[TARGET].isin([0, 1])].copy()
    train = eligible.loc[eligible["annee"] < 2024]
    test = eligible.loc[eligible["annee"] == 2024]
    if train.empty or test.empty or test[TARGET].nunique() < 2:
        raise ValueError("Chronological train/test split is empty or the test target has one class.")

    x_train, y_train = train[FEATURES], train[TARGET].astype(int)
    x_test, y_test = test[FEATURES], test[TARGET].astype(int)
    candidates = {
        "Prevalence baseline": make_pipeline(
            SimpleImputer(strategy="median"), DummyClassifier(strategy="prior")
        ),
        "Balanced logistic regression": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            LogisticRegression(class_weight="balanced", solver="liblinear", max_iter=1000, random_state=42),
        ),
        "Balanced random forest": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RandomForestClassifier(
                n_estimators=300, min_samples_leaf=5, class_weight="balanced_subsample",
                n_jobs=-1, random_state=42,
            ),
        ),
    }

    metrics = []
    prediction_rows = test[["point_id", "lon", "lat", "annee", "date_debut", "periode", TARGET]].copy()
    prediction_rows = prediction_rows.rename(columns={TARGET: "observation_reelle"})
    confusion_rows = []
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        probability = model.predict_proba(x_test)[:, 1]
        predicted = (probability >= 0.5).astype(int)
        metrics.append({
            "modele": name,
            "n_entrainement": len(train),
            "positifs_entrainement": int(y_train.sum()),
            "n_test_2024": len(test),
            "positifs_test": int(y_test.sum()),
            "prevalence_test_pct": round(float(y_test.mean() * 100), 4),
            "seuil_classification": 0.5,
            "precision": precision_score(y_test, predicted, zero_division=0),
            "rappel": recall_score(y_test, predicted, zero_division=0),
            "f1": f1_score(y_test, predicted, zero_division=0),
            "balanced_accuracy": balanced_accuracy_score(y_test, predicted),
            "roc_auc": roc_auc_score(y_test, probability),
            "average_precision": average_precision_score(y_test, probability),
            "brier_score": brier_score_loss(y_test, probability),
        })
        slug = "baseline" if name.startswith("Prevalence") else "logistic" if name.startswith("Balanced logistic") else "random_forest"
        prediction_rows[f"proba_{slug}"] = probability
        prediction_rows[f"prediction_{slug}"] = predicted
        matrix = confusion_matrix(y_test, predicted, labels=[0, 1])
        for actual in [0, 1]:
            for predicted_value in [0, 1]:
                confusion_rows.append({"modele": name, "observation": actual,
                                       "prediction": predicted_value,
                                       "n": int(matrix[actual, predicted_value])})

        if name == "Balanced random forest":
            fitted_imputer = model.named_steps["simpleimputer"]
            fitted_rf = model.named_steps["randomforestclassifier"]
            feature_names = fitted_imputer.get_feature_names_out(FEATURES)
            importance = pd.DataFrame({"variable": feature_names,
                                       "importance_gini": fitted_rf.feature_importances_})
            save_csv(importance.sort_values("importance_gini", ascending=False),
                     "importance_variables_random_forest.csv")

    performance = pd.DataFrame(metrics)
    save_csv(performance, "performances_modeles_2024.csv")
    save_csv(prediction_rows, "predictions_test_2024.csv", date_format="%Y-%m-%d")
    save_csv(pd.DataFrame(confusion_rows), "matrices_confusion_2024.csv")

    fig, ax = plt.subplots(figsize=(7, 4))
    for name, model in candidates.items():
        probability = model.predict_proba(x_test)[:, 1]
        precision, recall, _ = precision_recall_curve(y_test, probability)
        ap = average_precision_score(y_test, probability)
        ax.plot(recall, precision, label=f"{name} (AP={ap:.3f})")
    ax.axhline(y_test.mean(), color="#777777", linestyle="--", linewidth=1,
               label=f"Test prevalence ({y_test.mean():.3f})")
    ax.set(xlabel="Recall", ylabel="Precision", title="Precision-recall curves (2024 hold-out)",
           xlim=(0, 1), ylim=(0, 1))
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "06_modeles_precision_rappel_2024.png", dpi=220)
    plt.close(fig)
    return performance


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame, annual, area_year = analyze_input()
    analyze_agricultural_exposure()
    create_figures(frame, annual, area_year)
    performance = evaluate_models(frame)
    print(f"Input: {MAIN_CSV}")
    print(f"Output: {OUT_DIR}")
    print(f"Rows: {len(frame):,}; points: {frame['point_id'].nunique():,}")
    print(performance.to_string(index=False))


if __name__ == "__main__":
    main()