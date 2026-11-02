# Hiérarchie de la carte web

Type: prototype
Status: resolved
Blocked by: 03, 04

## Question

Quelle hiérarchie d'information sur la carte web pour rejeter en moins d'une seconde ?

Les raisons d'écart disent ce que le chasseur juge : prix, surface, étage, DPE, commune, annonceur, meublé, aspect. La carte doit les rendre lisibles sans survol (principe 1 de `PRODUCT.md`), et accueillir la position au marché (« −12 % vs réf. », « pas de repère ») sans écraser le *Nouveau*. Qu'est-ce qui monte, qu'est-ce qui descend, qu'est-ce qui disparaît (source, photos, date, doublons) ? Densité : combien de cartes par écran à 1280 et 1440 ?

Prototype de deux ou trois variantes sur données réelles et états rares, lié depuis ce ticket.

## Answer

**Variante A, la ligne de décision**, choisie sur prototype le 2026-10-29. Les trois variantes (ligne de décision, tableau en lignes, cases fixes) restent sur la branche `prototype/carte-web` (`3f9ba40`).

- **Ce qui monte** : le total et la commune, sur la première ligne. Puis taille · étage · DPE · GES, puis la composition du total et l'annonceur. Ce sont les critères qu'examinent les raisons d'écart.
- **Ce qui descend** : le titre, réduit à un lien d'une ligne étendu sur toute la carte (W13). Puis, en pied de carte : source · date · photos · doublons, chaque doublon avec son propre lien.
- **Ce qui disparaît** :
  - la pastille colorée de source sur la carte (ticket 04) ;
  - les pastilles de statistiques ;
  - le fond vert et la pulsation du *Nouveau* (W6) ;
  - « CC » puis « HC » sur le même chiffre (W1).
- **Corrigés au passage** :
  - séparateur de milliers (W12) ;
  - « 5e étage » corrigé dans le domaine, donc aussi en CLI (W23), avec un test ;
  - libellés DPE/GES à 11 px (W18).
- **Densité** : 9 cartes visibles à 1280 px et 12 à 1440 px. Le prototype en affichait 12 et 15 : la version réelle garde le GES et une ligne de titre. Aucun débordement à 390 px, en clair comme en sombre. `make ui-check` passe.
- **Position au marché** : sa place est réservée après le total. Rien n'est affiché tant que l'ADR-0010 n'est pas implémentée.
- **Restent ouverts** : les pastilles de source au-dessus des cartes, encore colorées, relèvent de l'implémentation du ticket 04. Le geste « écarter » relève du ticket 05.
