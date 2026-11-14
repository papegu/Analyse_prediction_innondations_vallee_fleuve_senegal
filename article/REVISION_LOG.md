# Journal de révision

## Sauvegarde et périmètre

- Une copie exacte du fichier LaTeX présent avant cette révision a été créée sous `springer_flood_agriculture.pre_revision.tex`.
- Le fichier source `springer_flood_agriculture.tex` et ses modifications préexistantes n'ont pas été écrasés.
- Les corrections ont été apportées dans la copie `IJRS_flood_agriculture_revised.tex`. Cette copie conserve la classe Springer Nature `sn-jnl`; elle n'est pas encore convertie au format Taylor & Francis/IJRS.

## Contrôle reviewer initial (14 novembre 2026)

- Contrôle de la copie PDF et de sa source LaTeX. La source conserve toujours la classe Springer Nature; le PDF ne constitue donc pas un fichier de soumission conforme au format IJRS.
- Lors de ce premier contrôle, les sources `sensibilite_labels_points_VV_2019_2024.csv` et `sensibilite_superficies_VV_DW_2019_2024.csv` n'étaient pas visibles dans le workspace. Les résultats ont été temporairement retirés de la copie révisée en attendant leur remise et leur audit.
- Conservation des CSV dérivés préexistants, sans les écraser ni les présenter comme des résultats vérifiés. Les comparaisons déjà possibles dans le jeu principal au seuil de référence ne remplacent pas la vérification des exports bruts ni une validation indépendante.
- Ajout de `audit_sensibilite_seuils.py`, outil en lecture seule qui vérifie noms/colonnes, périodes, volumes, valeurs manquantes, clés, classes binaires, métadonnées et concordance des labels $-16$ dB par \texttt{point\_id}, année et période. L'outil ne modifie aucun fichier.
- Aucun raster externe n'a été téléchargé, aucune tâche Earth Engine n'a été lancée et aucune installation n'a été effectuée. La recherche Kaggle autorisée sert uniquement à recommander des jeux candidats; elle ne constitue pas un résultat de validation.
- Compilation de la nouvelle source : PDF de travail de 23 pages créé sous `IJRS_flood_agriculture_revised_reviewed.pdf`; références et citations résolues, aucune erreur LaTeX fatale. Le PDF fourni initialement a été conservé sans modification.
- À cette première étape, l'exécution sur le dépôt réel était bloquée explicitement par l'absence du premier export brut. Aucun fichier n'a été écrit par le script.

### Rectification du journal antérieur

Le constat d'absence ci-dessus décrit l'état initial et a été supersédé après que l'utilisateur a exécuté l'audit et rendu les deux exports bruts disponibles dans le dossier. L'analyse et les vérifications consignées dans la suite de ce journal ont alors été reproduites à partir de ces sources; les calculs confirmés sont rétablis dans la copie révisée. Leur interprétation reste limitée à une sensibilité des proxys satellitaires, sans validation indépendante.

## Mise à jour après exécution de l'audit

- Les deux exports bruts sont présents; `audit_sensibilite_seuils.py` passe. Les labels de référence $-16$ dB concordent avec le jeu principal sur les clés valides \texttt{point\_id}/année/période; les métadonnées des périodes et les pourcentages de superficies sont contrôlés.
- Les trois périodes sans acquisition Sentinel-1 (2021-10-29, 2022-10-29 et 2024-10-29) sont exclues des agrégats d'aire et interprétées comme non observées. Les résumés dérivés sont reproduits à la précision flottante; les fichiers d'origine n'ont pas été écrasés.
- Réintégration dans le manuscrit des tableaux VV/Dynamic World et des résultats de performance confirmés. La discussion et les limites précisent que les seuils modifient les proxys, mais que l'audit n'est pas une validation terrain indépendante.
- Mise à jour du README et de la checklist pour refléter la présence des sources et le passage de l'audit.
- Compilation terminée après cette mise à jour sous `IJRS_flood_agriculture_revised_audited_20261114.pdf` (25 pages), sans écraser les PDF préexistants. BibTeX, citations et références sont résolus; quelques avertissements de mise en page `Underfull \hbox` restent non bloquants. Le document reste au modèle Springer `sn-jnl`, et ne constitue pas un fichier de soumission IJRS.

## Modifications et vérifications

