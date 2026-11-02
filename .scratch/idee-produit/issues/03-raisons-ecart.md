# Liste des raisons d'écart

Type: grilling
Status: resolved
Blocked by: 02

## Question

Quelles sont les valeurs exactes de la liste fermée, et quand une raison déclenche-t-elle la suggestion d'un critère de filtre ?

- Valeurs de départ proposées : trop cher, rez-de-chaussée, sombre/vue, DPE, quartier, autre (texte libre).
- Correspondance raison → critère du `SearchFilter` (`exclude_ground_floor`, `max_price`, `accepted_dpe_ratings`, `furnished`…).
- Seuil de suggestion (N écarts pour la même raison ?) et surface où elle apparaît.
- Règle de promotion d'un « autre » récurrent en nouvelle valeur.

## Answer

Termes *Raison d'écart* et *Suggestion de critère* ajoutés à `docs/functional/glossaire.md`. Pas d'ADR : rien de difficile à défaire.

**Liste fermée** (une touche, raison obligatoire) :

| Touche | Raison | Critère | Valeur suggérée |
|---|---|---|---|
| 1 | Trop cher | `max_price` (total CC) | dizaine sous le plus petit total CC écarté |
| 2 | Trop petit | `min_surface_m2` | m² entier au-dessus de la plus grande surface écartée |
| 3 | Étage | `exclude_ground_floor` / `exclude_first_floor` | selon l'étage des écarts ; étage inconnu ne compte pas |
| 4 | DPE | `accepted_dpe_ratings` | retirer la lettre écartée et les plus mauvaises ; liste vide → lettres meilleures |
| 5 | Commune | `excluded_cities` | la commune |
| 6 | Annonceur | `excluded_advertisers` | l'annonceur |
| 7 | Meublé / non meublé | `furnished` | l'inverse des écarts |
| 8 | Aspect (photos, luminosité, état) | aucun | — |
| 0 | Autre + texte libre (peut être vide) | aucun | — |

**Suggestion** : après 3 écarts même raison (et même valeur quand elle en a une), question posée dans `hunt review` juste après le 3e, pour chaque filtre qui laisse encore passer ces logements, avec l'impact (« masquerait aussi N logements non écartés »). Jamais appliquée sans confirmation. Refusée → revient après 3 nouveaux écarts même raison (refus conservé : critère, valeur, date).

**Stockage** : l'écart garde une photo figée des champs de décision (total CC, surface, étage, DPE, annonceur, meublé), en plus des éléments de regroupement du ticket 02.

**« Autre »** : promu en valeur à la main, par une requête SQL ; rien à construire.
