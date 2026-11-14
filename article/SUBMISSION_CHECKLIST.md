# Liste de contrôle avant soumission à l'International Journal of Remote Sensing

## Manuscrit et résultats

- [ ] Convertir `IJRS_flood_agriculture_revised.tex` du modèle Springer Nature vers le modèle IJRS courant; vérifier les consignes officielles (non accessibles pendant cette révision, HTTP 403).
- [ ] Recompiler le manuscrit après conversion et corriger les références, tableaux, figures, liens et débordements.
- [ ] Vérifier que les résultats chiffrés du texte, des tableaux et des figures correspondent aux sources brutes archivées.
- [x] Maintenir la séparation entre validation spatiale non tamponnée, validation tamponnée, test temporel 2024 et test conjoint espace-temps.
- [x] Auditer les deux exports bruts de sensibilité, comparer les labels de référence au jeu principal par `point_id`/année/période, reproduire les agrégations d'aire et les contrôles de performance disponibles, et rapporter les sensibilités sans les assimiler à une validation indépendante.
- [x] Ne pas présenter les observations satellites comme vérité terrain, l'exposition comme dommage, ni les scénarios économiques comme pertes constatées.
- [ ] Faire vérifier la définition des champs SPI avec le script GEE source et inspecter le GeoTIFF SPI lorsqu'il sera fourni.

## Données, code et figures

- [ ] Vérifier qu'un lecteur externe peut télécharger les CSV et scripts depuis le dépôt GitHub et accéder aux données Google Drive.
- [ ] Constituer un test externe par événement avec labels d'inondation indépendants, dates et géoréférencement; documenter la provenance/licence, exclure tout événement du développement et évaluer séparément toute adaptation de domaine.
- [ ] Archiver les scripts GEE sources, les versions exactes, paramètres, actifs requis, projection, résolution et méthodes de rééchantillonnage.
- [ ] Ajouter un environnement Python verrouillé et tester les commandes du [README](./README.md) dans un environnement propre.
- [ ] Confirmer que les légendes identifient la période, le système de coordonnées, l'échelle, les sources et les seuils pertinents.
- [ ] Distinguer les résultats 10 m des exports à 100 m; ne pas traiter les tuiles RGB comme des rasters analytiques.
- [x] Obtenir une validation indépendante hydrologique et agricole ou maintenir clairement les limites actuelles. Les limites sont explicites; les données indépendantes restent à obtenir.

## Déclarations et auteurs

- [ ] Confirmer auprès de tous les auteurs la liste et l'ordre des auteurs, affiliations, courriels et contributions.
- [ ] Confirmer les déclarations de financement et de conflits d'intérêts présentes dans le manuscrit.
- [ ] Compléter les déclarations de disponibilité des données et du code avec des liens testés et des instructions d'accès.
- [ ] Vérifier les exigences IJRS concernant les remerciements, les contributions, les données, le code et toute déclaration d'usage d'outils d'IA.
- [ ] Obtenir toutes les autorisations de réutilisation requises pour les figures et données tierces.

## Fichiers à préparer

- [ ] Manuscrit source et PDF compilé selon les exigences IJRS.
- [ ] Figures séparées dans les formats et résolutions acceptés.
- [ ] Tableaux éditables si demandé par la revue.
- [ ] Fichiers supplémentaires contenant protocoles, métriques par bloc et métadonnées nécessaires à la reproductibilité.

## Contrôle local complémentaire (6 novembre 2026)

- Les 20 clés de citation du manuscrit révisé ont toutes une entrée dans `references.bib`; cinq entrées bibliographiques ne sont pas citées. Cela vérifie la cohérence des clés, pas l'exactitude des références ni leur adéquation aux affirmations.
- Les chiffres consultés ont été comparés aux CSV disponibles : AP de la validation tamponnée, AP du test conjoint 2024, ablation sans Sentinel-1 contemporain et bornes annuelles de superficie agricole moyenne. Ce contrôle ciblé ne remplace pas un audit de chaque résultat, tableau et figure.
- Les deux exports bruts de sensibilité sont maintenant présents et l'audit local passe. Les agrégations vérifiées sont réintroduites dans la copie révisée; elles quantifient une sensibilité aux seuils des proxys satellitaires et ne constituent pas une validation indépendante.
- Les quatre GeoTIFF du dossier racine sont des copies exactes des quatre tuiles dans `article/data_gee_before/` (SHA-256 identiques par tuile). Les métadonnées déjà inspectées les décrivent comme des cartes d'affichage RGB à trois bandes, uint8, EPSG:32628 et 10 m; elles ne permettent pas de recalculer les seuils VV ou les probabilités Dynamic World.
- Aucun raster SPI ni jeu de référence terrain indépendant n'a été identifié dans les fichiers inspectés. Les CSV de sensibilité aux seuils sont présents et audités; une validation indépendante hydrologique et agricole nécessite toujours des références coïncidentes.
- La vérification externe du contenu des références, des consignes IJRS, des droits d'accès aux données et de toutes les affirmations n'est pas achevée. Cette checklist n'est pas une approbation de soumission.

