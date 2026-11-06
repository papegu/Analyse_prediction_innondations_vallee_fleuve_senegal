# Avis de relecture simule - International Journal of Remote Sensing

## Recommandation editoriale

**Revision majeure.** Le sujet entre dans le champ de la teledetection, mais les resultats actuels ne permettent pas encore de soutenir une performance de prevision generalisable ni une estimation de pertes agricoles observees. Cette recommandation est un avis de travail, pas une prediction de decision editoriale.

## Points majeurs et actions appliquees

1. **Le label radar n'est pas une verite terrain.** Le label reste un proxy Sentinel-1 au seuil VV de -16 dB. Le manuscrit le nomme explicitement ainsi et ne revendique plus de validation independante.
2. **La baseline persistence depasse les classifieurs en validation spatiale.** Sa moyenne AP est 0.240 (SD 0.125), contre 0.220 (SD 0.214) pour le meilleur classifieur, Random Forest. Son Brier moyen est meilleur que celui de la baseline de prevalence, contrairement au RF. Le resume, le tableau et les conclusions distinguent maintenant « meilleur classifieur » de « meilleure reference ».
3. **Le test temporel reutilise les sites.** Le texte rappelle que l'AP 2024 de la frequence historique par site (0.494) n'est pas une preuve de transfert spatial. Le test conjoint 2024 est mis en avant, avec son faible nombre de positifs.
4. **Les variables radar contemporaines sont liees au label.** Les methodes decrivent le modele complet comme une prediction conditionnelle du proxy et la variante sans Sentinel-1 comme une sensibilite, pas comme une preuve de prediction independante.
5. **Exposition et pertes economiques sont separees.** Les tableaux d'hectares sont des recoupements provisoires de masques. Les equations de pertes sont conditionnelles; aucune perte annuelle reelle n'est calculee faute de parcelles de riz identifiees, de taux de destruction observes, de rendements verifies et de prix de campagne.
6. **Couverture et contexte geographique.** Le tableau annuel inclut les periodes radar valides et le nombre moyen d'images Sentinel-1. Une figure du ROI et des 200 sites a ete ajoutee. Elle ne contient pas le fleuve ni les limites administratives, absents des donnees disponibles.
7. **Bibliographie et coherence interne.** L'entree de Lundberg et Lee est de type actes de conference, la pagination de Saarnak est corrigee, les caracteres du nom Lo sont restaures, et Sen1Floods11 ainsi que Tellman et al. sont ajoutes comme references contextuelles verifiees. Elles ne sont pas presentees comme validation utilisee dans cette etude.

## Conditions restantes avant soumission

- Constituer un jeu de reference independant et spatialement/temporellement stratifie pour mesurer les erreurs omission/commission du label radar; tester plusieurs seuils et distinguer eau permanente, rizieres et inondation temporaire.
- Fournir le script GEE d'origine, la description du tirage des 200 sites, les dates de reference, les projections/resolutions et les procedures de calcul des indices, du SPI et des valeurs sentinelles manquantes.
- Ajouter une validation avec blocs spatiaux tamponnes et validation par annee, intervalles d'incertitude et calibration; comparer formellement RF a persistence et a des modeles sans coordonnees.
- Obtenir une carte de reference du fleuve, des limites administratives et, si possible, du relief pour une carte d'etude interpretable et des covariables hydrologiques.
- Valider le masque Dynamic World contre des parcelles/cultures locales et quantifier sa sensibilite aux seuils. Les 10-m et 100-m resultats ne doivent pas etre presentes comme une seule mesure harmonisee.
- Pour estimer des pertes reelles, collecter les surfaces par culture effectivement endommagees, le stade phenologique, le degre de destruction, les rendements et prix bord-champ de la campagne. Les valeurs 5.5 t/ha et 160,000 FCFA/t restent des hypotheses fournies, non verifiees par une source institutionnelle dans les documents accessibles.
- Confirmer financement, conflits d'interets, contributions CRediT et declaration d'utilisation d'outils d'IA avec tous les auteurs.
- Convertir le fichier depuis le gabarit Springer Nature vers le gabarit et le style de references IJRS avant televersement. La page Taylor & Francis etait inaccessible lors de cette revision et aucun fichier `interact.cls` n'est present localement; les exigences exactes de formatage doivent etre confirmees sur les instructions officielles avant conversion.

## Resultats de calcul verifies

- Validation spatiale: persistence AP 0.240 +/- 0.125; RF 0.220 +/- 0.214; CatBoost 0.192 +/- 0.178; XGBoost 0.161 +/- 0.136.
- Test conjoint 2024: RF AP 0.379, persistence 0.333; RF Brier 0.037, persistence 0.031; RF sans variables S1 contemporaines AP 0.202.
- Scenario uniquement illustratif pour 1,500 ha de riz: a 5.5 t/ha, 160,000 FCFA/t et destruction totale, 8,250 t et 1,320,000,000 FCFA de valeur brute. A D=0.50, le resultat est 4,125 t et 660,000,000 FCFA.
- Les valeurs de rendement/prix et les scenarios +/-20% ne sont ni des statistiques officielles verifiees ni des observations de campagne.

## Mise a jour SPI et agriculture

La version LaTeX et le PDF final de 22 pages ont ete mis a jour apres les commentaires supplementaires. Dans le PDF, la documentation des cumuls CHIRPS et indices Z se trouve en Methodes p. 6-7; le masque agricole general est en Methodes p. 7; les equations de pertes sont en Methodes p. 8 et les parametres/scenarios hypothetique p. 9-10; les resultats d'exposition generale sont p. 13-14; les limites et la conclusion sont p. 19.

Les champs conserves sous les noms `SPI_30d` et `SPI_90d` sont decrits comme z-scores de cumuls glissants sur 30/90 jours, calcules relativement aux moyennes/ecarts-types du meme jour/mois sur 1991-2020, avec masque si ecart-type <= 1 mm. Ils ne sont pas presentes comme SPI conventionnels ajustes par Gamma. Les cumuls s'arretent a la date courante. Le referentiel fixe inclut toutefois 2020 pour quelques dates d'entrainement anterieures; les anciennes valeurs n'ont pas ete recalculees, et ce point est signale comme limite pour une simulation strictement prospective avant 2020.

Le code source GEE du SPI (`spiWindow`) n'a pas ete trouve dans le dossier: les details methodologiques ont ete rediges selon la specification fournie par l'auteur et restent a verifier contre le script source avant soumission. Le GEE d'impact agricole disponible emploie la classe generale Dynamic World `crops` avec seuil 0.30 et ne distingue aucune espece; les sorties sont donc nommees exposition agricole candidate, jamais riz/maïs/mil/sorgho inondes.

Les simulations rizicoles et leurs rendements/prix ont ete retirees des Resultats empiriques et placees en Methodes comme exemples hypothétiques. Aucune valeur experimentale ni metrique n'a ete modifiee.