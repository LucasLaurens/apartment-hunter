# Quels constats de l'audit retenir pour hunt review ?

Type: grilling
Status: resolved
Blocked by: 03

## Question

Parmi les constats de l'audit sur `hunt review` (variante C, liste + panneau, Rich), lesquels corriger, et comment, sans rouvrir la disposition retenue par [UX de hunt review](../../idee-produit/issues/04-ux-hunt-review.md) ? Et quelle part de la carte web décidée doit s'aligner dans le panneau, pour que les deux surfaces parlent la même langue ?

## Answer

Grilling du 2026-10-29. Les douze constats sont retenus, sans rouvrir la disposition liste + panneau. Reste à implémenter.

- **R1, les nouveautés** : un « ● » en tête de ligne, en `green` du terminal, et la ligne en gras. Le tri reste celui que le chasseur a choisi.
- **R2, R4, R11, les montants** : une seule mise en forme, dans le domaine, via `Price.format_total`.
  - Elle produit « 1 210 € CC », avec une espace fine pour les milliers.
  - « charges ? » s'ajoute quand le loyer est seul.
  - La colonne de prix est alignée à droite, et « €/m² » s'écrit avec une virgule.
  - Elle sert à la revue, au tableau de `hunt search` et aux alertes (`build_summary_line`).
- **R3, le panneau de détail** : il suit l'ordre de la carte web (ticket 06).
  1. Total et commune.
  2. Taille · étage · DPE · GES.
  3. Loyer + charges · annonceur.
  4. Mentions : meublé, chauffage collectif, interdiction F/G en orangé, source injoignable.
  5. Titre.
  6. Source · date · photos · aussi sur…
  7. Lien.
  
  La position au marché viendra après le total quand l'ADR-0010 sera implémentée.
- **R5, la ligne sélectionnée** : style `reverse` à la place de `grey23` codé en dur, et le « ▶ » est gardé.
- **R6, annuler un écart** : le message nomme le logement, sous la forme « Écarté : 941 € CC · Poisy · T3 (trop cher) · u pour annuler ». La touche `u` annule le dernier écart via `RestoreHome`, le même chemin que le web.
- **Restaurer depuis le terminal** : `hunt review --dismissed` reprend le même écran sur les écarts en vigueur, et `r` restaure.
- **R7** : `o` dit « Ouvert dans le navigateur : … ».
- **R8** : les flèches ↑/↓ font comme `j`/`k`.
- **R9** : hors terminal interactif, un message en français dit quoi faire.
- **R10** : les raisons s'affichent dans le panneau, en deux colonnes.
- **R12** : un logement présent sur plusieurs sources est marqué « ×3 » dans la liste.

Posé pendant le grilling : une carte des filtres et des logements. Elle relève d'un autre ticket.

## Implémentation (2026-10-29)

Sur `feat/review-constats`. Les douze constats sont corrigés, vérifiés dans un vrai terminal (pseudo-terminal, base d'essai) et par 13 tests.

- **Format des montants** : `format_euros` dans `price.py`. `format_total` et `format_display` en dépendent, donc aussi le tableau de `hunt search`, les alertes et le titre des doublons du web.
- **Liste de la revue** : le montant et son unité (« CC » ou « charges ? ») sont dans deux colonnes, pour que les chiffres restent alignés même quand le loyer est seul.
- **Écart avec la décision** : le web forme toujours ses montants lui-même (`Intl.NumberFormat`), avec le même résultat. Aucun test ne vérifie que les deux formats restent identiques.
