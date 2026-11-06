"""Merge the six annual CSVs exported by export_impact_agricole_gee.js."""
from pathlib import Path
import sys

import pandas as pd


ARTICLE_DIR = Path(__file__).resolve().parent
DATA_DIR = ARTICLE_DIR.parent
INPUT_DIR = ARTICLE_DIR / "data_gee_before"
OUTPUT = DATA_DIR / "impact_agricole_inondations_2019_2024.csv"
YEARS = range(2019, 2025)


def main() -> None:
    frames = []
    for year in YEARS:
        path = INPUT_DIR / f"impact_agricole_inondations_{year}.csv"
        if not path.exists():
            sys.exit(f"Missing annual GEE export: {path}")
        frame = pd.read_csv(path, low_memory=False)
        if "annee" not in frame or "periode" not in frame:
            sys.exit(f"Expected columns 'annee' and 'periode' in {path.name}")
        frame["annee"] = pd.to_numeric(frame["annee"], errors="coerce")
        frame["periode"] = pd.to_numeric(frame["periode"], errors="coerce")
        if frame["annee"].dropna().nunique() != 1 or int(frame["annee"].dropna().iloc[0]) != year:
            sys.exit(f"Unexpected year values in {path.name}")
        if frame["periode"].nunique() != 16:
            sys.exit(f"Expected 16 periods for {year}; got {frame['periode'].nunique()}")
        frames.append(frame)

    result = pd.concat(frames, ignore_index=True).sort_values(["annee", "periode"])
    if len(result) != 96:
        sys.exit(f"Expected 96 annual-period rows; got {len(result)}")
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Created {OUTPUT}")
    print(f"Rows: {len(result)}; period range: {result['date_debut'].min()} to {result['date_debut'].max()}")


if __name__ == "__main__":
    main()