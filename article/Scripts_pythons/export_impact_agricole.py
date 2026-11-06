"""Export annual agricultural flood-impact tables from Earth Engine."""
from __future__ import annotations

import argparse
from pathlib import Path

import ee
import pandas as pd
from google.auth.transport.requests import AuthorizedSession


PROJECT = "project37246"
ASSET_ROOT = f"projects/{PROJECT}/assets"
OUTPUT = Path(__file__).resolve().parent.parent / "impact_agricole_inondations_2019_2024.csv"
YEARS = range(2019, 2025)
SCALE = 10
CRS = "EPSG:32628"
THRESHOLD_DB = -16
CROP_THRESHOLD = 0.30
MAX_PIXELS = 1e13
TILE_SCALE = 8

ROI_COORDS = [
    [-16.60, 16.35], [-15.50, 16.80], [-14.90, 16.90],
    [-13.80, 16.45], [-13.00, 15.75], [-12.20, 15.20],
    [-11.90, 14.40], [-12.50, 14.10], [-13.20, 15.00],
    [-14.30, 15.55], [-15.30, 15.70], [-16.00, 15.70],
    [-16.60, 15.85],
]


def initialize() -> ee.Geometry:
    ee.Initialize(project=PROJECT)
    return ee.Geometry.Polygon([ROI_COORDS], None, False)


def sentinel1_collection(roi: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.ImageCollection:
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
    )


def radar_composite(collection: ee.ImageCollection) -> ee.Image:
    empty = (
        ee.Image.constant([0, 0])
        .rename(["VV", "VH"])
        .updateMask(ee.Image.constant(0))
    )
    composite = ee.Image(ee.Algorithms.If(collection.size().gt(0), collection.median(), empty))
    return composite.focalMedian(30, "circle", "meters")


def period_dates(year: int, index: ee.Number) -> tuple[ee.Date, ee.Date]:
    index = ee.Number(index)
    start = ee.Date.fromYMD(year, 6, 1).advance(index.multiply(10), "day")
    nominal_end = start.advance(10, "day")
    season_end = ee.Date.fromYMD(year, 11, 1)
    end = ee.Date(ee.Algorithms.If(nominal_end.millis().gt(season_end.millis()), season_end, nominal_end))
    return start, end


def get_value(values: ee.Dictionary, key: str) -> ee.Number:
    return ee.Number(ee.Algorithms.If(values.contains(key), values.get(key), 0))


def annual_collection(roi: ee.Geometry, year: int) -> ee.FeatureCollection:
    dry_collection = sentinel1_collection(
        roi, ee.Date.fromYMD(year, 3, 1), ee.Date.fromYMD(year, 5, 16)
    )
    dry_water = radar_composite(dry_collection).select("VV").lt(THRESHOLD_DB)
    crops = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(roi)
        .filterDate(ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 11, 1))
        .select("crops")
    )
    crop_mask = crops.mean().gte(CROP_THRESHOLD)
    pixel_area = ee.Image.pixelArea()

    def period_feature(index: ee.Number) -> ee.Feature:
        index = ee.Number(index)
        start, end = period_dates(year, index)
        collection = sentinel1_collection(roi, start, end)
        vv = radar_composite(collection).select("VV")
        water = vv.lt(THRESHOLD_DB)
        flood = water.And(dry_water.Not())
        valid = flood.mask().gt(0)
        flooded = flood.eq(1).And(valid)
        crop_observed = crop_mask.And(valid)
        crop_flooded = flooded.And(crop_mask)

        area_bands = ee.Image.cat([
            pixel_area.updateMask(flooded).rename("superficie_inondee_m2"),
            flooded.selfMask().rename("pixels_inondes"),
            pixel_area.updateMask(crop_mask).rename("superficie_agricole_totale_m2"),
            pixel_area.updateMask(crop_observed).rename("superficie_agricole_observee_m2"),
            pixel_area.updateMask(crop_flooded).rename("superficie_agricole_inondee_m2"),
            crop_flooded.selfMask().rename("pixels_agricoles_inondes"),
        ])
        values = ee.Dictionary(area_bands.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=SCALE,
            crs=CRS,
            maxPixels=MAX_PIXELS,
            tileScale=TILE_SCALE,
        ))

        total_crop = get_value(values, "superficie_agricole_totale_m2")
        observed_crop = get_value(values, "superficie_agricole_observee_m2")
        flood_crop = get_value(values, "superficie_agricole_inondee_m2")
        affected_percent = ee.Algorithms.If(
            observed_crop.gt(0), flood_crop.divide(observed_crop).multiply(100), None
        )

        return ee.Feature(None, {
            "annee": year,
            "periode": index.add(1),
            "date_debut": start.format("YYYY-MM-dd"),
            "n_images_S1": collection.size(),
            "n_observations_dynamicworld": crops.size(),
            "pixels_inondes": get_value(values, "pixels_inondes"),
            "superficie_inondee_ha": get_value(values, "superficie_inondee_m2").divide(10000),
            "nombre_zones_detectees": None,
            "superficie_agricole_totale_ha": total_crop.divide(10000),
            "superficie_agricole_observee_ha": observed_crop.divide(10000),
            "superficie_agricole_inondee_ha": flood_crop.divide(10000),
            "pixels_agricoles_inondes": get_value(values, "pixels_agricoles_inondes"),
            "pourcentage_surface_agricole_touchee": affected_percent,
        })

    return ee.FeatureCollection(ee.List.sequence(0, 15).map(period_feature))


def submit_exports() -> None:
    roi = initialize()
    for year in YEARS:
        asset_id = f"{ASSET_ROOT}/impact_agricole_{year}"
        task = ee.batch.Export.table.toAsset(
            collection=annual_collection(roi, year),
            description=f"impact_agricole_{year}",
            assetId=asset_id,
        )
        task.start()
        print(f"submitted year={year} task={task.id} asset={asset_id}", flush=True)


def download_exports() -> None:
    initialize()
    session = AuthorizedSession(ee.data.get_persistent_credentials())
    frames = []
    for year in YEARS:
        asset_id = f"{ASSET_ROOT}/impact_agricole_{year}"
        table = ee.FeatureCollection(asset_id)
        url = table.getDownloadURL(filetype="csv")
        response = session.get(url, timeout=180)
        response.raise_for_status()
        frame = pd.read_csv(pd.io.common.StringIO(response.text))
        frames.append(frame)
        print(f"downloaded year={year} rows={len(frame)}", flush=True)

    result = pd.concat(frames, ignore_index=True).sort_values(["annee", "periode"])
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"CSV: {OUTPUT}")
    print(f"Rows: {len(result)}; expected: {len(list(YEARS)) * 16}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download completed annual assets and merge the CSV.")
    args = parser.parse_args()
    if args.download:
        download_exports()
    else:
        submit_exports()


if __name__ == "__main__":
    main()