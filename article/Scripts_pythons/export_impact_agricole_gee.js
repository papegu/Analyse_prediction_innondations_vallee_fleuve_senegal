/*******************************************************************************
 SENEGAL RIVER VALLEY - ANNUAL FLOOD AND AGRICULTURAL EXPOSURE EXPORTS
 Period: 2019-2024

 Run this script in the Google Earth Engine Code Editor.
 It creates six Drive tasks, one table per year, to keep each reduction small.
 Merge the six downloaded CSV files locally into:
   impact_agricole_inondations_2019_2024.csv

 Flood area and crop exposure are satellite estimates. The Dynamic World
 cropland probability threshold is provisional and requires local validation.
 The connected-component count is omitted to keep the regional reductions
 computationally tractable.
*******************************************************************************/

var POINTS_ASSET = 'projects/project37246/assets/points_200_vallee';
var DRIVE_FOLDER = 'GEE_VFS_SPI_10m';
var START_YEAR = 2019;
var END_YEAR = 2024;
var N_DEKADS = 16;
var S1_THRESHOLD_DB = -16;
var S1_SPECKLE_RADIUS_M = 30;
var CROP_PROBABILITY_THRESHOLD = 0.30;
var SCALE = 10;
var EXPORT_CRS = 'EPSG:32628';

var roi = ee.Geometry.Polygon(
  [[
    [-16.60, 16.35], [-15.50, 16.80],
    [-14.90, 16.90], [-13.80, 16.45],
    [-13.00, 15.75], [-12.20, 15.20],
    [-11.90, 14.40], [-12.50, 14.10],
    [-13.20, 15.00], [-14.30, 15.55],
    [-15.30, 15.70], [-16.00, 15.70],
    [-16.60, 15.85]
  ]],
  null,
  false
);

var points = ee.FeatureCollection(POINTS_ASSET);
var pixelArea = ee.Image.pixelArea();
var s1All = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .select(['VV', 'VH']);
var dwAll = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(roi)
  .select('crops');

function safeNumber(dictionary, key) {
  return ee.Number(ee.Algorithms.If(
    dictionary.contains(key), dictionary.get(key), 0
  ));
}

function s1Composite(collection) {
  var empty = ee.Image.constant([0, 0])
    .rename(['VV', 'VH'])
    .updateMask(ee.Image.constant(0));
  var median = ee.Image(ee.Algorithms.If(
    collection.size().gt(0), collection.median(), empty
  ));
  return median.focalMedian(S1_SPECKLE_RADIUS_M, 'circle', 'meters');
}

function dekadDates(year, index) {
  var start = ee.Date.fromYMD(year, 6, 1)
    .advance(ee.Number(index).multiply(10), 'day');
  var nominalEnd = start.advance(10, 'day');
  var seasonEnd = ee.Date.fromYMD(year, 11, 1);
  var end = ee.Date(ee.Algorithms.If(
    nominalEnd.millis().gt(seasonEnd.millis()), seasonEnd, nominalEnd
  ));
  return {start: start, end: end};
}

function annualImpactTable(year) {
  var dryStart = ee.Date.fromYMD(year, 3, 1);
  var dryEnd = ee.Date.fromYMD(year, 5, 16);
  var dryReference = s1Composite(s1All.filterDate(dryStart, dryEnd))
    .select('VV')
    .lt(S1_THRESHOLD_DB)
    .rename('eau_ref_seche');

  var cropCollection = dwAll.filterDate(
    ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 11, 1)
  );
  var cropProbability = cropCollection.mean();
  var cropMask = cropProbability.gte(CROP_PROBABILITY_THRESHOLD);

  var rows = ee.FeatureCollection(ee.List.sequence(0, N_DEKADS - 1).map(function(k) {
    var dates = dekadDates(year, k);
    var s1 = s1All.filterDate(dates.start, dates.end);
    var composite = s1Composite(s1);
    var vv = composite.select('VV');
    var water = vv.lt(S1_THRESHOLD_DB);

    // Potential new water relative to the annual pre-season reference.
    var flood = water.and(dryReference.not()).rename('inondation_S1');
    var validRadar = flood.mask().gt(0);
    var flooded = flood.eq(1).and(validRadar);
    var cropObserved = cropMask.and(validRadar);
    var cropFlooded = flooded.and(cropMask);

    // One combined reducer minimizes the number of full-ROI raster passes.
    var areaBands = ee.Image.cat([
      pixelArea.updateMask(flooded).rename('superficie_inondee_m2'),
      flooded.selfMask().rename('pixels_inondes'),
      pixelArea.updateMask(cropMask).rename('superficie_agricole_totale_m2'),
      pixelArea.updateMask(cropObserved).rename('superficie_agricole_observee_m2'),
      pixelArea.updateMask(cropFlooded).rename('superficie_agricole_inondee_m2'),
      cropFlooded.selfMask().rename('pixels_agricoles_inondes')
    ]);

    var sums = ee.Dictionary(areaBands.reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: roi,
      scale: SCALE,
      crs: EXPORT_CRS,
      maxPixels: 1e13,
      tileScale: 8
    }));

    var totalCropM2 = safeNumber(sums, 'superficie_agricole_totale_m2');
    var observedCropM2 = safeNumber(sums, 'superficie_agricole_observee_m2');
    var floodedCropM2 = safeNumber(sums, 'superficie_agricole_inondee_m2');
    var affectedPercent = ee.Algorithms.If(
      observedCropM2.gt(0),
      floodedCropM2.divide(observedCropM2).multiply(100),
      null
    );

    return ee.Feature(null, {
      annee: year,
      periode: ee.Number(k).add(1),
      date_debut: dates.start.format('YYYY-MM-dd'),
      n_images_S1: s1.size(),
      n_observations_dynamicworld: cropCollection.size(),
      pixels_inondes: safeNumber(sums, 'pixels_inondes'),
      superficie_inondee_ha:
        safeNumber(sums, 'superficie_inondee_m2').divide(10000),
      superficie_agricole_totale_ha: totalCropM2.divide(10000),
      superficie_agricole_observee_ha: observedCropM2.divide(10000),
      superficie_agricole_inondee_ha: floodedCropM2.divide(10000),
      pixels_agricoles_inondes: safeNumber(sums, 'pixels_agricoles_inondes'),
      pourcentage_surface_agricole_touchee: affectedPercent,
      seuil_VV_db: S1_THRESHOLD_DB,
      seuil_probabilite_culture: CROP_PROBABILITY_THRESHOLD,
      echelle_calcul_m: SCALE
    });
  }));

  return rows;
}

print('Point count', points.size());
print('Exports: one impact table per year, 16 dekads each.');

for (var year = START_YEAR; year <= END_YEAR; year++) {
  Export.table.toDrive({
    collection: annualImpactTable(year),
    description: 'impact_agricole_inondations_' + year,
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'impact_agricole_inondations_' + year,
    fileFormat: 'CSV'
  });
}

Map.centerObject(roi, 8);
Map.addLayer(roi, {color: 'red'}, 'Senegal River Valley', false);