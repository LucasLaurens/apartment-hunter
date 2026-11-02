# Tri, pagination et URL

Type: grilling
Status: resolved
Blocked by:

## Question

Comment la liste se trie, se pagine et se partage ? Constats de l'audit (ticket 03) :

- **W8** : les compteurs des pastilles de source portent sur la page courante, pas sur tout le filtre.
- **W21** : ni le filtre, ni la page, ni le tri, ni la source ne sont dans l'URL : un rechargement revient au premier filtre.
- **Tri par position au marché** : à décider une fois l'ADR-0010 implémentée.

Restent des constats bas, à prendre avec ce ticket : W20 (pas de `h1`, nom de l'application en anglais, `<title>` figé), W22 (tirets cadratins dans l'interface), W26 (en-tête des résultats à 390 px).

## Décisions

- **Q1 (W8)** : le serveur compte chaque source sur tout le filtre (`ListingPage.source_counts`) et choisit la source avant de couper la page (`execute_paginated(source=…)`). La liste, ses pages, son total et les pastilles portent sur la même chose. La barre latérale garde le total de tous les logements.
- **Q2 (W21)** : `?filtre=…&page=…&tri=…&source=…&vue=carte`, valeurs par défaut omises. Changer de filtre ajoute une entrée d'historique (`pushState`), le reste la réécrit (`replaceState`). `popstate` relit l'URL. Un filtre inconnu ouvre le premier ; une page au-delà de la dernière sert la dernière.
- **Q3** : tri par position au marché d'abord reporté, faute d'ADR-0010 ; livré avec elle sur `feat/position-marche` (« Position au marché : plus bas » et « Prix au m² : moins cher » dans le sélecteur).
- **Q4** : onglet « Annecy centre · 25 logements », `h1` visuellement masqué au nom du filtre, onglet des pages latérales à leur `h1` (W20) ; libellés de tri et infobulle en deux-points, DPE inconnu en `?`, tenu par `test_no_em_dash_reaches_the_page_text` (W22) ; à ≤ 560 px le compte prend sa ligne, « · page 2 sur 3 » ne se coupe plus (W26). « Apartment Hunter » reste le nom du produit.
