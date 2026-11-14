"""Evaluate a buffered spatial hold-out using the existing site blocks."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
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


ARTICLE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ARTICLE_DIR.parent
RESULTS_DIR = ARTICLE_DIR / "resultats_inondations"
DATA_PATH = PROJECT_DIR / "dataset_vfs_ml_2019_2024.csv"
BLOCKS_PATH = RESULTS_DIR / "points_echantillonnage_blocs.csv"
FOLD_OUTPUT_PATH = RESULTS_DIR / "validation_spatiale_buffer_par_bloc.csv"
SUMMARY_OUTPUT_PATH = RESULTS_DIR / "validation_spatiale_buffer_resume.csv"
TARGET = "inondation_S1_suivante"
CURRENT_LABEL = "inondation_S1"
RANDOM_STATE = 42
EARTH_RADIUS_M = 6_371_008.8
BUFFER_QUANTILE = 0.90
MODEL_FEATURES = [
    "lon", "lat", "annee", "mois", "jour_annee", "periode",
    "n_images_S1", "S1_VV", "S1_VH", "eau_S1",
    "JRC_max_extent", "n_images_S2", "NDVI", "EVI", "MSAVI", "NDWI",
    "n_jours_chirps", "P_10d", "P_max_jour", "P_jours_pluie",
    "P_10d_lag1", "P_10d_cum2", "P_10d_cum3", "P_30d", "P_90d",
    "SPI_30d", "SPI_90d", "observation_S1_valide",
]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Main dataset not found: {DATA_PATH}")
    if not BLOCKS_PATH.is_file():
        raise FileNotFoundError(
            f"Spatial block assignments not found: {BLOCKS_PATH}. "
            "Run article/analyse_complete.py first."
        )

    frame = pd.read_csv(DATA_PATH, low_memory=False)
    frame.columns = frame.columns.str.strip()
    blocks = pd.read_csv(BLOCKS_PATH)
    blocks.columns = blocks.columns.str.strip()

    required_data = {
        "point_id", "annee", "lon", "lat", CURRENT_LABEL, TARGET, *MODEL_FEATURES
    }
    missing_data = required_data - set(frame.columns)
    if missing_data:
        raise ValueError(f"Required dataset columns missing: {sorted(missing_data)}")
    required_blocks = {"point_id", "lon", "lat", "bloc_spatial"}
    missing_blocks = required_blocks - set(blocks.columns)
    if missing_blocks:
        raise ValueError(f"Required block columns missing: {sorted(missing_blocks)}")
    if frame["point_id"].isna().any() or blocks["point_id"].isna().any():
        raise ValueError("Site identifiers cannot be missing.")
    if blocks["point_id"].duplicated().any():
        raise ValueError("The spatial block file contains duplicate site identifiers.")

    for column in set(MODEL_FEATURES) | {TARGET, CURRENT_LABEL, "annee"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    coordinates = frame.groupby("point_id")[["lon", "lat"]].nunique(dropna=False)
    if coordinates.gt(1).any().any():
        raise ValueError("Site coordinates are not constant within point_id.")
    observed_sites = set(frame["point_id"].unique())
    block_sites = set(blocks["point_id"].unique())
    if observed_sites != block_sites:
        raise ValueError("Block assignments do not match the dataset's site identifiers.")

    site_coordinates = (
        frame[["point_id", "lon", "lat"]]
        .drop_duplicates("point_id")
        .set_index("point_id")
        .sort_index()
    )
    saved_coordinates = (
        blocks.set_index("point_id")[["lon", "lat"]]
        .sort_index()
        .apply(pd.to_numeric, errors="coerce")
    )
    if not np.allclose(
        site_coordinates[["lon", "lat"]].to_numpy(),
        saved_coordinates[["lon", "lat"]].to_numpy(),
        equal_nan=False,
    ):
        raise ValueError("Saved block coordinates differ from the main dataset.")

    frame = frame.merge(
        blocks[["point_id", "bloc_spatial"]],
        on="point_id",
        how="left",
        validate="many_to_one",
    )
    if frame["bloc_spatial"].isna().any():
        raise ValueError("Some observations have no spatial block assignment.")
    return frame, blocks


def haversine_matrix(coordinates: np.ndarray) -> np.ndarray:
    latitude = np.radians(coordinates[:, 1])
    longitude = np.radians(coordinates[:, 0])
    delta_latitude = latitude[:, None] - latitude[None, :]
    delta_longitude = longitude[:, None] - longitude[None, :]
    haversine = (
        np.sin(delta_latitude / 2) ** 2
        + np.cos(latitude[:, None])
        * np.cos(latitude[None, :])
        * np.sin(delta_longitude / 2) ** 2
    )
    distances = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(haversine, 0, 1)))
    np.fill_diagonal(distances, np.inf)
    return distances


def score_predictions(actual: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    predicted = (probability >= 0.5).astype(int)
    return {
        "precision_seuil_0_5": precision_score(actual, predicted, zero_division=0),
        "rappel_seuil_0_5": recall_score(actual, predicted, zero_division=0),
        "f1_seuil_0_5": f1_score(actual, predicted, zero_division=0),
        "balanced_accuracy_seuil_0_5": balanced_accuracy_score(actual, predicted),
        "roc_auc": roc_auc_score(actual, probability),
        "average_precision": average_precision_score(actual, probability),
        "brier_score": brier_score_loss(actual, probability),
    }


def fit_random_forest(
    train: pd.DataFrame, test: pd.DataFrame
) -> np.ndarray:
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=4,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=4,
            random_state=RANDOM_STATE,
        )),
    ])
    model.fit(train[MODEL_FEATURES], train[TARGET].astype(int))
    return model.predict_proba(test[MODEL_FEATURES])[:, 1]


def main() -> None:
    frame, blocks = load_inputs()
    sites = blocks.sort_values("point_id").reset_index(drop=True)
    distances = haversine_matrix(sites[["lon", "lat"]].to_numpy(dtype=float))
    nearest_neighbor_m = distances.min(axis=1)
    buffer_m = float(np.quantile(nearest_neighbor_m, BUFFER_QUANTILE, method="nearest"))

    eligible = frame.loc[
        frame[TARGET].isin([0, 1]) & frame["annee"].between(2019, 2023)
    ].copy()
    fold_rows: list[dict[str, float | int | str]] = []
    block_values = sorted(sites["bloc_spatial"].unique())

    for block in block_values:
        test_sites = sites.loc[sites["bloc_spatial"] == block]
        candidate_train_sites = sites.loc[sites["bloc_spatial"] != block]
        test_site_indices = test_sites.index.to_numpy()
        train_site_indices = candidate_train_sites.index.to_numpy()
        nearest_test_distance = distances[np.ix_(train_site_indices, test_site_indices)].min(axis=1)
        retained = nearest_test_distance > buffer_m
        train_sites = candidate_train_sites.loc[retained]
        excluded_sites = candidate_train_sites.loc[~retained]

        test_ids = set(test_sites["point_id"])
        train_ids = set(train_sites["point_id"])
        train = eligible.loc[eligible["point_id"].isin(train_ids)].copy()
        test = eligible.loc[eligible["point_id"].isin(test_ids)].copy()
        if train[TARGET].nunique() != 2 or test[TARGET].nunique() != 2:
            raise ValueError(
                f"Block {block} does not contain both classes in train and test."
            )

        forest_probability = fit_random_forest(train, test)
        prevalence = float(train[TARGET].mean())
        persistence_probability = (
            test[CURRENT_LABEL].fillna(prevalence).to_numpy(dtype=float)
        )
        actual = test[TARGET].astype(int).to_numpy()
        common = {
            "bloc_spatial": int(block),
            "buffer_km": buffer_m / 1000,
            "sites_test": len(test_ids),
            "sites_train": len(train_ids),
            "sites_exclus_du_buffer": len(excluded_sites),
            "observations_train": len(train),
            "positifs_train": int(train[TARGET].sum()),
            "negatifs_train": int(len(train) - train[TARGET].sum()),
            "observations_test": len(test),
            "positifs_test": int(actual.sum()),
            "negatifs_test": int(len(actual) - actual.sum()),
        }
        for model_name, probability in [
            ("Balanced random forest", forest_probability),
            ("Persistence", persistence_probability),
        ]:
            fold_rows.append({
                **common,
                "modele": model_name,
                **score_predictions(actual, probability),
            })

    per_block = pd.DataFrame(fold_rows)
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    per_block.to_csv(FOLD_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    current_spatial = pd.read_csv(
        RESULTS_DIR / "performances_validation_spatiale.csv"
    )
    current_baselines = pd.read_csv(
        RESULTS_DIR / "performances_baselines_spatiales.csv"
    )
    current_metrics = {
        "Balanced random forest": current_spatial.loc[
            current_spatial["modele"] == "Balanced random forest"
        ].iloc[0],
        "Persistence": current_baselines.loc[
            current_baselines["reference"] == "Persistence"
        ].agg({
            "average_precision": "mean",
            "brier_score": "mean",
        }),
    }
    summary_rows = []
    for model_name, rows in per_block.groupby("modele", sort=False):
        baseline = current_metrics[model_name]
        summary_rows.append({
            "modele": model_name,
            "n_blocs": int(rows["bloc_spatial"].nunique()),
            "observations_test_total": int(rows["observations_test"].sum()),
            "positifs_test_total": int(rows["positifs_test"].sum()),
            "buffer_quantile_nearest_neighbor": BUFFER_QUANTILE,
            "buffer_km": buffer_m / 1000,
            "nearest_neighbor_q10_km": float(np.quantile(nearest_neighbor_m, 0.10) / 1000),
            "nearest_neighbor_q25_km": float(np.quantile(nearest_neighbor_m, 0.25) / 1000),
            "nearest_neighbor_median_km": float(np.median(nearest_neighbor_m) / 1000),
            "nearest_neighbor_q75_km": float(np.quantile(nearest_neighbor_m, 0.75) / 1000),
            "nearest_neighbor_q90_km": float(np.quantile(nearest_neighbor_m, 0.90) / 1000),
            "sites_exclus_du_buffer_total": int(
                rows.drop_duplicates("bloc_spatial")["sites_exclus_du_buffer"].sum()
            ),
            "average_precision_moyenne": float(rows["average_precision"].mean()),
            "average_precision_sd_blocs": float(rows["average_precision"].std(ddof=1)),
            "brier_moyen": float(rows["brier_score"].mean()),
            "brier_sd_blocs": float(rows["brier_score"].std(ddof=1)),
            "average_precision_validation_spatiale_sans_buffer": float(
                baseline["average_precision"]
            ),
            "brier_validation_spatiale_sans_buffer": float(baseline["brier_score"]),
            "delta_average_precision": float(
                rows["average_precision"].mean() - baseline["average_precision"]
            ),
            "delta_brier": float(rows["brier_score"].mean() - baseline["brier_score"]),
        })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Empirical 90th-percentile buffer: {buffer_m / 1000:.2f} km")
    print(f"Per-block metrics: {FOLD_OUTPUT_PATH}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