## Mise à jour reviewer (14 novembre 2026)

- La copie PDF fournie correspond à une source utilisant toujours `sn-jnl`, pas au modèle de soumission Taylor & Francis/IJRS.
- Le manuscrit révisé rapporte les métriques VV/Dynamic World reproduites depuis les exports bruts; les tableaux décrivent la sensibilité des proxys et non leur exactitude terrain.
- L'audit des exports bruts passe et reste strictement en lecture seule; il ne calcule pas de vérité terrain indépendante.
- La source actuelle a été recompilée en un PDF distinct de 25 pages, sans écraser les sorties antérieures; citations et références sont résolues. Le format reste Springer `sn-jnl`, à convertir avant soumission.
- Les données Kaggle candidates ne doivent pas être considérées comme validation avant vérification des événements, labels, géoréférencement, chevauchement avec les données d'entraînement et licence.

## Candidats Kaggle pour une évaluation externe (repérage du 14 novembre 2026)

Ces dépôts sont des candidats de benchmark, pas des labels de vérité terrain déjà validés pour la vallée du Sénégal. Inspecter le contenu et les métadonnées avant de télécharger ou d'intégrer les données.

- [ ] **ETCi 2021 Competition on Flood Detection** — [fiche Kaggle](https://www.kaggle.com/datasets/aninda/etci-2021-competition-on-flood-detection). La fiche indique des tuiles VV/VH Sentinel-1, des masques issus de 54 GeoTIFF étiquetés, des partitions de compétition et une licence « U.S. Government Works ». Candidat le plus concret pour un test externe de cartographie, sous réserve de récupérer les GeoTIFF sources géoréférencés et de documenter la provenance des labels. Les tuiles seules ne sont pas directement compatibles avec le classifieur tabulaire actuel.
- [ ] **Sen1Floods11 Dataset** — [fiche Kaggle](https://www.kaggle.com/datasets/robertomarinoformica/sen1floods11-dataset). La version Kaggle consultée fait environ 34,8 GB et indique une licence « Unknown »; ne pas redistribuer ni intégrer avant clarification des droits. Vérifier les masques manuels/weak labels, leurs événements et les métadonnées géographiques.
- [ ] **SEN12FLOOD: Flood Detection Dataset** — [fiche Kaggle](https://www.kaggle.com/datasets/rhythmroy/sen12flood-flood-detection-dataset). La fiche décrit des séries co-enregistrées Sentinel-1/2 et une couverture multi-régionale, mais indique une licence « Other (specified in description) » et ne décrit pas assez précisément la disponibilité/provenance des masques. N'utiliser qu'après inspection du contenu réel, des dates, des lieux et des labels.
- [ ] Ne pas utiliser comme référence le dépôt Kaggle « Satellite Imagery Data for Senegal » sans audit préalable : la fiche repérée n'expose pas de description ni de labels d'inondation vérifiables.
- [ ] Pour une validation indépendante pertinente pour la vallée, rechercher en priorité des polygones d'étendue d'inondation datés, géoréférencés et interprétés indépendamment, idéalement accompagnés de Sentinel-1 VV/VH bruts coïncidents. Ajouter séparément des parcelles/cultures et observations de dommages ou rendements si des affirmations agricoles sont visées. Aucun benchmark Kaggle repéré ne remplace ces références locales.
- [ ] Séparer les partitions par événement/région (jamais par tuile aléatoire), contrôler tout chevauchement spatial/temporel avec l'entraînement, harmoniser résolution/CRS et comparer les sorties au niveau masque/pixel ou après échantillonnage explicite des sites. Rapporter les scores par événement et l'incertitude; ne pas mélanger ces scores avec la validation tabulaire actuelle.
