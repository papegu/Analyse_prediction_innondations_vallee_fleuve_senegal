/*******************************************************************************
 SENEGAL RIVER VALLEY — SEUILS DE SENSIBILITE

 Prépare deux exports CSV Google Drive :
 1. Labels Sentinel-1 aux seuils -14, -16 et -18 dB pour les 200 points
    et les 16 périodes de juin à octobre, années 2019-2024.
 2. Surfaces inondées et exposition agricole par période, croisant les mêmes
    seuils Sentinel-1 avec les probabilités Dynamic World 0.20, 0.30 et 0.40.

 Les labels sont des proxys Sentinel-1, non une vérité terrain indépendante.
 Les superficies agricoles sont rétrospectives : le masque Dynamic World est
 la moyenne de la saison (1 juin - 1 novembre) pour chaque année.

 Ouvrir dans le Code Editor Earth Engine, vérifier l'accès à POINTS_ASSET,
 cliquer Run, puis lancer les deux tâches proposées dans l'onglet Tasks.
*******************************************************************************/

var POINTS_ASSET = 'projects/project37246/assets/points_200_vallee';
var DRIVE_FOLDER = 'GEE_VFS_SPI_10m';

var START_YEAR = 2019;
var END_YEAR = 2024;
var N_DEKADS = 16;
var SCALE = 10;
var EXPORT_CRS = 'EPSG:32628';
var SPECKLE_RADIUS_M = 30;

var VV_THRESHOLDS = [
  {value: -14, suffix: 'm14'},
  {value: -16, suffix: 'm16'},
  {value: -18, suffix: 'm18'}
];

var CROP_THRESHOLDS = [
  {value: 0.20, suffix: 'c20'},
  {value: 0.30, suffix: 'c30'},
  {value: 0.40, suffix: 'c40'}
];

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

var points = ee.FeatureCollection(POINTS_ASSET).map(function(feature) {
  var lon = ee.Number(feature.get('lon'));
  var lat = ee.Number(feature.get('lat'));
  return ee.Feature(ee.Geometry.Point([lon, lat]), {
    point_id: ee.String(feature.get('point_id')),
    lon: lon,
    lat: lat
  });
});

var s1All = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains(
    'transmitterReceiverPolarisation', 'VV'
  ))
  .filter(ee.Filter.listContains(
    'transmitterReceiverPolarisation', 'VH'
  ))
  .select(['VV', 'VH']);

var dwAll = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(roi)
  .select('crops');

function s1Composite(collection) {
  var empty = ee.Image.constant([0, 0])
    .rename(['VV', 'VH'])
    .updateMask(ee.Image.constant(0));
  var median = ee.Image(ee.Algorithms.If(
    collection.size().gt(0),
    collection.median(),
    empty
  ));
  return median.focalMedian(SPECKLE_RADIUS_M, 'circle', 'meters');
}

function dekadDates(year, index) {
  var start = ee.Date.fromYMD(year, 6, 1)
    .advance(index * 10, 'day');
  var nominalEnd = start.advance(10, 'day');
  var seasonEnd = ee.Date.fromYMD(year, 11, 1);
  var end = ee.Date(ee.Algorithms.If(
    nominalEnd.millis().gt(seasonEnd.millis()),
    seasonEnd,
    nominalEnd
  ));
  return {start: start, end: end};
}

function floodLabel(vv, dryVv, threshold, bandName) {
  var valid = vv.mask().gt(0).and(dryVv.mask().gt(0));
  return vv.lt(threshold)
    .and(dryVv.gte(threshold))
    .rename(bandName)
    .updateMask(valid);
}

function maskedLabel(bandName) {
  return ee.Image.constant(0)
    .rename(bandName)
    .updateMask(ee.Image.constant(0));
}

function numberOrZero(dictionary, key) {
  return ee.Number(ee.Algorithms.If(
    dictionary.contains(key),
    dictionary.get(key),
    0
  ));
}

var pointRows = ee.FeatureCollection([]);
var areaRows = ee.FeatureCollection([]);
var pixelArea = ee.Image.pixelArea();

