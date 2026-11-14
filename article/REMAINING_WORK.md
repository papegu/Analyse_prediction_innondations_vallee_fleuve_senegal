# Travaux restant à réaliser

## Analyses et données absentes

- **GeoTIFF SPI** : `SPI_2024-08-31_10m.tif` n'est pas présent dans le dépôt ni dans les dossiers locaux examinés. Les bandes annoncées, la projection, la résolution, les valeurs NoData/NaN/sentinelles et les distributions de pixels restent à vérifier. Le fichier ne doit pas être utilisé avant contrôle.
- **Définition SPI** : le script GEE de calcul n'est pas archivé. Les champs `SPI_30d` et `SPI_90d` du CSV sont documentés dans le manuscrit comme des z-scores de cumuls de pluie, et non comme un SPI conventionnel; cette description doit être confrontée au code source GEE avant soumission.
- **Sensibilité aux seuils** : les exports fournis permettent désormais de comparer les labels aux seuils VV $-14/-16/-18$ dB et les superficies aux combinaisons avec Dynamic World 0,20/0,30/0,40. Les rasters sources restent absents; aucune extrapolation à d'autres seuils, échelles ou méthodes n'est possible. Trois périodes sans acquisition radar sont exclues des résumés de superficie.
- **Validation de référence** : aucune vérité terrain indépendante et coïncidente (inondation, parcelles, culture, dommage) n'est fournie. Le proxy Sentinel-1 ne doit pas être présenté comme une validation de terrain.
- **Échantillonnage** : le code ou les métadonnées décrivant le tirage des 200 sites ne sont pas disponibles. La représentativité du bassin ne peut donc pas être affirmée.
- **Pertes agricoles** : les exports ne distinguent pas les cultures et ne fournissent ni parcelles effectivement détruites, ni rendements, ni prix de campagne vérifiés. Les simulations rizicoles restent hypothétiques.
- **Résolution** : les cartes GeoTIFF disponibles sont des cartes RGB à 10 m; elles ne permettent pas de reconstituer les rasters analytiques à 10 m ou les exports tabulaires à 100 m. Conserver ces niveaux séparés.

## Validation et reproductibilité

- La validation tamponnée ajoutée teste les mêmes cinq blocs spatiaux et les observations valides 2019--2023. Elle n'est pas une validation externe ni une preuve de généralisation hors de la zone échantillonnée.
- Pour étendre ou reproduire les sensibilités au-delà des combinaisons déjà exportées, archiver et vérifier dans Earth Engine les scripts, paramètres, composites, masques et sorties; ne soumettre aucune métrique simulée.
- Obtenir et archiver les références indépendantes permettant de mesurer omission/commission et de valider le masque agricole.
- Créer un environnement reproductible avec versions verrouillées. Le nouveau `requirements.txt` énumère les dépendances sans versions; il ne suffit pas à reproduire bit à bit les sorties.
- Le dépôt GitHub cité est publiquement visible; vérifier avant soumission la présence des versions finales de tous les scripts, données tabulaires et figures. Le dossier Drive affiche un listing, mais les droits de téléchargement externes n'ont pas été vérifiés.
- Confirmer avec tous les auteurs les déclarations de financement, conflits d'intérêts, contributions et disponibilité des données.

## Préparation éditoriale

- Convertir le manuscrit de `sn-jnl` vers le modèle et le style de références IJRS après consultation des consignes officielles. La page Taylor & Francis a répondu HTTP 403 pendant cette révision; aucune conformité complète n'est revendiquée.
- Vérifier les limites de longueur, les formats de fichiers, les résolutions et tailles des figures, les tableaux, les déclarations obligatoires et les règles de partage de données dans les consignes accessibles aux auteurs.
- Compiler à nouveau après la conversion au modèle IJRS et vérifier les références, les figures, les tableaux et les débordements de page.
