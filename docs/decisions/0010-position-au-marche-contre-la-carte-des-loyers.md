# ADR-0010 — La position au marché se mesure contre la Carte des loyers, jamais contre nos annonces

**Statut** : en vigueur — acceptée le 2026-09-25, implémentée le 2026-10-31

## Contexte

Pour aider à décider, l'application doit dire si un loyer est bas **pour le marché**,
pas seulement le classer parmi les annonces affichées. La référence la plus proche sous
la main, la médiane du total CC au m² de nos propres annonces, est faussée trois fois :

- **circulaire** : la base ne contient que ce qui passe déjà le filtre, donc sous le
  budget. Sa médiane est celle de ce que le chasseur accepte, pas celle du marché ;
- **sans historique** : la purge supprime les annonces retirées et hors critères ;
- **trop petite** : quelques dizaines d'annonces, sur quelques communes.

La *Carte des loyers* (ANIL pour le ministère du Logement, data.gouv.fr, Licence Ouverte
2.0) publie chaque année, par commune, un loyer au m² charges comprises, non meublé, avec
un intervalle de prédiction à 95 %, pour T1-T2, T3+ et tous appartements.

## Décision

**La position au marché compare le total CC au m² d'une annonce au loyer de référence de
la Carte des loyers**, pour sa commune (code INSEE) et son nombre de pièces. Aucune
médiane calculée sur nos annonces, ni en repli.

## Conséquences

- Il faut le code INSEE de chaque commune : ajouté aux `fields` de l'appel geo.api.gouv.fr
  déjà fait par le géocodeur, pas via Nominatim (qui renvoie des codes de communes
  déléguées absents de la carte).
- Le fichier se télécharge (pas d'API par commune) et se garde en cache. Les URL du
  millésime sont des constantes, mises à jour à la main chaque décembre ; le millésime
  est affiché, et deux millésimes ne sont jamais comparés.
- La référence est une prédiction pour un logement type (37 m² ou 72 m²), pas une
  médiane, et ne se recale pas sur la surface réelle. L'interface dit « vs réf. », jamais
  « prix du marché ».
- Les annonces non comparables — meublées, aux charges inconnues, sans surface, d'une
  commune absente — n'ont **pas de position**, plutôt qu'une position fausse.
- « Sous le marché » n'est affirmé que hors de l'intervalle de prédiction ; en deçà, le
  pourcentage sert à classer.
- Mention obligatoire de la source dans chaque surface qui affiche une position.
- Une position mesure le marché de l'annonce, jamais les goûts du chasseur : ceux-là
  passent par le filtre et les *suggestions de critère*.
