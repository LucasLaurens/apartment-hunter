# Affichage de la position au marché

Type: grilling
Status: resolved
Blocked by: 01

## Question

Comment l'écart du prix/m² à la référence est-il calculé et montré ?

- Format (« −18 % », « 3 €/m² sous le marché »…).
- Base de comparaison : loyer charges comprises ou hors charges, selon ce que le référentiel fournit ; que faire de `Listing.charges_unknown` ?
- Commune absente du référentiel : pas de repère, ou repli (commune voisine, département) ?
- L'écart apparaît-il dans le digest email ?

### Faits apportés par la recherche 01

- Le référentiel est charges comprises : comparer le total loyer + charges ; une annonce `charges_unknown` paraîtra sous-cotée à tort.
- Non meublé seulement : que faire d'une annonce meublée (pas d'écart, ou écart marqué) ?
- Prédiction pour un logement type (37 m² ou 72 m²), coefficients non publiés : l'écart sur un 60 m² est approximatif. Choisir T1-T2 ou T3+ selon le nombre de pièces.
- Intervalle de prédiction large (Annecy −27 % / +38 %) : afficher l'écart seulement hors intervalle ? ou toujours, avec une marque ?
- Fiabilité (`TYPPRED` commune vs regroupement, `nbobs_com` < 30) : la signaler ?
- Mention de la source obligatoire (Licence Ouverte 2.0).

## Answer

Renommé : « écart » est réservé au geste du chasseur ; la différence de loyer s'appelle **position au marché**. Termes *Loyer de référence* et *Position au marché* ajoutés à `docs/functional/glossaire.md`, avec deux mots bannis.

| Sujet | Décision |
|---|---|
| Format | Pourcentage toujours affiché (« −12 % vs réf. »), marque « hors fourchette » seulement hors intervalle de prédiction |
| Non comparables | Meublé, charges inconnues, sans surface, commune absente : « pas de repère (raison) », jamais de chiffre ; aucun repli sur une zone plus large ; maison comparée aux appartements (limite connue) |
| Référence | 1-2 pièces → T1-T2, 3+ → T3+, inconnu → tous appartements ; pas de correction de surface ; contexte en vue détaillée (« réf. T1-T2 Annecy 20,9 €/m², logement type 37 m², 2025 ») |
| Fiabilité | Mention écrite « (repère faible) » si `nbobs_com` < 30 ou `R2_adj` < 0,5, et seulement là |
| Surfaces | `hunt review` et email d'alerte oui ; web non (gelé) ; mention de source en pied des deux |
| Référentiel | Téléchargé à la première utilisation, cache local ; URL du millésime en constantes, mises à jour à la main en décembre ; millésime affiché |
