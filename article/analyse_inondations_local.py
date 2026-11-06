# -*- coding: utf-8 -*-
"""
Analyse locale du dataset VFS 2019-2024 exporté depuis Google Earth Engine.

Ce script ne consomme aucun quota GEE. Il nécessite un CSV déjà exporté :
  dataset_vfs_ml_2019_2024.csv

Sorties créées dans ./resultats_inondations :
- statistiques_globales.csv
- statistiques_par_annee.csv
- statistiques_par_periode.csv
- frequence_inondations_par_point.csv
- qualite_donnees.csv
- matrice_inondations_annee_periode.csv
- graphiques PNG

Important : le CSV ponctuel ne permet pas de calculer la superficie inondée
sur toute la zone ni un GeoTIFF spatial fiable. Ces sorties nécessitent les
rasters d'inondation source exportés séparément depuis GEE.
"""
from pathlib import Path
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

INPUT = Path("dataset_vfs_ml_2019_2024.csv")
OUT = Path("resultats_inondations")
OUT.mkdir(parents=True, exist_ok=True)

if not INPUT.exists():
    sys.exit(
        f"Fichier introuvable : {INPUT.resolve()}\n"
        "Place dataset_vfs_ml_2019_2024.csv dans le même dossier que ce script."
    )

# Lecture robuste : colonnes vides restent NaN, sans remplacement arbitraire par 0.
df = pd.read_csv(INPUT, low_memory=False)
df.columns = [c.strip() for c in df.columns]

required = {"point_id", "annee", "periode", "date_debut", "inondation_S1"}
missing = required - set(df.columns)
if missing:
    sys.exit(f"Colonnes obligatoires absentes du CSV : {sorted(missing)}")

