"""Audit raw threshold-sensitivity exports without modifying project files."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ARTICLE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ARTICLE_DIR.parent
RESULTS_DIR = ARTICLE_DIR / "resultats_inondations"
KEYS = ["point_id", "annee", "periode"]
AREA_KEYS = ["annee", "periode"]
VV_SUFFIXES = {"m14": -14, "m16": -16, "m18": -18}
CROP_SUFFIXES = {"c20": 0.20, "c30": 0.30, "c40": 0.40}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only audit of the GEE threshold-sensitivity CSV exports."
    )
    parser.add_argument(
        "--main-data",
        type=Path,
        default=PROJECT_DIR / "dataset_vfs_ml_2019_2024.csv",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=RESULTS_DIR / "sensibilite_labels_points_VV_2019_2024.csv",
    )
    parser.add_argument(
        "--areas",
        type=Path,
        default=RESULTS_DIR / "sensibilite_superficies_VV_DW_2019_2024.csv",
    )
    return parser.parse_args()


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required input CSV is missing: {path}")


def read_csv(path: Path) -> pd.DataFrame:
    require_file(path)
    frame = pd.read_csv(path, low_memory=False)
    frame.columns = frame.columns.str.strip()
    print(f"{path.name}: {len(frame):,} rows, {len(frame.columns)} columns, "
          f"{path.stat().st_size:,} bytes")
    print(f"  columns: {', '.join(frame.columns)}")
    missing = frame.isna().sum()
    nonzero_missing = missing[missing.gt(0)]
    if nonzero_missing.empty:
        print("  missing values: none")
    else:
        print("  missing values: " + ", ".join(
            f"{column}={int(count):,}" for column, count in nonzero_missing.items()
        ))
    return frame


def require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def normalized_keys(
    frame: pd.DataFrame, name: str, key_columns: list[str] = KEYS
) -> pd.DataFrame:
    keys = frame[key_columns].copy()
    if "point_id" in key_columns:
        keys["point_id"] = keys["point_id"].astype("string").str.strip()
    for column in ["annee", "periode"]:
        keys[column] = pd.to_numeric(keys[column], errors="coerce")
    if keys.isna().any().any():
        raise ValueError(f"{name} contains missing or invalid join keys.")
    if keys.duplicated().any():
        sample = keys.loc[keys.duplicated(keep=False)].head(5).to_dict("records")
        raise ValueError(f"{name} has duplicate point/year/period keys: {sample}")
    return keys


def values_match(left: pd.Series, right: pd.Series) -> np.ndarray:
    left_values = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    right_values = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    same_missing = np.isnan(left_values) & np.isnan(right_values)
    both_present = np.isfinite(left_values) & np.isfinite(right_values)
    close = np.zeros(len(left_values), dtype=bool)
    close[both_present] = np.isclose(
        left_values[both_present], right_values[both_present], rtol=0, atol=1e-10
    )
    return same_missing | close


def compare_labels(main: pd.DataFrame, labels: pd.DataFrame) -> None:
    require_columns(
        main,
        {"point_id", "annee", "periode", "date_debut", "lon", "lat",
         "inondation_S1", "inondation_S1_suivante"},
        "main dataset",
    )
    export_columns = {
        *KEYS, "date_debut", "lon", "lat", "n_images_S1",
        *(f"inondation_{suffix}" for suffix in VV_SUFFIXES),
        *(f"inondation_suivante_{suffix}" for suffix in VV_SUFFIXES),
    }
    require_columns(labels, export_columns, "point-label export")
    main_keys = normalized_keys(main, "main dataset")
    label_keys = normalized_keys(labels, "point-label export")
    if len(labels) != 19_200:
        raise ValueError(f"Expected 19,200 point rows; found {len(labels):,}.")
    label_years = sorted(pd.to_numeric(labels["annee"]).dropna().unique().tolist())
    label_periods = sorted(pd.to_numeric(labels["periode"]).dropna().unique().tolist())
    if label_years != list(range(2019, 2025)) or label_periods != list(range(1, 17)):
        raise ValueError(
            f"Unexpected years or periods: years={label_years}, periods={label_periods}."
        )
    counts = label_keys.groupby(["annee", "periode"]).size()
    if len(counts) != 96 or not counts.eq(200).all():
        raise ValueError(
            "Expected 200 point records in each of 96 year/period groups."
        )
    joined = main_keys.merge(
        label_keys, on=KEYS, how="outer", indicator=True, validate="one_to_one"
    )
    unmatched = joined.loc[joined["_merge"] != "both"]
    if not unmatched.empty:
        raise ValueError(
            f"Main dataset and point export have {len(unmatched)} unmatched keys; "
            f"examples: {unmatched.head(5).to_dict('records')}"
        )

    left = main.copy()
    right = labels.copy()
    for frame in [left, right]:
        frame["point_id"] = frame["point_id"].astype("string").str.strip()
        frame["annee"] = pd.to_numeric(frame["annee"], errors="coerce")
        frame["periode"] = pd.to_numeric(frame["periode"], errors="coerce")
    paired = left.merge(
        right,
        on=KEYS,
        how="inner",
        suffixes=("_main", "_export"),
        validate="one_to_one",
    )
    for suffix in VV_SUFFIXES:
        current = f"inondation_{suffix}"
        following = f"inondation_suivante_{suffix}"
        for column in [current, following]:
            values = pd.to_numeric(right[column], errors="coerce").dropna()
            if not values.isin([0, 1]).all():
                raise ValueError(f"{column} contains values other than 0, 1, or missing.")

    for export_column, main_column in [
        ("inondation_m16", "inondation_S1"),
        ("inondation_suivante_m16", "inondation_S1_suivante"),
        ("date_debut_export", "date_debut_main"),
        ("lon_export", "lon_main"),
        ("lat_export", "lat_main"),
    ]:
        if export_column in {"date_debut_export", "lon_export", "lat_export"}:
            if export_column == "date_debut_export":
                match = (
                    pd.to_datetime(paired[export_column], errors="coerce")
                    == pd.to_datetime(paired[main_column], errors="coerce")
                ).to_numpy()
            else:
                match = values_match(paired[export_column], paired[main_column])
        else:
            match = values_match(paired[export_column], paired[main_column])
        if not match.all():
            raise ValueError(
                f"{int((~match).sum()):,} mismatches between "
                f"{export_column} and {main_column}."
            )
        print(f"  exact agreement: {export_column} == {main_column} ({len(paired):,} keys)")

    print(
        f"  unique point IDs: {labels['point_id'].nunique():,}; "
        f"years: {sorted(pd.to_numeric(labels['annee']).dropna().unique().tolist())}; "
        f"periods: {sorted(pd.to_numeric(labels['periode']).dropna().unique().tolist())}"
    )
    print(
        f"  VV label settings present: {', '.join(str(value) + ' dB' for value in VV_SUFFIXES.values())}"
    )


def audit_areas(areas: pd.DataFrame) -> None:
    required = {
        *AREA_KEYS, "date_debut", "n_images_S1", "n_observations_dynamicworld",
        *(f"superficie_inondee_ha_{suffix}" for suffix in VV_SUFFIXES),
        *(
            column
            for vv in VV_SUFFIXES
            for crop in CROP_SUFFIXES
            for column in [
                f"superficie_agricole_observee_ha_{vv}_{crop}",
                f"superficie_agricole_inondee_ha_{vv}_{crop}",
                f"pourcentage_agricole_touche_{vv}_{crop}",
            ]
        ),
    }
    require_columns(areas, required, "area export")
    keys = normalized_keys(areas, "area export", AREA_KEYS)
    years = sorted(pd.to_numeric(areas["annee"], errors="coerce").dropna().unique())
    periods = sorted(pd.to_numeric(areas["periode"], errors="coerce").dropna().unique())
    if len(areas) != 96 or years != list(range(2019, 2025)) or periods != list(range(1, 17)):
        raise ValueError(
            f"Expected 96 area rows for years 2019--2024 and periods 1--16; "
            f"found {len(areas)} rows, years={years}, periods={periods}."
        )
    expected_dates = pd.to_datetime(areas["date_debut"], errors="coerce")
    if expected_dates.isna().any():
        raise ValueError("Area export contains invalid period start dates.")
    expected_period_dates = pd.to_datetime(
        areas["annee"].astype(str) + "-06-01"
    ) + pd.to_timedelta((pd.to_numeric(areas["periode"]) - 1) * 10, unit="D")
    if not expected_dates.eq(expected_period_dates).all():
        raise ValueError("Area dates do not match the expected ten-day periods.")
    image_counts = pd.to_numeric(areas["n_images_S1"], errors="coerce")
    dynamicworld_counts = pd.to_numeric(
        areas["n_observations_dynamicworld"], errors="coerce"
    )
    if image_counts.isna().any() or image_counts.lt(0).any():
        raise ValueError("Area export contains missing or negative Sentinel-1 counts.")
    if dynamicworld_counts.isna().any() or dynamicworld_counts.lt(0).any():
        raise ValueError("Area export contains missing or negative Dynamic World counts.")
    area_columns = [
        f"superficie_inondee_ha_{suffix}" for suffix in VV_SUFFIXES
    ] + [
        column
        for vv in VV_SUFFIXES
        for crop in CROP_SUFFIXES
        for column in [
            f"superficie_agricole_observee_ha_{vv}_{crop}",
            f"superficie_agricole_inondee_ha_{vv}_{crop}",
        ]
    ]
    for column in area_columns:
        values = pd.to_numeric(areas[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all() or values.lt(0).any():
            raise ValueError(f"{column} contains missing, non-finite, or negative areas.")
    for vv in VV_SUFFIXES:
        for crop in CROP_SUFFIXES:
            observed = pd.to_numeric(
                areas[f"superficie_agricole_observee_ha_{vv}_{crop}"],
                errors="coerce",
            )
            flooded = pd.to_numeric(
                areas[f"superficie_agricole_inondee_ha_{vv}_{crop}"],
                errors="coerce",
            )
            percentage = pd.to_numeric(
                areas[f"pourcentage_agricole_touche_{vv}_{crop}"],
                errors="coerce",
            )
            if percentage.dropna().lt(0).any() or percentage.dropna().gt(100).any():
                raise ValueError(
                    f"Percentage values for {vv}/{crop} fall outside 0--100."
                )
            expected_percentage = flooded.div(observed.where(observed.gt(0))).mul(100)
            comparable = percentage.notna() & expected_percentage.notna()
            if comparable.any() and not np.allclose(
                percentage[comparable],
                expected_percentage[comparable],
                rtol=0,
                atol=1e-5,
            ):
                raise ValueError(
                    f"Reported percentage is inconsistent with areas for {vv}/{crop}."
                )
            if (percentage.isna() != expected_percentage.isna()).any():
                raise ValueError(
                    f"Missing percentages do not match zero denominators for {vv}/{crop}."
                )
    print(
        f"  area periods: {len(keys):,} unique; years: {years}; "
        f"dekads: {periods}"
    )
    print(
        "  VV settings: -14, -16, -18 dB; Dynamic World crop thresholds: "
        "0.20, 0.30, 0.40 (nine exported combinations)"
    )
    no_radar = image_counts.eq(0)
    print(f"  periods with zero Sentinel-1 images: {int(no_radar.sum())}")
    if no_radar.any():
        unexpected = {
            column: int(pd.to_numeric(areas.loc[no_radar, column], errors="coerce").ne(0).sum())
            for column in area_columns
        }
        unexpected = {column: count for column, count in unexpected.items() if count}
        if unexpected:
            raise ValueError(
                "Areas should be zero when no radar images are available; "
                f"nonzero values: {unexpected}"
            )
        print(
            "  zero-radar periods contain zero areas; treat these as unobserved, "
            "not as measured zero inundation."
        )


def compare_period_metadata(labels: pd.DataFrame, areas: pd.DataFrame) -> None:
    point_periods = (
        labels.groupby(["annee", "periode"], as_index=False)
        .agg(
            date_points=("date_debut", "first"),
            n_images_points=("n_images_S1", "first"),
            unique_dates=("date_debut", "nunique"),
            unique_image_counts=("n_images_S1", "nunique"),
        )
    )
    if point_periods["unique_dates"].ne(1).any():
        raise ValueError("Point export has inconsistent dates within a period.")
    if point_periods["unique_image_counts"].ne(1).any():
        raise ValueError("Point export has inconsistent Sentinel-1 counts within a period.")
    point_periods["n_images_points"] = pd.to_numeric(
        point_periods["n_images_points"], errors="coerce"
    )
    area_periods = areas[["annee", "periode", "date_debut", "n_images_S1"]].copy()
    area_periods["n_images_S1"] = pd.to_numeric(
        area_periods["n_images_S1"], errors="coerce"
    )
    compared = point_periods.merge(
        area_periods,
        on=["annee", "periode"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    mismatch = (
        compared["_merge"].ne("both")
        | compared["date_points"].ne(compared["date_debut"])
        | compared["n_images_points"].ne(compared["n_images_S1"])
    )
    if mismatch.any():
        raise ValueError(
            f"Point and area exports disagree on {int(mismatch.sum())} period "
            "dates or Sentinel-1 image counts."
        )
    print("  point/area dates and Sentinel-1 image counts agree for all 96 periods.")


def main() -> int:
    args = parse_args()
    try:
        main_data = read_csv(args.main_data)
        labels = read_csv(args.labels)
        areas = read_csv(args.areas)
        print("Label-export comparison:")
        compare_labels(main_data, labels)
        print("Area-export structure:")
        audit_areas(areas)
        compare_period_metadata(labels, areas)
    except (FileNotFoundError, pd.errors.ParserError, ValueError) as error:
        print(f"AUDIT FAILED: {error}")
        return 1
    print("AUDIT PASSED. No files were written or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
