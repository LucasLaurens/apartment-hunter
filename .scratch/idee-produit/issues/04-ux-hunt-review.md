# UX de `hunt review`

Type: prototype
Status: resolved
Blocked by: 02, 03

## Question

À quoi ressemble et comment se pilote `hunt review` ?

- Touches : `j`/`k` navigation, `x` écarter + raison, `o` ouvrir dans le navigateur, `u` restaurer (en `--dismissed`).
- Contenu d'une ligne : quels champs (prix total, €/m², position au marché, DPE, étage, charges, source) ?
- Ordre d'affichage par défaut (position au marché ? €/m² ? parution ?) ; où vont les annonces « pas de repère » ?
- Rich suffit-il, ou faut-il Textual ?

### Apporté par le ticket 02

- Mentions à placer sur une ligne : « ouverte le … », « restauré le … », « écarté le … à N € (raison) » (logement revenu après un changement de loyer).
- `o` marque le logement *ouvert* (tous ses doublons), pas seulement l'annonce.

### Apporté par le ticket 03

- `x` ouvre le choix de raison : `1`-`8` ou `0` + texte libre (Entrée pour vide). Raison obligatoire.
- Question de suggestion `[o/N]` affichée juste après le 3e écart même raison, avec l'impact.

### Apporté par le ticket 05

- Position au marché sur la ligne : « −12 % vs réf. », « hors fourchette », « (repère faible) », « pas de repère (raison) ». Contexte de la référence en vue détaillée. Mention de source en pied.

## Answer

**Variante C, « Liste + panneau »** : liste courte à gauche (position, total, commune, marque de mention), panneau de détail à droite (position, référence avec fourchette et millésime, total, €/m², taille, étage, DPE, annonceur, source, parution, mentions, lien). Prototype sur la branche jetable `prototype/hunt-review` (commit `203b0a3`, `src/apartment_hunter/presentation/cli/prototype_hunt_review.py`, lancer avec `uv run python -m apartment_hunter.presentation.cli.prototype_hunt_review`).

- **Tri par défaut** : position au marché croissante ; « pas de repère » en fin de liste. `s` fait tourner position → €/m² → parution.
- **Champs** : ceux du prototype, validés tels quels.
- **Touches** : `j`/`k`, `o` ouvrir (marque le logement *ouvert*), `x` + `1`-`8`/`0` écarter, `d` bascule vers les écartés, `u` restaurer, `s` tri, `q` quitter. Question de suggestion `[o/N]` juste après le 3e écart même raison. Mention de source en pied.
- **Rich suffit** : rendu Rich + lecture de touches en mode brut (stdlib `termios`/`tty`), pas de Textual.

Constats sur les vraies données (2026-09-25), hors du périmètre de cette map, confiés à une tâche séparée :

- un tiers des logements est « pas de repère », surtout faute de surface ;
- l'étage est inconnu partout : la raison « étage » ne déclenchera presque jamais de suggestion ;
- « Colocation à louer » passe `is_out_of_scope_tenancy` ; des annonces logic-immo (source retirée) datent de juin et ne sont jamais purgées ; une annonce Orpi est stockée à 0 €. Ces trois fuites prennent la tête du tri par position.
