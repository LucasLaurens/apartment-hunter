# Budget de couleur : position au marché et écart

Type: grilling
Status: resolved
Blocked by: 03

## Question

`PRODUCT.md` (principe 2) et `DESIGN.md` réservent la couleur d'accent au statut *Nouveau*. La position au marché (sous-coté, hors fourchette, repère faible) et l'écart deviennent visibles sur le web : méritent-ils une teinte, ou restent-ils en texte neutre ?

Préférence de départ : texte neutre. À confronter à l'audit (le *Nouveau* se repère-t-il encore ?) et au thème sombre à venir (une teinte de plus = une teinte à décliner deux fois). Si la règle change, `PRODUCT.md` et `DESIGN.md` changent avec elle.

## Answer

Texte neutre, confirmé. Le budget de couleur est resserré au lieu d'être élargi. Grilling du 2026-10-29, en deux rounds.

- **Position au marché** : texte neutre partout. « sous la réf. » en graisse 600, sans teinte. Mention de la source (ADR-0010) en texte muted.
- **Logement écarté (vue de restauration)** : neutre, raison écrite en clair (« écarté · trop cher · 28/10 »), pas de rouge.
- **Sources** : plus aucune teinte par source. Le nom est en texte gris. Les pastilles sont neutres et leur état se lit à la forme (pleine ou contour, coche), ce qui règle W7 et W9. `--src-h` disparaît. `DESIGN.md` § Source badges est réécrit.
- **Nouveau** : badge plein et bordure d'accent gardés. Le fond vert teinté et la pulsation sont retirés (W6). Le mouvement est réservé aux cartes arrivées pendant la session.
- **Orangé** : il n'est plus que pour « charges ? » et l'interdiction de louer F/G. « Chauffage collectif » devient une étiquette neutre. L'échelle DPE/GES est inchangée.
- **Primaire, secondaire, tertiaire** : c'est une hiérarchie d'actions, sur une seule teinte. Primaire = bouton plein accent, secondaire = contour, tertiaire = texte. Les tokens `--primary`, `--secondary` et `--tertiary` nomment des rôles, pas trois couleurs : le principe 2 tient.
- **Thèmes** : le budget vaut pour tous les thèmes. Le ticket 07 réécrit le principe 3, ajoute les tokens sombres et fait sauter `check_single_light_theme`.
- **Encodé** : `scripts/verify_ui.py` échoue sur une teinte hors tokens autorisés (accent, danger, orangé, DPE/GES), sur un `--src-h` restant et sur une animation de `.badge-new`, dans le même commit que l'implémentation.
- **Reporté** : W18 (police à 10 px) et W19 (pastilles de 22 px) passent au ticket 06.

Hors couleur, posé pendant le grilling : les annonces expirées encore affichées. Ce sujet a son propre ticket, [13](13-annonces-expirees.md).

À faire à l'implémentation : amender `PRODUCT.md` (principe 2, avec la hiérarchie primaire/secondaire/tertiaire) et `DESIGN.md` (§ Color, § Source badges, tag orangé) dans le même commit.

## Implémentation (2026-10-29)

Sur `feat/budget-couleur`. La carte avait déjà reçu sa part avec le ticket 06 : source en gris, Nouveau sans fond teinté ni pulsation, chauffage collectif neutre.

- **Pastilles de source neutres** : leur état se lit à la forme (pleine avec bordure marquée, ou contour seul), et la source choisie porte une coche. Elles passent à 11 px et 28 px de haut. Règle W7, W9, W18 et W19. `--src-h` et `sourceClass()` sont supprimés.
- **Hiérarchie d'actions** : un seul bouton plein par vue. « Nouveau filtre » passe en contour (W17).
- **Budget encodé** : `tests/presentation/test_colour_budget.py` échoue sur une teinte hors accent, danger, orangé et DPE/GES, sur un `--src-h` qui revient, et sur une carte animée. Les trois cas ont été provoqués exprès : la suite est passée au rouge.
- **Écarts avec la décision** :
  - Pas de tokens `--primary`, `--secondary`, `--tertiary` : ils n'auraient fait que répéter `--accent`. Les rôles sont nommés par les classes (`.btn-primary`, `.btn`, `.nav-link` / `.btn-icon`) dans `DESIGN.md`.
  - La vérification vit dans un test pytest plutôt que dans `verify_ui.py`. Elle tourne ainsi à chaque `make full` sans serveur.
  - Aucune animation pour les cartes arrivées en cours de session : la carte ne bouge plus du tout.
- **Position au marché et vue des écartés** : la règle (texte neutre) est écrite dans `DESIGN.md`. Elle s'appliquera quand ces vues existeront.
