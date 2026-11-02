# Carte des loyers : le référentiel est-il utilisable ?

Type: research
Status: resolved
Blocked by:

## Question

La Carte des loyers (ministère du Logement, data.gouv.fr) peut-elle servir de référence de prix/m² pour les annonces ?

- Format du fichier, dernier millésime, fréquence de mise à jour, licence.
- Granularité : par commune ? par type d'appartement (T1-T2, T3+) ? charges comprises ou non ?
- Clé : code INSEE ? Comment passer d'une annonce (nom de commune, code postal) à ce code ? Le géocodage actuel (`infrastructure/geocoding.py`, Nominatim) le renvoie-t-il ?
- Couverture des communes du filtre « Autour d'Annecy » (Annecy, Veyrier-du-Lac, Villaz…).

## Answer

**Utilisable.** Détail complet : branche `research/carte-des-loyers`, fichier `.scratch/idee-produit/research/01-carte-des-loyers.md` (`git show research/carte-des-loyers:.scratch/idee-produit/research/01-carte-des-loyers.md`).

- Millésime 2025 (ANIL, publié le 2025-12-11, loyers du T3 2025), annuel en décembre. Licence Ouverte 2.0 : citer la source dans l'UI.
- 4 CSV : appartements, T1-T2, T3+, maisons. Loyer **charges comprises**, **non meublé** seulement.
- Colonnes : `INSEE_C`, `loypredm2` (€/m²), `lwr.IPm2` / `upr.IPm2` (intervalle de prédiction à 95 %), fiabilité `TYPPRED`, `nbobs_com`, `R2_adj`. `loypredm2` est une prédiction pour un logement type (T1-T2 = 37 m², T3+ = 72 m²), pas une médiane ; coefficients non publiés.
- Code INSEE : ajouter `code` aux `fields` de l'appel geo.api.gouv.fr existant (`_fetch_dept_communes`, `infrastructure/geocoder.py`), zéro requête en plus ; 279 codes du 74 = 279 lignes du fichier. Anciennes communes via `/communes_associees_deleguees` (`chefLieu`). Pas de Nominatim (renvoie des codes de commune déléguée absents du fichier). Un code postal seul est ambigu.
- Couverture : Annecy 74010 (commune), Villaz 74303 (commune), Veyrier-du-Lac 74299 et Montagny-les-Lanches 74186 (regroupement de communes voisines ; Montagny sous le seuil de 30 observations).
- Pièges de comparaison : meublés, `charges_unknown`, surface absente, mélange de millésimes. Intervalles larges (Annecy −27 % / +38 %). Parsing : cp1252, virgule décimale, `INSEE_C` en chaîne.