for c in ["annee", "periode", "inondation_S1", "n_images_S1", "observation_S1_valide"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# Normaliser la cible binaire sans transformer les valeurs manquantes en non-inondation.
df["inondation_S1"] = df["inondation_S1"].where(df["inondation_S1"].isin([0, 1]))
if "date_debut" in df.columns:
    df["date_debut"] = pd.to_datetime(df["date_debut"], errors="coerce")

# 1) Contrôle qualité
quality = pd.DataFrame({
    "colonne": df.columns,
    "type": [str(df[c].dtype) for c in df.columns],
    "valeurs_manquantes": [int(df[c].isna().sum()) for c in df.columns],
    "pourcentage_manquant": [round(float(df[c].isna().mean()*100), 3) for c in df.columns],
    "valeurs_distinctes": [int(df[c].nunique(dropna=True)) for c in df.columns],
})
quality.to_csv(OUT / "qualite_donnees.csv", index=False, encoding="utf-8-sig")

# 2) Statistiques globales et annuelles
valid = df[df["inondation_S1"].notna()].copy()
valid["inondation_S1"] = valid["inondation_S1"].astype(int)

global_rows = [{
    "nombre_lignes_total": len(df),
    "nombre_points_distincts": int(df["point_id"].nunique()),
    "nombre_annees": int(df["annee"].nunique()),
    "nombre_observations_cible_valide": len(valid),
    "nombre_periodes_inondees": int((valid["inondation_S1"] == 1).sum()),
    "nombre_periodes_non_inondees": int((valid["inondation_S1"] == 0).sum()),
    "taux_inondation_pct": round(float(valid["inondation_S1"].mean()*100), 4) if len(valid) else np.nan,
    "taux_cible_manquante_pct": round(float(df["inondation_S1"].isna().mean()*100), 4),
}]
pd.DataFrame(global_rows).to_csv(OUT / "statistiques_globales.csv", index=False, encoding="utf-8-sig")

annual = valid.groupby("annee", dropna=False).agg(
    observations_valides=("inondation_S1", "size"),
    periodes_inondees=("inondation_S1", "sum"),
    points_distincts=("point_id", "nunique"),
    taux_inondation_pct=("inondation_S1", lambda s: s.mean()*100),
).reset_index()
annual["periodes_non_inondees"] = annual["observations_valides"] - annual["periodes_inondees"]
annual["taux_inondation_pct"] = annual["taux_inondation_pct"].round(4)
annual.to_csv(OUT / "statistiques_par_annee.csv", index=False, encoding="utf-8-sig")

# 3) Statistiques par période (agrégation des points observés)
period_cols = ["annee", "periode"]
if "date_debut" in valid.columns:
    period_cols.append("date_debut")
period = valid.groupby(period_cols, dropna=False).agg(
    observations_valides=("inondation_S1", "size"),
    points_inondes=("inondation_S1", "sum"),
    taux_points_inondes_pct=("inondation_S1", lambda s: s.mean()*100),
).reset_index()
period["points_non_inondes"] = period["observations_valides"] - period["points_inondes"]
period["taux_points_inondes_pct"] = period["taux_points_inondes_pct"].round(4)
period.to_csv(OUT / "statistiques_par_periode.csv", index=False, encoding="utf-8-sig")

# 4) Fréquence par point : seulement les périodes où la cible est renseignée.
point_freq = valid.groupby("point_id").agg(
    nombre_periodes_valides=("inondation_S1", "size"),
    nombre_periodes_inondees=("inondation_S1", "sum"),
    frequence_inondation_pct=("inondation_S1", lambda s: s.mean()*100),
    premiere_annee_observee=("annee", "min"),
    derniere_annee_observee=("annee", "max"),
).reset_index()
point_freq["frequence_inondation_pct"] = point_freq["frequence_inondation_pct"].round(4)
# Ajouter coordonnées si présentes.
for c in ["lon", "lat", "NDVI_ref"]:
    if c in df.columns:
        coords = df.groupby("point_id")[c].first().reset_index()
        point_freq = point_freq.merge(coords, on="point_id", how="left")
point_freq.to_csv(OUT / "frequence_inondations_par_point.csv", index=False, encoding="utf-8-sig")

# 5) Tableau année x période pour comparaison temporelle.
pivot = period.pivot_table(index="annee", columns="periode", values="taux_points_inondes_pct", aggfunc="mean")
pivot.to_csv(OUT / "matrice_inondations_annee_periode.csv", encoding="utf-8-sig")

# 6) Graphiques sans palette imposée.
if not annual.empty:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(annual["annee"].astype("Int64").astype(str), annual["taux_inondation_pct"])
    ax.set_title("Taux d'observations ponctuelles classées inondées par année")
    ax.set_xlabel("Année")
    ax.set_ylabel("Taux d'inondation (%)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(OUT / "taux_inondation_par_annee.png", dpi=180); plt.close(fig)

if not period.empty:
    period_plot = period.sort_values(["annee", "periode"]).copy()
    period_plot["annee_periode"] = period_plot["annee"].astype("Int64").astype(str) + "-P" + period_plot["periode"].astype("Int64").astype(str)
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(period_plot["annee_periode"], period_plot["taux_points_inondes_pct"], marker="o", linewidth=1)
    ax.set_title("Évolution du taux de points classés inondés par période")
    ax.set_xlabel("Année-période")
    ax.set_ylabel("Points inondés parmi les observations valides (%)")
    ax.tick_params(axis="x", labelrotation=90)
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(OUT / "taux_inondation_par_periode.png", dpi=180); plt.close(fig)

if not point_freq.empty:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(point_freq["frequence_inondation_pct"].dropna(), bins=20)
    ax.set_title("Distribution de la fréquence d'inondation par point")
    ax.set_xlabel("Périodes inondées / périodes valides (%)")
    ax.set_ylabel("Nombre de points")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(OUT / "distribution_frequence_par_point.png", dpi=180); plt.close(fig)

print("Analyse terminée.")
print(f"Entrée : {INPUT.resolve()}")
print(f"Sorties : {OUT.resolve()}")
print(f"Lignes CSV : {len(df):,}")
print(f"Points distincts : {df['point_id'].nunique():,}")
print(f"Observations avec cible valide : {len(valid):,}")
print("Note : les taux calculés concernent les points échantillonnés, pas la superficie totale inondée.")
