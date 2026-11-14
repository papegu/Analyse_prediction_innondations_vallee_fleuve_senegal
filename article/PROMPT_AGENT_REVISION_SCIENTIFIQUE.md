# Prompt pour Claude ou GitHub Agent

Tu es un assistant de révision scientifique spécialisé en télédétection et en évaluation de modèles spatiaux. Travaille dans le dépôt du manuscrit sur les inondations et l'exposition agricole dans la vallée du fleuve Sénégal.

## Objectif

Améliorer la rigueur scientifique du manuscrit `article/IJRS_flood_agriculture_revised.tex` à partir des données, scripts et résultats réellement présents dans le dépôt, ainsi que du script Google Earth Engine fourni après ce prompt. N'invente aucune observation de terrain, validation indépendante, référence bibliographique, paramètre ni résultat.

## Travail demandé

1. Lis le manuscrit, les scripts analytiques, les exports CSV utilisés par les résultats et le script GEE fourni. Identifie les fichiers effectivement disponibles et distingue clairement les données brutes, les proxys dérivés et les sorties d'analyse.
2. Vérifie la cohérence des méthodes, unités, agrégations spatiales et chiffres du manuscrit avec les fichiers disponibles. Ne remplace aucun chiffre sans recalcul reproductible et vérification de sa provenance.
3. Audite particulièrement dans le script GEE :
   - le calcul des superficies à 100 m à partir du masque Sentinel-1, notamment la signification de `pixels_inondes` et la conservation de la surface lors de la réduction d'échelle ;
   - le calcul à 30 m des deux bandes de fréquence et l'agrégation explicite des nombres de périodes inondées et valides ;
   - la disponibilité de la référence Sentinel-1 de saison sèche pour chaque année et le traitement des périodes sans observations ;
   - les projections, résolutions, masques, dates, dénominateurs et valeurs NoData.
   Si le script produit des valeurs approximatives ou ambiguës, corrige-le de manière explicite et vérifie les changements par un test ou une comparaison appropriée. N'affirme pas que les calculs sont validés par le seul fait que le script s'exécute.
4. Si aucune référence indépendante d'inondation, aucun plan d'échantillonnage documenté et aucune validation locale des cultures ne sont disponibles, conserve ces manques comme limites. Présente les métriques comme accord avec un label Sentinel-1 dérivé, les superficies comme exposition potentielle et non comme dommages, et les inférences sur les 200 sites comme non représentatives de toute la vallée.
5. Ne présente pas les performances comme une prévision opérationnelle si elles ne sont évaluées que contre le proxy satellitaire. Compare les modèles aux baselines, notamment la persistance, et rapporte sans sélection favorable les résultats spatiaux, temporels et espace-temps.
6. Vérifie que le résumé, les objectifs, les méthodes, les résultats, la discussion et la conclusion utilisent la même portée scientifique. Signale les éléments qui ne peuvent pas être résolus avec les données actuelles au lieu de les masquer.
7. Préserve les travaux préexistants et les changements non liés. Ne supprime ni ne remplace des fichiers ou résultats sans justification explicite.

## Livrables et validation

- Modifications minimales et traçables du manuscrit et, si nécessaire, du script GEE.
- Une courte synthèse des modifications, des vérifications exécutées et des limites restantes.
- Exécution des validations les plus ciblées disponibles. Si une validation échoue, indique clairement l'erreur et ne prétends pas qu'elle a réussi.
- Aucun commit ni push sans demande explicite de l'utilisateur.

## Script GEE à auditer

Le script ci-dessous est à auditer comme une spécification de traitement, pas comme une vérité de terrain ni comme une preuve de validité.

