# Rapport de revision scientifique avant soumission

## Portee de la revision

Le manuscrit a ete corrige a partir des CSV 2019-2024, des six exports annuels d'exposition agricole, des quatre tuiles GeoTIFF, des scripts et du classeur de commentaires. La periode 2018 n'est pas couverte par les fichiers disponibles. Le manuscrit reste dans le gabarit Springer Nature; une soumission Taylor & Francis devra etre reformatee selon les consignes du journal cible.

## Corrections integrees

- Le titre et le resume distinguent detection satellitaire, exposition potentielle et dommages agricoles verifies.
- Les six CSV agricoles sont analyses: 96 periodes, dont 93 avec acquisitions Sentinel-1. Les hectares des trois periodes sans image sont maintenant manquants, jamais codes comme zero.
- Le tableau annuel rapporte la moyenne et le maximum par periode valide et la fraction ponderee des cultures candidates observees exposees. Les sommes en hectares-periodes ne sont pas presentees comme des superficies saisonnieres uniques.
- Les calculs agricoles a 10 m sont separes des statistiques de superficie inondee a 100 m.
- La comparaison inclut persistance, frequence historique par site et un modele sans variables Sentinel-1 contemporaines.
- Les performances sont qualifiees d'exploratoires; les conclusions reconnaissent la faible transferabilite, l'incertitude entre blocs et l'absence de donnees de revenus, rendement et dommages.
- Une methode conditionnelle de pertes de production et de valeur brute a ete ajoutee avec controle des unites, definitions de variables et rappel que l'exposition satellitaire n'est pas une destruction.
- La simulation rizicole de 1 500 ha et les sensibilites au rendement, au prix paddy et au coefficient de destruction sont explicitement hypothetique; aucun resultat de perte annuelle n'est attribue a la vallee.
- Les methodes non executees (modeles de comptage, segmentation d'image, prediction de dommages) ont ete retirees des resultats et reservees aux travaux futurs.

## Resultats a retenir avec prudence

- Parmi les classifieurs, Random Forest a la meilleure AP en validation spatiale (0.220, ecart-type 0.214), mais la persistance fait mieux (0.240, ecart-type 0.125). Le RF n'est donc pas le meilleur modele global dans cette validation.
- En test conjoint 2024 et sites retenus, Random Forest atteint AP 0.379, contre 0.333 pour la persistance. Son score de Brier est cependant moins bon (0.037 contre 0.031).
- Sans predicteurs Sentinel-1 contemporains, l'AP Random Forest passe a 0.202 sur ce test conjoint. Le signal predictif est donc lie en partie au capteur et a la definition de la cible.
- La frequence historique par site atteint AP 0.494 sur le test temporel, mais ne peut pas etre appliquee aux sites jamais vus. Le test temporel n'est pas une preuve de generalisation spatiale.
- Les hectares exposes sont une intersection conditionnelle entre le seuil VV de -16 dB et la classe Dynamic World "crops" a probabilite >= 0.30. Ils ne mesurent ni pertes de recolte, ni baisse de rendement, ni revenu agricole.

## Travaux indispensables avant soumission

1. Valider les labels d'inondation sur un echantillon spatialement et temporellement stratifie, avec reference independante et matrice de confusion; tester plusieurs seuils radar et l'eau permanente.
2. Documenter le plan de selection des 200 points, les dates de reference, les reprojections et le calcul des covariables. Ajouter le script GEE source, l'asset ou une archive partageable.
3. Executer une validation imbriquee avec reglage des hyperparametres dans les seuls plis d'entrainement, validation leave-one-year-out, blocs spatiaux avec tampons, intervalles d'incertitude par site et calibration probabiliste.
4. Tester la sensibilite du masque agricole (au moins seuils 0.20, 0.30 et 0.50), confronter Dynamic World a une reference locale de riz/cultures et documenter les ecarts d'echelle entre CHIRPS et les produits optiques/radar.
5. Ajouter des variables de relief et d'hydrologie (HAND, distance au fleuve, pente, niveaux/debits si disponibles), puis mesurer l'apport sans coordonnees geographiques.
6. Obtenir des observations de terrain, rendements, superficies par culture, prix ou revenus pour pretendre modeliser les pertes economiques des cultivateurs.
7. Une carte du ROI et des 200 sites a ete ajoutee. Ajouter encore le fleuve et les limites administratives a partir de couches geographiques fiables; verifier lisibilite, ordre et references de toutes les figures/tableaux.
8. Remplacer les declarations de financement, contributions CRediT, conflits d'interets et usage d'outils d'IA par des informations approuvees par les auteurs; ne pas les deviner.

## Fichiers AgriSmart

Les deux fichiers nommes `.xls` sont des copies identiques de CSV (2 200 lignes, 12 colonnes), et non des classeurs Excel. Les champs sont des nutriments, conditions agroclimatiques, cultures, source et zone; aucun champ de rendement, prix, revenu ou perte n'a ete trouve. Le champ `source` inclut `SMOTE` et `Variation_Gaussienne_ISRA`: ce jeu synthetique ne doit pas servir de verite terrain ni etre joint aux labels satellitaires sans provenance, unite d'observation et validation documentees.

## Rendement et prix provisoires

Les valeurs de 5,5 t/ha et 160 000 FCFA/t ont ete conservees comme parametres de scenario fournis pour la revision, et non comme statistiques officielles verifiees. Aucune nouvelle reference n'a ete ajoutee pour les soutenir: une recherche web accessible n'a pas permis de confirmer ces valeurs dans une publication SAED, ISRA, ANSD ou un bulletin de marche daté. Avant soumission, joindre une source primaire precise et aligner la campagne, la zone, la qualite du paddy et le prix bord-champ. Le prix du paddy ne doit pas etre confondu avec celui du riz blanc decortique.

Les variables `SPI_30d` et `SPI_90d` sont utilisees comme champs exportes mais leur calcul et leur periode de reference ne sont pas documentes. Le manuscrit signale maintenant cette limite; le script source GEE reste necessaire pour rendre leur interpretation reproductible.

## Revision SPI et perimetre agricole - PDF final

PDF compile le 6 novembre 2026, 22 pages. Les pages ci-dessous se rapportent a `springer_flood_agriculture_final.pdf`.

| Modification | Section du manuscrit | Page(s) |
|---|---|---:|
| Resume sans estimation de pertes observees ni rendement rizicole rapporte comme resultat | Abstract | 1 |
| Definition de `P_30d`, `P_90d`, z-score `SPI_30d`/`SPI_90d`, reference 1991-2020, `STD_MIN_WINDOW=1 mm`, ecart avec le SPI Gamma | Methodes, CHIRPS | 6-7 |
| Role de court terme du Z30 et contexte saisonnier du Z90; limites pour la disponibilite prospective et code source absent | Methodes, CHIRPS et fuite temporelle | 7-8 |
| Masque general Dynamic World `crops` avec seuil 0.30; absence de classification riz/mais/mil/sorgho et correspondance des noms internes/exportes | Methodes, masque agricole | 7 |
| Correspondance entre `inondation_S1` et `inondation_S1_suivante`; exposition agricole definie par l'intersection des masques | Methodes, aire et cible | 8 |
| Equations conditionnelles de production et valeur brute; parametres riz et tableaux de sensibilite explicitement hypothetiques, deplaces hors des resultats empiriques | Methodes, pertes conditionnelles | 8-10 |
| Hectares interpretes comme exposition generale des surfaces agricoles candidates, sans pertes ni cultures specifiques | Resultats, exposition agricole | 13-14 |
| Limites du proxy, du SPI simplifie, de l'absence de source GEE SPI, de l'absence de dommage observe et du referentiel 1991-2020 | Limites | 19 |
| Conclusion sans estimation economique annuelle | Conclusion | 19 |

Les valeurs experimentales de classification, les statistiques d'exposition et les fichiers de donnees n'ont pas ete recalcules. Le code `spiWindow`/`STD_MIN_WINDOW` n'a pas ete retrouve dans les fichiers du projet; la methodologie SPI ci-dessus suit les instructions techniques fournies pour cette revision et n'est pas une verification du script GEE source. Le script doit etre archive avec la version exacte avant soumission.

La standardisation rolling de chaque date utilise une climatologie fixe 1991-2020. Les cumuls journaliers n'utilisent aucune pluie apres la date de prediction, mais pour des lignes d'entrainement avant 2020, la climatologie fixe contient une annee posterieure a la date. La limitation est explicitee dans le manuscrit; les valeurs existantes n'ont pas ete modifiees. Une evaluation strictement prospective avant 2020 devrait recalculer la normale a chaque origine, ce qui constituerait une nouvelle experience.