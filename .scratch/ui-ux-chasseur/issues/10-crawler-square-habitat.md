# Ajouter le crawler Square Habitat

Type: task
Status: resolved
Blocked by:

## Question

Ajouter Square Habitat : liste SSR Angular (JSON `ng-state`), route `/annonces/location/bien/appartement/immobilier/auvergne-rhone-alpes/haute-savoie/annecy-74000` ; page détail pour DPE, GES, étage, meublé, charges. Corriger la ligne « Square Habitat = SPA » de `docs/functional/sources.md`. Détails : la recherche, § Square Habitat.

Recherche : [sources-accessibles.md](../research/sources-accessibles.md), branche `research/sources-annecy`. Livre du code (voir Notes de la map).

## Answer

Implémenté sur `feat/crawler-squarehabitat` (`ba48100`), partie de `main`, non poussée.

- **Collecte** : une page département (`…/haute-savoie-74`, trouvée dans le sitemap des locations) couvre le rayon, 18 annonces par page.
- **Contenu de la liste** : les annonces sont dans le JSON `ng-state`, avec leurs coordonnées, le prix charges comprises, la date et les photos.
- **Page détail** : DPE, GES, étage et meublé.
- **Premier passage réel (2026-10-30)** : 38 annonces dans le 74.
  - DPE, GES, meublé et coordonnées : 38 sur 38.
  - Étage : 37. Photos : 36.
- **Tests** : 4 tests, chacun provoqué exprès.