```javascript
/***************************************************************
 VALLÉE DU FLEUVE SÉNÉGAL
 CALCUL ALLÉGÉ DES INONDATIONS : 2019-2024

 Sorties intermédiaires :
 1. stats_inondations_2019.csv ... stats_inondations_2024.csv
 2. frequence_intermediaire_2019.tif ... _2024.tif

 Le raster annuel contient :
 - bande 1 : nombre de périodes inondées
 - bande 2 : nombre de périodes radar valides

 Les six années seront assemblées localement avec Python.
***************************************************************/

// =============================================================
// 1. PARAMÈTRES
// =============================================================

var DRIVE_FOLDER = 'GEE_VFS_SPI_10m';

var START_YEAR = 2019;
var END_YEAR = 2024;

var THRESHOLD_DB = -16;
var SCALE_STATS = 100;  // Statistiques surfaciques allégées
var SCALE_RASTER = 30;  // Raster de fréquence à 30 m
var EXPORT_CRS = 'EPSG:32628';

var N_PERIODS = 16;

// Zone d'étude
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

Map.centerObject(roi, 8);
Map.addLayer(roi, {color: 'red'}, 'Zone étude', false);

// =============================================================
// 2. SENTINEL-1 : VV UNIQUEMENT
// =============================================================

var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(roi)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains(
    'transmitterReceiverPolarisation', 'VV'
  ))
  .select('VV');

// Composite VV masqué si aucune image n'est disponible
function getComposite(start, end) {
  var col = s1.filterDate(start, end);

  var empty = ee.Image.constant(0)
    .rename('VV')
    .updateMask(ee.Image.constant(0));

  var image = ee.Image(ee.Algorithms.If(
    col.size().gt(0),
    col.median(),
    empty
  ));

  return {
    image: image,
    n: col.size()
  };
}

// Référence annuelle de saison sèche
function getDryReference(year) {
  var start = ee.Date.fromYMD(year, 3, 1);
  var end = ee.Date.fromYMD(year, 5, 16);

  return getComposite(start, end).image.lt(THRESHOLD_DB);
}

// =============================================================
// 3. TRAITEMENT D'UNE ANNÉE
// =============================================================

function processYear(year) {

  print('Préparation de l’année', year);

  var dry = getDryReference(year);

  var floodList = [];
  var validList = [];
  var statsList = [];

  for (var k = 0; k < N_PERIODS; k++) {

    var start = ee.Date.fromYMD(year, 6, 1)
      .advance(k * 10, 'day');

    var end = start.advance(10, 'day');

    var seasonEnd = ee.Date.fromYMD(year, 11, 1);

    end = ee.Date(ee.Algorithms.If(
      end.millis().gt(seasonEnd.millis()),
      seasonEnd,
      end
    ));

    var composite = getComposite(start, end);
    var vv = composite.image;

    // Observation radar disponible
    var valid = vv.mask()
      .rename('radar_valide')
      .clip(roi);

    // Même principe de détection que dans le script initial
    var water = vv.lt(THRESHOLD_DB);

    var flood = water
      .and(dry.not())
      .rename('inondation')
      .updateMask(valid)
      .clip(roi);

    floodList.push(flood);
    validList.push(valid);

    // ---------------------------------------------------------
    // Statistiques allégées à 100 m
    // Pas de connectedComponents ni de comptage des zones
    // ---------------------------------------------------------

    var area = ee.Image.pixelArea()
      .updateMask(flood)
      .rename('superficie_m2');

    var pixel = ee.Image.constant(1)
      .updateMask(flood)
      .rename('pixels_inondes');

    var reduced = area.addBands(pixel).reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: roi,
      scale: SCALE_STATS,
      crs: EXPORT_CRS,
      maxPixels: 1e10,
      tileScale: 4
    });

    var areaM2 = ee.Number(ee.Algorithms.If(
      reduced.contains('superficie_m2'),
      reduced.get('superficie_m2'),
      0
    ));

    var pixels = ee.Number(ee.Algorithms.If(
      reduced.contains('pixels_inondes'),
      reduced.get('pixels_inondes'),
      0
    ));

    statsList.push(ee.Feature(null, {
      annee: year,
      periode: k + 1,
      date_debut: start.format('YYYY-MM-dd'),
      n_images_S1: composite.n,
      pixels_inondes: pixels,
      superficie_inondee_m2: areaM2,
      superficie_inondee_ha: areaM2.divide(10000),
      echelle_calcul_m: SCALE_STATS
    }));
  }

  // -----------------------------------------------------------
  // EXPORT 1 : statistiques annuelles
  // -----------------------------------------------------------

  var statsYear = ee.FeatureCollection(statsList);

  Export.table.toDrive({
    collection: statsYear,
    description: 'stats_inondations_' + year,
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'stats_inondations_' + year,
    fileFormat: 'CSV'
  });

  // -----------------------------------------------------------
  // EXPORT 2 : raster annuel à deux bandes
  // -----------------------------------------------------------

  var floodImages = ee.ImageCollection.fromImages(
    floodList.map(function(img) {
      return img.unmask(0)
        .rename('periodes_inondees')
        .clip(roi);
    })
  );

  var validImages = ee.ImageCollection.fromImages(
    validList.map(function(img) {
      return img.unmask(0)
        .rename('periodes_valides')
        .clip(roi);
    })
  );

  var floodSum = floodImages.sum()
    .rename('periodes_inondees');

  var validSum = validImages.sum()
    .rename('periodes_valides');

  var annualRaster = floodSum
    .addBands(validSum)
    .clip(roi);

  Export.image.toDrive({
    image: annualRaster,
    description: 'frequence_intermediaire_' + year,
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'frequence_intermediaire_' + year,
    region: roi,
    scale: SCALE_RASTER,
    crs: EXPORT_CRS,
    maxPixels: 1e13,
    fileFormat: 'GeoTIFF',
    formatOptions: {
      cloudOptimized: true
    }
  });

  print('Exports préparés pour', year);
}

// =============================================================
// 4. PRÉPARER LES SIX ANNÉES
// =============================================================

for (var year = START_YEAR; year <= END_YEAR; year++) {
  processYear(year);
}

print('Terminé : 12 exports intermédiaires à lancer dans Tasks.');
```
