# Explications des contrôles qualité

## COMP_01 : age manquant (critique)

- **Cause probable** : Âge absent à la saisie ou perdu lors d'une transformation de données. Sur 400 lignes en erreur, 0 sont déjà dans les données brutes et 400 sont apparues ensuite.
- **Impact** : Les analyses par tranche d'âge et les modèles qui utilisent l'âge excluent ces lignes ou sont faussés. Taux observé : 0,97 %, seuil d'alerte : 0,5 %.
- **Correction suggérée** : Retrouver l'âge dans la source ; sinon le coder explicitement comme inconnu et bloquer les imports où il est vide. Lignes à examiner en premier (row_id) : 219, 302, 408, 801, 888.
- *Chiffres vérifiés : oui*

## VALID_01 : age hors plage 18-100 (critique)

- **Cause probable** : Erreur de saisie, ou valeur technique utilisée à la place de l'âge. Sur 205 lignes en erreur, 5 sont déjà dans les données brutes et 200 sont apparues ensuite.
- **Impact** : Des âges impossibles faussent les moyennes et les tranches d'âge. Taux observé : 0,49 %, seuil d'alerte : 0,1 %.
- **Correction suggérée** : Rejeter à l'import les âges hors de la plage autorisée et corriger à la source. Lignes à examiner en premier (row_id) : 23, 366, 867, 1317, 1519.
- *Chiffres vérifiés : oui*

## COH_01 : duration = 0 mais y = yes (critique)

- **Cause probable** : Durée d'appel effacée ou mal enregistrée alors que la souscription est notée. Sur 100 lignes en erreur, 0 sont déjà dans les données brutes et 100 sont apparues ensuite.
- **Impact** : Le lien entre durée d'appel et souscription est faussé, ce qui peut tromper un modèle. Taux observé : 0,24 %, seuil d'alerte : 0,1 %.
- **Correction suggérée** : Vérifier ces lignes dans le système d'origine et corriger la durée ou le résultat. Lignes à examiner en premier (row_id) : 1115, 1190, 8884, 9448, 10354.
- *Chiffres vérifiés : oui*

## COH_02 : pdays renseigné mais previous = 0 (critique)

- **Cause probable** : Nombre de contacts précédents non mis à jour alors qu'un délai depuis le dernier contact existe. Sur 100 lignes en erreur, 0 sont déjà dans les données brutes et 100 sont apparues ensuite.
- **Impact** : L'historique de contact des clients est sous-estimé. Taux observé : 0,24 %, seuil d'alerte : 0,1 %.
- **Correction suggérée** : Recalculer le nombre de contacts précédents à partir de l'historique. Lignes à examiner en premier (row_id) : 24800, 26195, 27479, 28791, 29307.
- *Chiffres vérifiés : oui*

## COH_03 : pdays = 999 mais previous > 0 (majeure)

- **Cause probable** : Code de substitution du délai utilisé alors que des contacts précédents sont enregistrés, déjà présent dans la source. Sur 4133 lignes en erreur, 4110 sont déjà dans les données brutes et 23 sont apparues ensuite.
- **Impact** : Les statistiques sur le délai depuis le dernier contact sont peu fiables pour ces clients. Taux observé : 9,99 %, seuil d'alerte : 1 %.
- **Correction suggérée** : Documenter l'incohérence et traiter ces lignes à part dans les analyses sur le délai. Lignes à examiner en premier (row_id) : 24014, 24020, 24077, 24103, 24114.
- *Chiffres vérifiés : oui*

## COMP_02 : job manquant (majeure)

- **Cause probable** : Profession non renseignée, ou colonne mal alimentée lors de l'import. Sur 800 lignes en erreur, 0 sont déjà dans les données brutes et 800 sont apparues ensuite.
- **Impact** : Les segmentations par profession sous-représentent ces clients. Taux observé : 1,93 %, seuil d'alerte : 1 %.
- **Correction suggérée** : Compléter depuis la source, ou utiliser la modalité unknown déjà prévue plutôt qu'une valeur vide. Lignes à examiner en premier (row_id) : 51, 63, 68, 176, 183.
- *Chiffres vérifiés : oui*

## COMP_03 : education manquante (majeure)

- **Cause probable** : Niveau d'études non renseigné, ou colonne mal alimentée lors de l'import. Sur 600 lignes en erreur, 0 sont déjà dans les données brutes et 600 sont apparues ensuite.
- **Impact** : Les analyses par niveau d'études perdent une partie des clients. Taux observé : 1,45 %, seuil d'alerte : 1 %.
- **Correction suggérée** : Compléter depuis la source, ou utiliser la modalité unknown plutôt qu'une valeur vide. Lignes à examiner en premier (row_id) : 43, 188, 196, 227, 265.
- *Chiffres vérifiés : oui*

## VALID_02 : marital hors valeurs autorisées (majeure)

- **Cause probable** : Saisie libre, ou casse et espaces non normalisés. Sur 400 lignes en erreur, 0 sont déjà dans les données brutes et 400 sont apparues ensuite.
- **Impact** : Les regroupements par statut marital créent de fausses catégories. Taux observé : 0,97 %, seuil d'alerte : 0,5 %.
- **Correction suggérée** : Normaliser (minuscules, espaces retirés) et restreindre la saisie à la liste autorisée. Lignes à examiner en premier (row_id) : 314, 504, 576, 689, 770.
- *Chiffres vérifiés : oui*

## UNIQ_01 : lignes dupliquées (majeure)

- **Cause probable** : Double chargement des données, ou fusion de sources sans clé unique. Sur 212 lignes en erreur, 12 sont déjà dans les données brutes et 200 sont apparues ensuite.
- **Impact** : Les clients dupliqués sont comptés plusieurs fois et gonflent les volumes. Taux observé : 0,51 %, seuil d'alerte : 0,1 %.
- **Correction suggérée** : Dédoublonner à l'import et mettre en place une clé unique. Lignes à examiner en premier (row_id) : 1267, 12262, 14235, 16957, 18466.
- *Chiffres vérifiés : oui*

## VALID_03 : month invalide (majeure)

- **Cause probable** : Abréviations non conformes, ou valeurs non reconnues pour le mois. Sur 200 lignes en erreur, 0 sont déjà dans les données brutes et 200 sont apparues ensuite.
- **Impact** : Les analyses saisonnières et le tri chronologique deviennent incorrects. Taux observé : 0,48 %, seuil d'alerte : 0,1 %.
- **Correction suggérée** : Valider le mois contre la liste des abréviations autorisées. Lignes à examiner en premier (row_id) : 110, 497, 882, 1006, 1093.
- *Chiffres vérifiés : oui*

## COMP_04 : default = unknown (mineure)

- **Cause probable** : Information collectée de façon incomplète auprès des clients, déjà présente dans la source. Sur 8637 lignes en erreur, 8597 sont déjà dans les données brutes et 40 sont apparues ensuite.
- **Impact** : La variable est peu exploitable telle quelle : une part importante des clients n'a pas de valeur connue. Taux observé : 20,87 %, seuil d'alerte : 10 %.
- **Correction suggérée** : Documenter la limite, traiter unknown comme une catégorie à part, ou envisager d'écarter la variable. Lignes à examiner en premier (row_id) : 2, 6, 8, 11, 16.
- *Chiffres vérifiés : oui*