for (var year = START_YEAR; year <= END_YEAR; year++) {
  var dryComposite = s1Composite(s1All.filterDate(
    ee.Date.fromYMD(year, 3, 1),
    ee.Date.fromYMD(year, 5, 16)
  ));
  var dryVv = dryComposite.select('VV');

  var cropCollection = dwAll.filterDate(
    ee.Date.fromYMD(year, 6, 1),
    ee.Date.fromYMD(year, 11, 1)
  );
  var cropProbability = cropCollection.mean().rename('proba_culture');

  for (var k = 0; k < N_DEKADS; k++) {
    var dates = dekadDates(year, k);
    var currentCollection = s1All.filterDate(dates.start, dates.end);
    var currentComposite = s1Composite(currentCollection);
    var currentVv = currentComposite.select('VV');
    var currentVh = currentComposite.select('VH');

    var nextVv;
    if (k < N_DEKADS - 1) {
      var nextDates = dekadDates(year, k + 1);
      nextVv = s1Composite(
        s1All.filterDate(nextDates.start, nextDates.end)
      ).select('VV');
    }

    var pointBands = [
      currentVv.rename('S1_VV'),
      currentVh.rename('S1_VH'),
      cropProbability
    ];

    var labelsByThreshold = [];
    for (var vi = 0; vi < VV_THRESHOLDS.length; vi++) {
      var vvSetting = VV_THRESHOLDS[vi];
      var currentName = 'inondation_' + vvSetting.suffix;
      var nextName = 'inondation_suivante_' + vvSetting.suffix;
      var currentLabel = floodLabel(
        currentVv, dryVv, vvSetting.value, currentName
      );
      var nextLabel = k < N_DEKADS - 1
        ? floodLabel(nextVv, dryVv, vvSetting.value, nextName)
        : maskedLabel(nextName);

      pointBands.push(currentLabel, nextLabel);
      labelsByThreshold.push({
        setting: vvSetting,
        current: currentLabel
      });
    }

    for (var ci = 0; ci < CROP_THRESHOLDS.length; ci++) {
      var cropSetting = CROP_THRESHOLDS[ci];
      pointBands.push(
        cropProbability.gte(cropSetting.value)
          .rename('zone_agricole_' + cropSetting.suffix)
      );
    }

    var sampled = ee.Image.cat(pointBands)
      .clip(roi)
      .reduceRegions({
        collection: points,
        reducer: ee.Reducer.first(),
        scale: SCALE,
        crs: EXPORT_CRS,
        tileScale: 4
      })
      .map(function(feature) {
        return feature.set({
          annee: year,
          periode: k + 1,
          date_debut: dates.start.format('YYYY-MM-dd'),
          n_images_S1: currentCollection.size(),
          n_observations_dynamicworld: cropCollection.size()
        });
      });

    pointRows = pointRows.merge(sampled);

    var validRadar = currentVv.mask().gt(0).and(dryVv.mask().gt(0));
    var areaBands = [];

    for (var vj = 0; vj < labelsByThreshold.length; vj++) {
      var floodSetting = labelsByThreshold[vj].setting;
      var flood = labelsByThreshold[vj].current;
      var floodBandName = 'inondee_m2_' + floodSetting.suffix;

      areaBands.push(
        pixelArea.updateMask(flood)
          .rename(floodBandName)
      );

      for (var cj = 0; cj < CROP_THRESHOLDS.length; cj++) {
        var areaCropSetting = CROP_THRESHOLDS[cj];
        var cropMask = cropProbability.gte(areaCropSetting.value);
        var observedName = 'culture_observee_m2_' +
          floodSetting.suffix + '_' + areaCropSetting.suffix;
        var floodedName = 'culture_inondee_m2_' +
          floodSetting.suffix + '_' + areaCropSetting.suffix;

        areaBands.push(
          pixelArea.updateMask(cropMask.and(validRadar))
            .rename(observedName),
          pixelArea.updateMask(flood.and(cropMask))
            .rename(floodedName)
        );
      }
    }

    var sums = ee.Dictionary(ee.Image.cat(areaBands).reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: roi,
      scale: SCALE,
      crs: EXPORT_CRS,
      maxPixels: 1e13,
      tileScale: 8
    }));

    var areaProperties = {
      annee: year,
      periode: k + 1,
      date_debut: dates.start.format('YYYY-MM-dd'),
      n_images_S1: currentCollection.size(),
      n_observations_dynamicworld: cropCollection.size()
    };

    for (var vk = 0; vk < VV_THRESHOLDS.length; vk++) {
      var areaVv = VV_THRESHOLDS[vk];
      areaProperties['superficie_inondee_ha_' + areaVv.suffix] =
        numberOrZero(sums, 'inondee_m2_' + areaVv.suffix).divide(10000);

      for (var ck = 0; ck < CROP_THRESHOLDS.length; ck++) {
        var areaCrop = CROP_THRESHOLDS[ck];
        var observedM2 = numberOrZero(
          sums,
          'culture_observee_m2_' + areaVv.suffix + '_' + areaCrop.suffix
        );
        var floodedCropM2 = numberOrZero(
          sums,
          'culture_inondee_m2_' + areaVv.suffix + '_' + areaCrop.suffix
        );
        var prefix = areaVv.suffix + '_' + areaCrop.suffix;

        areaProperties['superficie_agricole_observee_ha_' + prefix] =
          observedM2.divide(10000);
        areaProperties['superficie_agricole_inondee_ha_' + prefix] =
          floodedCropM2.divide(10000);
        areaProperties['pourcentage_agricole_touche_' + prefix] =
          ee.Algorithms.If(
            observedM2.gt(0),
            floodedCropM2.divide(observedM2).multiply(100),
            null
          );
      }
    }

    areaRows = areaRows.merge(
      ee.FeatureCollection([ee.Feature(null, areaProperties)])
    );
  }
}

