# Référence des filtres

Tous les critères disponibles lors de `hunt filter add`.

---

## Localisation

### `cities` — Villes cibles
Liste de villes autour desquelles chercher, **10 au plus** (`MAX_CITIES` : chaque ville coûte un
appel au géocodeur, limité à un par seconde). La recherche est géographique (rayon), pas par nom
exact.

```
Exemples : Annecy, Lyon, Grenoble, Chambéry
```

### `radius_km` — Rayon de recherche
Distance maximale en km autour de chaque ville cible.

```
Défaut : 20 km
Recommandé : 10–30 km selon la densité urbaine
Accepté : 1 à 150 km (au-delà, le filtre est refusé — le crawl s'étendrait à des
          milliers de communes)
```

> **Comment ça marche** : toutes les communes dans le rayon sont géocodées (geo.api.gouv.fr, par département). Une annonce est gardée si ses coordonnées — les siennes, ou à défaut celles de sa commune — sont à ≤ `radius_km` d'une ville cible. Le crawl interroge en plus les communes les plus proches (et pas seulement la ville de base).

### `excluded_cities` — Villes exclues
Villes à exclure explicitement, même si elles sont dans le rayon. Utile pour éliminer des villes proches non désirées.

```
Exemple avec Annecy ±30km : exclure Rumilly, Aix-les-Bains
```

Le matching sur les villes exclues est insensible à la casse et fonctionne par nom exact.

---

## Prix

### `min_price` / `max_price` — Fourchette de loyer (€/mois)
Comparé au **loyer total** : loyer de base + charges si connues.

```
Exemple : min=600, max=1200
```

> Si une annonce ne précise pas les charges, le loyer de base seul est comparé.

---

## Surface et pièces

### `min_surface_m2` / `max_surface_m2` — Surface habitable (m²)
```
Exemple : min=40, max=80
```

### `min_rooms` / `max_rooms` — Nombre de pièces
```
1 = studio/T1
2 = T2
3 = T3
etc.
```

> Si l'annonce ne précise pas la surface ou les pièces, le critère est ignoré (annonce incluse).

---

## Type de bien

### `furnished` — Meublé / Non meublé
| Valeur | Effet |
|--------|-------|
| `true` | Uniquement meublés |
| `false` | Uniquement non meublés |
| `null` | Indifférent (défaut) |

> Le meublé vient de deux lectures : le **tableau de critères de la page détail** (« Meublé : non »)
> quand la source en a un, sinon le **texte de l'annonce** (« meublé » vs « non meublé / vide »,
> négation prioritaire). La page détail corrige la carte en cas de désaccord. Un filtre
> **non meublé** exclut donc les annonces annoncées meublées. Si aucune des deux ne dit rien, le
> critère est ignoré (annonce incluse) : Foncia ne visite aucune page détail, ses annonces n'ont donc
> que le texte de la carte.

---

## Étage

### `exclude_ground_floor` — Exclure le rez-de-chaussée
Élimine les annonces avec `floor_level = 0`.

> Utile pour raisons de sécurité ou de bruit.

### `exclude_first_floor` — Exclure le premier étage
Élimine les annonces avec `floor_level = 1`.

### `top_floor_only` — Dernier étage uniquement
N'accepte que les annonces marquées `is_top = true`.

> Ces trois critères sont cumulables. Une annonce sans info d'étage passe toujours (info manquante = on ne filtre pas).

---

## Performance énergétique (DPE)

### `accepted_dpe_ratings` — Notes DPE acceptées
Ensemble (set) des notes acceptées — chaque note est cochée individuellement, pas de seuil unique.
Ordre indicatif : **A (meilleur) → G (pire)**.

| Valeur | Ce qu'on accepte |
|--------|-----------------|
| `{A}` | Uniquement A |
| `{A, B}` | A et B |
| `{A, B, C, D}` | A, B, C et D ← recommandé |
| `{A, C, E}` | A, C, E — sélection arbitraire, trous autorisés |
| `set()` (vide) | Pas de filtre DPE |

```
Conseil : cocher A→D. E, F, G = factures élevées.
```

> Set vide = aucun filtre DPE. Cocher une note l'ajoute aux notes acceptées (matching `IN`, pas un seuil `≤`).

