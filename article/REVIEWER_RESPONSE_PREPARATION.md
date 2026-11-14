# Préparation aux réponses des évaluateurs

Les formulations ci-dessous sont des bases de réponse à adapter aux commentaires réels. Elles ne doivent pas laisser entendre qu'une donnée ou une validation manquante a été obtenue.

## 1. La cible Sentinel-1 n'est pas une vérité terrain

**Critique probable :** le modèle apprend une classe issue du même système satellitaire que plusieurs prédicteurs et ne démontre pas la prévision d'inondations confirmées.

**Réponse possible :** « Nous sommes d'accord. Nous avons renommé la cible en proxy Sentinel-1 d'eau/inondation potentielle, explicité le chevauchement avec les prédicteurs contemporains et ajouté l'ablation sans Sentinel-1 contemporain. Nous ne présentons pas cette expérience comme une validation indépendante. Une validation hydrologique coïncidente reste nécessaire. »

## 2. Dépendance au protocole spatial

**Critique probable :** les blocs spatiaux ne garantissent pas une séparation suffisante entre sites proches.

**Réponse possible :** « Nous avons ajouté une validation tamponnée en réutilisant les cinq blocs et en excluant les sites d'entraînement situés à moins de 15,97 km des sites de test. Ce rayon est le 90e percentile empirique de l'espacement au plus proche voisin; les effectifs et métriques par bloc sont fournis. La persistance conserve une AP moyenne supérieure (0,240 contre 0,218), ce qui ne permet pas de revendiquer une supériorité générale du Random Forest. »

## 3. Sensibilité aux seuils de détection

**Critique probable :** les superficies dépendent du seuil VV et du seuil de probabilité Dynamic World.

**Réponse possible :** « Nous avons calculé une sensibilité aux seuils exportés : VV à $-14/-16/-18$ dB et probabilité Dynamic World à 0,20/0,30/0,40, en distinguant labels ponctuels et superficies agrégées. Les résumés de superficie excluent trois périodes sans acquisition radar. Il s'agit d'une sensibilité au protocole satellitaire, pas d'une validation indépendante; les rasters sources et des références hydrologiques/agricoles coïncidentes restent nécessaires pour étendre et valider l'analyse. »

## 4. Généralisation temporelle et espace-temps

**Critique probable :** le test 2024 réutilise des sites d'entraînement.

**Réponse possible :** « Le test chronologique 2024 est rapporté séparément et n'est pas qualifié de transfert spatial. Nous présentons également le test conjoint futur-et-sites-blocs-exclus (80 positifs), où le Random Forest obtient une AP de 0,379 contre 0,333 pour la persistance, mais un Brier plus élevé (0,037 contre 0,031). Les deux métriques ne soutiennent pas une supériorité générale. »

## 5. Exposition agricole versus dommages

**Critique probable :** la classe Dynamic World `crops` et l'intersection avec l'eau ne prouvent ni une culture effectivement implantée ni sa destruction.

**Réponse possible :** « Nous avons remplacé les formulations de dommages par exposition potentielle de surfaces agricoles candidates. Dynamic World ne fournit pas l'espèce cultivée ni un relevé de parcelle; nous ne calculons donc aucun dommage observé, rendement perdu ou perte économique annuelle. Les scénarios rizicoles sont explicitement hypothétiques. »

## 6. SPI et période de référence

**Critique probable :** les champs `SPI_30d`/`SPI_90d` peuvent ne pas être des SPI standardisés selon une distribution de probabilité.

**Réponse possible :** « Le manuscrit les décrit comme des z-scores de cumuls glissants selon la spécification disponible, et non comme un SPI conventionnel. Le script GEE de calcul et le GeoTIFF SPI annoncé ne sont pas archivés; nous ne revendiquons pas une vérification indépendante des bandes. Nous signalons aussi que la climatologie fixe 1991--2020 inclut 2020 pour certaines dates antérieures. »

## 7. Format éditorial et pièces de soumission

**Critique probable :** le source utilise un modèle Springer Nature plutôt que le style IJRS.

**Réponse possible :** « La copie de travail a été révisée scientifiquement, mais la conversion éditoriale reste à faire. La page officielle Taylor & Francis était inaccessible (HTTP 403) lors de cette révision; nous appliquerons le modèle et les consignes IJRS dès que les exigences courantes auront été consultées. »