var pointSelectors = [
  'point_id', 'lon', 'lat', 'annee', 'periode', 'date_debut',
  'n_images_S1', 'n_observations_dynamicworld', 'S1_VV', 'S1_VH',
  'proba_culture',
  'inondation_m14', 'inondation_suivante_m14',
  'inondation_m16', 'inondation_suivante_m16',
  'inondation_m18', 'inondation_suivante_m18',
  'zone_agricole_c20', 'zone_agricole_c30', 'zone_agricole_c40'
];

var areaSelectors = [
  'annee', 'periode', 'date_debut',
  'n_images_S1', 'n_observations_dynamicworld',
  'superficie_inondee_ha_m14',
  'superficie_inondee_ha_m16',
  'superficie_inondee_ha_m18'
];

for (var av = 0; av < VV_THRESHOLDS.length; av++) {
  for (var ac = 0; ac < CROP_THRESHOLDS.length; ac++) {
    var areaPrefix = VV_THRESHOLDS[av].suffix + '_' +
      CROP_THRESHOLDS[ac].suffix;
    areaSelectors.push(
      'superficie_agricole_observee_ha_' + areaPrefix,
      'superficie_agricole_inondee_ha_' + areaPrefix,
      'pourcentage_agricole_touche_' + areaPrefix
    );
  }
}

print('Nombre de points', points.size());
print('Lignes attendues dans le CSV des points',
  points.size().multiply((END_YEAR - START_YEAR + 1) * N_DEKADS));
print('Lignes attendues dans le CSV des superficies',
  (END_YEAR - START_YEAR + 1) * N_DEKADS);

Export.table.toDrive({
  collection: pointRows,
  description: 'sensibilite_labels_points_VV_2019_2024',
  folder: DRIVE_FOLDER,
  fileNamePrefix: 'sensibilite_labels_points_VV_2019_2024',
  fileFormat: 'CSV',
  selectors: pointSelectors
});

Export.table.toDrive({
  collection: areaRows,
  description: 'sensibilite_superficies_VV_DW_2019_2024',
  folder: DRIVE_FOLDER,
  fileNamePrefix: 'sensibilite_superficies_VV_DW_2019_2024',
  fileFormat: 'CSV',
  selectors: areaSelectors
});

Map.centerObject(roi, 8);
Map.addLayer(roi, {color: 'red'}, 'Vallée du fleuve Sénégal', false);
print('Deux tâches CSV sont prêtes. Lancez-les dans l’onglet Tasks.');