- Clarification des 19 200 observations comme 200 sites répétés sur 96 périodes, sans les assimiler à 19 200 unités spatiales indépendantes.
- Maintien de la distinction entre le proxy d'eau Sentinel-1, l'inondation indépendante, l'exposition agricole, les dommages aux cultures et les pertes économiques.
- Correction d'un bloc de code Markdown accidentellement inclus dans la source LaTeX de travail et nettoyage d'une ligne de tableau résiduelle.
- Analyse des deux exports de sensibilité fournis : 19 200 labels (20 colonnes; 200 points x 96 périodes) et 96 lignes de superficies (35 colonnes). Les labels à $-16$ dB concordent exactement avec le CSV principal sur les 14 519 labels courants et 13 583 cibles suivantes valides, après jointure sur \texttt{point\_id}, année et période; dates et coordonnées concordent aussi.
- Contrôle des valeurs manquantes : 4 681 valeurs absentes dans chacun des champs S1_VV, S1_VH et labels courants; 5 617 dans chacune des colonnes de labels suivants; aucun manque dans les autres champs du fichier de points. Les neuf colonnes de pourcentage de superficies ont chacune trois valeurs manquantes, correspondant aux trois périodes sans image radar; les champs d'aire à zéro dans ces lignes sont traités comme non observés.
- Calcul des labels aux seuils VV $-14/-16/-18$ dB et des superficies aux neuf combinaisons Dynamic World 0,20/0,30/0,40. Les résumés excluent les périodes 2021-10-29, 2022-10-29 et 2024-10-29, sans acquisition Sentinel-1, dont les superficies exportées à zéro ne représentent pas des observations nulles. Les sorties agrégées sont `sensibilite_labels_resume_annuel.csv`, `sensibilite_superficies_resume_annuel.csv` et `sensibilite_superficies_resume_global.csv`.
- Réévaluation des cinq classifieurs et des références persistence/fréquence historique avec les mêmes blocs, partitions temporelles, prédicteurs et paramètres. Le résultat de référence à $-16$ dB reproduit exactement les AP et Brier spatiaux et temporels existants. Les 42 lignes de résultats sont dans `sensibilite_performances_modeles.csv`; la persistance dépasse le Random Forest en AP spatiale aux trois seuils.
- Contrôle de cohérence des superficies : la combinaison de référence $-16$ dB/0,30 concorde avec l'export d'exposition 10 m existant à moins de $2\times10^{-8}$ ha. La série historique distincte à 100 m diffère des nouvelles superficies à 10 m d'une moyenne absolue de 11 627 ha sur les 93 dates comparables; elle n'a pas été remplacée ni fusionnée, et cette différence n'est pas attribuée au seuil seul.
- Ajout d'une validation spatiale tamponnée, sans remplacement des résultats initiaux. Le rayon de 15,97 km correspond au 90e percentile empirique des distances géodésiques au plus proche voisin des 200 sites (médiane : 7,87 km; Q1--Q3 : 5,19--12,33 km).
- Ajout du script `analyse_validation_spatiale_buffer.py` et des sorties `resultats_inondations/validation_spatiale_buffer_par_bloc.csv` et `resultats_inondations/validation_spatiale_buffer_resume.csv`.
- Résultats tamponnés sur cinq blocs : RF AP = 0,218 (écart-type 0,216), persistance AP = 0,240 (0,125); Brier RF = 0,033 (0,011), persistance = 0,033 (0,009). Onze exclusions site-bloc au total; effectifs détaillés dans le manuscrit et les CSV.
- Ajout d'une note sur le GeoTIFF SPI absent et sur l'impossibilité d'en vérifier les bandes, unités, valeurs NoData ou statistiques.
- Réécriture du README pour documenter les entrées, scripts, commandes, sorties et limites; ajout de `requirements.txt` non verrouillé.
- Création de `REMAINING_WORK.md`, `REVIEWER_RESPONSE_PREPARATION.md` et `SUBMISSION_CHECKLIST.md`.
- Les GeoTIFF disponibles ont été inspectés avec Rasterio : les tuiles d'exposition et d'inondation sont des images RGB uint8 à trois bandes, en EPSG:32628 et à 10 m; elles ne contiennent pas les bandes sources requises pour les tests de seuil.
- Le dépôt GitHub cité est public selon l'API GitHub. La page du dossier Drive s'ouvre et présente une liste de fichiers, mais la possibilité de télécharger chaque fichier avec les droits d'un lecteur tiers n'a pas été confirmée.
- La page officielle des consignes IJRS a renvoyé HTTP 403. La conformité éditoriale complète n'est donc pas attestée.

## Validation technique

- Le script de validation tamponnée a été exécuté avec succès sur le CSV local.
- Les fichiers de sensibilité ont été contrôlés pour les colonnes, périodes, valeurs manquantes, clés dupliquées et cohérence des classes; les 93 périodes avec acquisition ont servi aux moyennes de superficies. Aucun fichier source ni export existant n'a été écrasé.
- Le calcul des modèles à $-16$ dB reproduit les résultats archivés avec les mêmes partitions et paramètres. Aucune tâche Earth Engine, installation de dépendance ni recherche externe n'a été effectuée.
- Le manuscrit révisé a été compilé dans un répertoire temporaire en PDF (25 pages, A4), sans écraser le PDF préexistant; les références sont résolues et le journal final ne contient aucun débordement horizontal (`Overfull \hbox`).
- Contrôle local complémentaire (6 novembre 2026) : les clés de citation du manuscrit révisé ont toutes une entrée BibTeX; les chiffres clés consultés concordent avec leurs CSV de résultats. Les quatre tuiles GeoTIFF du dossier racine sont identiques aux copies de `article/data_gee_before/`; ce sont des images RGB d'affichage, pas les rasters analytiques nécessaires aux sensibilités. Aucun jeu de référence terrain indépendant n'a été repéré dans les fichiers inspectés. La vérification externe des références et l'audit exhaustif des résultats restent à faire.