> Annonce sans DPE renseigné → toujours incluse (on ne peut pas filtrer ce qu'on ne connaît pas).

---

## Charges et chauffage

### `charges_included` — Charges comprises
| Valeur | Effet |
|--------|-------|
| `true` | Annonces CC uniquement |
| `false` | Annonces HC uniquement |
| `null` | Indifférent (défaut) |

### `collective_heating` — Chauffage collectif
| Valeur | Effet |
|--------|-------|
| `true` | Chauffage collectif uniquement |
| `false` | Chauffage individuel uniquement |
| `null` | Indifférent (défaut) |

---

## Qualité d'annonce

### `min_photos` — Nombre minimum de photos
Écarte les annonces dont on **sait** qu'elles ont trop peu de photos.

```
Défaut : 0 (pas de filtre)
```

> ⚠️ **Sans effet aujourd'hui.** Aucun crawler ne remplit `images`, donc aucune annonce
> n'a de nombre de photos *connu*. Un ensemble d'images vide se lit « non collecté », pas
> « zéro photo » — comme un DPE absent, il ne rejette pas. Compter le vide comme zéro
> faisait rejeter **toutes** les annonces dès que le seuil dépassait 0. Le critère
> reprendra son sens le jour où une source alimentera le champ.

### `excluded_advertisers` — Annonceurs à exclure
Liste de noms d'agences à ignorer. Matching par **sous-chaîne**, insensible à la casse :
saisir `Century 21` écarte aussi « Century 21 Lac Bleu ». Une annonce dont la source ne
publie pas d'agence est conservée (on ne peut pas prouver la correspondance).

---

## Affichage

### `max_results` — Nombre de résultats max
Plafond du nombre d'annonces correspondantes à remonter.

```
Défaut : 25
```

| Valeur | Comportement |
|--------|-------------|
| ≤ 25 | Une seule page, pas de pagination |
| > 25 | Résultats paginés **25 par page** dans l'interface web (contrôles ‹ Préc / pages / Suiv ›) ; l'API ne sert qu'une page par requête |

Le compteur affiché sur la vignette du filtre applique le même plafond que la liste : un badge
annonçant plus que la liste qu'il ouvre se lit comme un filtre cassé.

En CLI, `hunt search` affiche jusqu'à `max_results` (surchargé par `--limit`).

---

## Scheduler

### `notification_interval_minutes` — Intervalle de polling
Fréquence de vérification en mode `hunt watch`.

```
Défaut : 15 minutes
Minimum accepté : 5 minutes (le filtre est refusé en dessous)
Minimum conseillé : 10 minutes (au-dessous → risque de blocage anti-bot)
```

Même règle pour `refresh_interval_minutes` et pour les overrides
`hunt watch --interval / --refresh`. Un intervalle nul ou négatif placerait la prochaine
échéance dans le passé : la boucle re-crawlerait les 9 sources à chaque seconde.

### `enabled` — Activer/désactiver
Un filtre désactivé n'est pas utilisé en mode `watch`.

---

## Exemple de configuration YAML

```yaml
# config/filters.example.yml
filters:
  - name: "Annecy région - 3p meublé"
    cities: ["Annecy"]
    radius_km: 30
    excluded_cities: ["Rumilly", "Aix-les-Bains"]
    min_price: 700
    max_price: 1300
    min_surface_m2: 50
    min_rooms: 2
    max_rooms: 4
    furnished: true
    exclude_ground_floor: true
    exclude_first_floor: false
    top_floor_only: false
    accepted_dpe_ratings: ["A", "B", "C", "D"]
    charges_included: null
    collective_heating: null
    min_photos: 1
    max_results: 50          # > 25 → paginé 25/page
    notification_interval_minutes: 15
    enabled: true
```

> Le YAML est disponible comme référence. La configuration se fait actuellement via `hunt filter add` (CLI interactif) ou directement en base SQLite.

---

## Recherche ad-hoc en CLI

`hunt search --city ...` construit un filtre jetable depuis des flags (rien n'est
sauvegardé, pas de purge) — pratique pour tester des critères depuis le terminal.
Les flags mappent le formulaire web « Modifier le filtre » 1:1.

```bash
hunt search \
  --city Annecy --radius 20 \
  --exclude "Rumilly,Aix-les-Bains,Annemasse" \
  --max-price 1200 --min-surface 45 \
  --unfurnished --no-ground-floor --no-first-floor \
  --dpe A,B,C,D -n 25
```

| Formulaire | Flag CLI |
|------------|----------|
| Villes | `--city` / `-c` (séparées par virgules) |
| Rayon (km) | `--radius` |
| Villes exclues | `--exclude` (séparées par virgules) |
| Prix min / max | `--min-price` / `--max-price` |
| Surface min | `--min-surface` |
| Pièces min / max | `--min-rooms` / `--max-rooms` |
| Meublé | `--furnished` / `--unfurnished` (défaut : peu importe) |
| Exclure rez-de-chaussée | `--no-ground-floor` |
| Exclure 1er étage | `--no-first-floor` |
| Dernier étage uniquement | `--top-floor` |
| DPE acceptés | `--dpe A,B,C,D` (vide = aucun filtre DPE) |
| Nombre de résultats max | `--limit` / `-n` |

Sans `--city`, `hunt search` utilise un filtre sauvegardé (le premier, ou `--filter NOM`).
