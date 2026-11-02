# ADR-0001 — L'annonce est l'unité stockée, les doublons sont regroupés à l'affichage

**Statut** : acceptée, en vigueur — 2026-08-04

## Contexte

L'entité `Listing` est identifiée par `SHA-256(url)`. Un même logement confié à
trois agences en mandat non exclusif, ou republié par une agence sur un portail,
produit donc autant de lignes que d'URLs. La déduplication ne rattrape que la même
annonce revue au crawl suivant.

`docs/functional/overview.md` affirmait le contraire (« seule la première insérée est
conservée » pour une annonce présente sur deux sites). C'était faux : deux URLs, deux
hashs, deux lignes.

Fusionner en base est tentant, mais chaque annonce du même logement porte un prix, un
annonceur, des honoraires et des photos différents. Fusionner, c'est choisir laquelle
de ces vérités survit.

## Décision

Garder **une ligne par annonce** en base : le crawl, la purge et l'alerte continuent
de raisonner en annonces.

Introduire le regroupement « même logement » **uniquement à l'affichage** : une carte
par logement présumé, marqueur « aussi sur N sources », loyer le plus bas mis en avant,
détail des annonces dépliable.

Ne jamais masquer une annonce au motif qu'elle serait un doublon : un faux positif de
regroupement doit rester réversible d'un coup d'œil.

## Conséquences

- Aucune migration, aucun changement de crawler : le stockage ne bouge pas.
- Le regroupement est une heuristique (commune, pièces, surface arrondie, loyer). Elle
  vit dans `domain/services/duplicates.py`, elle est testable en pur, et un test lui
  interdit de perdre une annonce en route.
- Un logement n'est publié qu'une fois par source : deux annonces identiques du même
  site restent séparées, parce qu'une résidence publie ses lots identiques côte à côte.
- Le regroupement se fait **avant** la pagination et avant le plafond `max_results`,
  sinon un badge annoncerait un nombre que la liste ne montre pas.
- Les compteurs de l'interface comptent désormais des **logements**, et le disent :
  « 4 logements », jamais « 4 annonces ».
- La notion **Logement** entre au glossaire sans entrer dans le schéma de base.
- `docs/functional/overview.md` est corrigé : il n'y a pas de déduplication cross-source.
