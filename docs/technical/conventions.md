# Conventions de code

Ce que le code de ce dépôt applique, et ce qu'on attend de toute contribution
(humaine ou assistée). La règle courte : **une connaissance = un seul endroit**.

---

## Clean Architecture

La règle de dépendance prime sur tout le reste : `presentation → infrastructure →
application → domain`, jamais l'inverse.

- Une règle métier (matching, déduction meublé, valeurs par défaut d'un filtre) vit
  dans `domain/`, même si un seul appelant s'en sert aujourd'hui.
- L'`infrastructure` implémente les ports du domaine ; elle n'en définit aucun.
- La `presentation` ne contient que de la traduction entrée/sortie : si une méthode y
  décide quelque chose de métier, elle est au mauvais étage.

Détail des couches : [Architecture](architecture.md).

---

## SOLID appliqué ici

| Principe | Comment il se voit dans le code |
|----------|--------------------------------|
| **S** — responsabilité unique | Un use case = un fichier ; `cli/main.py` déclare les commandes, `cli/session.py` gère le conteneur, `cli/filter_wizard.py` pose les questions |
| **O** — ouvert/fermé | Ajouter une source = une classe de plus dans `container.build_crawlers`, aucun `if source == …` ailleurs |
| **L** — substitution | Tout `CrawlerPort` est interchangeable : `CrawlAllSources` ne connaît que `fetch()` et `source_name` |
| **I** — ségrégation | Ports courts et séparés (`CrawlerPort`, `NotifierPort`, `CachePort`, `ListingRepositoryPort`) |
| **D** — inversion | Les use cases reçoivent des ports par constructeur ; le `Container` est le seul à connaître les classes concrètes |

---

## DRY — mutualiser la connaissance, pas les caractères

Deux copies d'une même règle finissent par diverger. Exemples déjà mutualisés :

| Connaissance | Endroit unique |
|--------------|----------------|
| Meublé / non meublé (texte de carte **et** étiquette de page détail) | `domain/services/furnishing.py` |
| Fusion carte ↔ page détail (DPE, GES, étage, meublé, date) | `infrastructure/crawlers/base_crawler.py` (`merge_details`) |
| Valeurs par défaut d'un filtre | `domain/entities/search_filter.py` |
| Slug ville, en-têtes navigateur, pagination, surface / pièces | `infrastructure/crawlers/base_crawler.py` |
| Formulaire web → `SearchFilter` (création **et** édition) | `presentation/web/filter_payload.py` |
| Oui / non / indifférent | `presentation/tri_state.py` |
| Ordre d'affichage + normalisation de la date de parution | `domain/services/listing_order.py` |
| Nettoyage du texte scrapé + schémas d'URL acceptés | `domain/services/sanitising.py` |
| Bornes d'un filtre (intervalles, rayon, cap de résultats) | `domain/entities/search_filter.py` |

À l'inverse, deux règles identiques par hasard mais qui évolueront séparément restent
séparées : la ressemblance n'est pas une duplication.

Quand une règle **doit** exister en double parce que deux moteurs l'exécutent (l'ordre
d'affichage vit en Python *et* en SQL, puisque le `LIMIT` du pré-filtre coupe sur la clé
demandée), la copie s'accompagne d'un test qui échoue à la divergence :
`tests/infrastructure/test_sqlite_sort_parity.py`.

---

## Clean Code

- **Pas de valeur magique** : un seuil porte un nom (`_PRICE_SLACK_RATIO`,
  `_MAX_CANDIDATES`, `CITY_CONCURRENCY`) ou devient un enum (`PublicationSource`,
  `SearchState`).
- **Pas de paramètre mort** : si une fonction reçoit un argument qu'elle n'utilise
  pas, l'argument disparaît (pas le calcul chez l'appelant).
- **Commentaires du « pourquoi »** : le code dit ce qu'il fait ; le commentaire
  explique la contrainte du site, la subtilité anti-bot, ou l'invariant. Un
  commentaire qui paraphrase la ligne suivante est supprimé.
- **Immutabilité par défaut** : `Listing` et les value objects sont des
  `frozen dataclass` ; `SearchFilter` est mutable parce que l'utilisateur le
  configure.
- **Éviter le nullable** : préférer une valeur toujours présente (liste vide, valeur
  par défaut) à un `None` que chaque appelant doit tester.
- **Loi de Déméter** : demander à l'objet plutôt que traverser ses entrailles
  (`listing.format_published_label()`, `listing.has_site_publication_date`, `filter.max_results`).

---

## Nommage — une fonction est une action

Une fonction *fait* quelque chose : son nom commence par un **verbe**. Un nom sans
verbe décrit une *chose*, et une chose est un attribut, pas un comportement. Un nom
nominal ment sur le coût : `repository.top_listings(...)` se lit comme un champ et
cache une requête SQL ; `repository.find_top(...)` annonce le travail.

```python
# ❌ Se lit comme un attribut
availability.programs_inherited(category_id)
filter_codec._radius(data)
floor.label()

# ✅ Le site d'appel dit ce qui se passe
availability.find_programs_inherited(category_id)
filter_codec._read_radius(data)
floor.format_label()
```

### Choisir le verbe d'après ce qui se passe vraiment

| La fonction… | Verbe |
|--------------|-------|
| interroge un store et renvoie des lignes | `find…`, `list…`, `search…` |
| dérive une valeur de ce qu'elle a déjà | `compute…`, `build…`, `format…` |
| lit une valeur en résolvant une indirection | `read…`, `resolve…` |
| transforme A en B | `to_…` / `from_…`, `convert…`, `map…` |
| change un état sans rien renvoyer | `save…`, `update…`, `delete…`, `apply…`, `sync…` |
| déplace des données stockées vers la forme d'un schéma plus récent | `migrate…` |
| crée et renvoie un objet | `create…`, `build…`, `make…` |
| parse du texte scrapé | `parse…`, `detect…` |
| répond oui / non | `is…`, `has…`, `can…`, `should…` |

Prendre le verbe **vrai**, pas le plus vague qui passe. `get…` est le défaut
paresseux : réservé à un accesseur sur un champ déjà chargé (`get_settings`), jamais
devant une requête — d'où `list_all`, `find_top`, `find_new_since` sur
`ListingRepositoryPort`. `handle…` / `process…` / `manage…` ne nomment rien : si c'est
le seul verbe qui convient, la fonction en fait trop (SRP).

### Ce que la règle ne couvre pas

- **Les prédicats** — `is_`/`has_`/`can_`/`should_` sont déjà des verbes.
- **Les propriétés et valeurs calculées** — un `@property` (`charges_unknown`,
  `is_thermal_sieve` côté service, `Floor.is_known`) *est* une chose ; il reste nominal.
- **Les constructeurs nommés** — `Floor.unknown()`, `Floor.from_int()`,
  `DpeRating.from_string()`, `Price.from_float()` : `from_…` est l'idiome.
- **Les conversions** — `listing_to_dict`, `filter_from_json`, `with_site_date` :
  `to_…` / `from_…` / `with_…` se lisent comme des actions.
- **Les noms imposés par un framework** — `lifespan` (FastAPI), `on_response`
  (Playwright), les fixtures pytest (`repository`, `matcher` : ce sont des valeurs),
  les dunders.

### Renommer ce qu'on touche

Un fichier ouvert par le changement est un fichier dont on est responsable : les noms
nominaux qu'on y croise sont renommés dans le même commit, sites d'appel inclus. Deux
limites : un fichier seulement traversé ne devient pas le nôtre, et un renommage
préserve le comportement — tous les sites d'appel mis à jour, `make full` vert, et
`grep` sur l'ancien nom revient vide.

**Attention aux noms qui sortent du Python** : une clé JSON (`display_total`,
`rental_ban_warning`, `advertiser_kind` dans `listing_to_dict`) est un contrat avec
`app.js`, une colonne SQLite (`listing_id`) un contrat avec la base. Renommer la
fonction, jamais la clé — sauf migration assumée des deux côtés.

### Signal

Lire le site d'appel à voix haute. Si ça sonne comme un accès à un champ
(`codec._radius(data)`), le nom est nominal. Si ça sonne comme un ordre
(`codec._read_radius(data)`), c'est une fonction.

---

## Complexité algorithmique

Toute fonction non triviale doit être justifiable en Big O, et l'annotation est
attendue quand ce n'est pas évident :

```python
# O(n) en taille de page, O(k) en mémoire pour k annonces
```

Réflexes appliqués dans le code :

- appartenance / déduplication → `set` (`_paginate`, `_gather_cities`), jamais `x in list`
  dans une boucle ;
- normalisation répétée d'une même liste → mémoïsation (`_normalise` du matcher,
  `@lru_cache`) ;
- critères de matching évalués paresseusement, le calcul géodésique en dernier ;
- coût réseau borné explicitement (`MAX_PAGES`, `CITY_CONCURRENCY`, `ENERGY_CONCURRENCY`,
  `SOURCE_TIMEOUT_SECONDS`) ;
- tout compromis mémoire est dit à voix haute (cache DPE 24 h, cache géocodage 24 h).

---

## Tests

- Fakes concrets dans `tests/fakes/` — **aucun mock**, aucune requête réseau.
- Structure `# Arrange / # Act / # Assert` systématique.
- Données générées par Faker, sauf les valeurs qui pilotent l'assertion.
- Les conventions vérifiables par une machine le sont : `tests/test_function_naming.py`
  échoue sur toute fonction de `src/` dont le nom ne commence pas par un verbe,
  `tests/infrastructure/test_sqlite_sort_parity.py` sur une divergence Python ↔ SQL,
  `tests/infrastructure/test_advertiser_source_parity.py` sur un crawler non classé.

---

## Interface web — thème et accessibilité

Le système visuel complet (tokens, échelles, composants) vit dans
[DESIGN.md](../../DESIGN.md) à la racine ; la stratégie produit qui le justifie dans
[PRODUCT.md](../../PRODUCT.md). Les règles que le code doit respecter :

- **Clair, Sombre ou Système, une seule liste de couleurs** ([ADR-0011](../decisions/0011-le-theme-est-un-choix-du-chasseur.md)).
  Chaque couleur s'écrit `light-dark(clair, sombre)` ; `color-scheme` sur `:root`
  choisit la moitié. Aucune branche `prefers-color-scheme`, aucun second bloc de
  tokens : DRY appliqué au CSS. `test_theme_tokens.py` échoue sur une couleur sans sa
  valeur sombre. Le choix est appliqué par le script du `<head>`, avant le rendu.
- **Couleurs en OKLCH**, déclarées une fois dans `:root` de `styles.css`. Jamais
  de `#fff` ni de `#000` ; les neutres sont teintés vers la teinte d'accent (155).
  Aucune valeur de couleur en dur dans une règle : passer par un token.
- **La teinte va à l'état, jamais à la décoration** (ticket 04). Accent pour le
  *nouveau* et l'action primaire, danger pour l'action destructrice, orangé pour
  « charges ? » et l'interdiction F/G, échelle DPE/GES. Une source n'a pas de teinte.
  `test_colour_budget.py` échoue sur toute autre teinte.
- **Une teinte par note DPE, pas une règle par note.** Chaque note ne déclare que
  sa teinte (`--dpe-h`) ; la règle partagée la consomme.
- **Icônes en SVG** depuis le sprite `<symbol>` de `index.html`, via
  `icon(name)` dans `app.js`. Pas d'emoji : rendu différent par plateforme et sans
  nom accessible.
- **Base WCAG 2.1 AA** : texte à 4.5:1 minimum, `label for` sur chaque champ,
  erreur sous le champ concerné (`aria-invalid` + `aria-describedby`), tout
  atteignable au clavier avec un `:focus-visible` visible, `aria-label` sur les
  boutons sans texte, aucune information portée par la seule couleur (la lettre
  du DPE est toujours affichée), `prefers-reduced-motion` respecté.
- **Aucune affordance réservée au survol** : ce qui apparaît au `:hover` apparaît
  aussi au `:focus-within`.
- **Aucune magic string dans `app.js`.** Un endpoint, un id de champ, un statut de
  crawl, un nom d'icône ou une classe pilotée par le JS a une seule orthographe,
  déclarée en tête de fichier dans un objet gelé : `API`, `HTTP`, `EL`, `FIELD`,
  `ICON`, `CSS`, `SEARCH_STATUS`, `FURNISHED`, `DEFAULT`. Les bornes sont nommées
  de la même façon (`SKELETON_CARDS`, `PAGE_WINDOW`, `LOAD_TIMEOUT_MS`,
  `SEARCH_POLL_MS`, `AGENCY_MAX_CHARS`…) : jamais de littéral dans un chemin de
  rendu ou de polling. Les valeurs par défaut du formulaire vivent dans `DEFAULT`,
  partagées par le pré-remplissage et le payload — pas deux copies de `20`.

Ces règles sont exécutables, pas seulement écrites :

```bash
make dev                    # dans un terminal
make ui-check PORT=8001     # dans un autre
```

`scripts/verify_ui.py` pilote l'interface réelle avec Playwright : contraste calculé
sur les couleurs rendues, absence de reste de thème sombre, absence d'emoji-icône,
premier arrêt de tabulation, focus et Échap de la modale, validation inline, nom
accessible de chaque bouton icône, débordement horizontal à 390 px. Il écrit aussi
les captures dans `.ui-screenshots/` : une suite verte ne prouve rien sur du visuel,
il faut l'avoir regardé.

Les captures du README sont d'une autre nature : elles se font sur des **données
fictives**, jamais sur une base réelle (une annonce scrapée n'a rien à faire dans un dépôt).
`scripts/seed_demo.py` remplit une base de démonstration (Faker, graine fixe, liens vers
example.org) ; `scripts/capture_readme_media.py` en tire `docs/media/` : captures web dans
les deux thèmes, visite animée (ffmpeg) et `hunt review` en SVG (Rich), dans l'ordre que
la revue ouvre vraiment. Les commandes sont dans le README, « Régénérer les captures ».

La vidéo de présentation suit la même règle. `scripts/capture_marketing_media.py` tire de
la base de démonstration des images deux fois plus denses (`marketing/video/shots/`),
`scripts/render_marketing_video.py square|vertical` les anime (`marketing/video/stage.html`,
une image par appel à `seek(t)`, donc indépendante de la vitesse de la machine) et encode
le MP4 avec ffmpeg. Les textes des réseaux sont dans `marketing/posts.md`.

---

## Documentation

La documentation fait partie du changement, pas d'un rattrapage ultérieur.

| Si tu touches… | Mets à jour |
|----------------|-------------|
| Une couche, un module, un déplacement de fichier | [architecture.md](architecture.md) (dont l'arborescence) |
| Un crawler, le socle commun, l'anti-bot | [crawlers.md](crawlers.md) |
| Une entité, un champ, une migration | [data-model.md](data-model.md) |
| Le mode watch, les intervalles, la concurrence | [scheduler.md](scheduler.md) |
| Une commande CLI, une source, une variable d'env | [README.md](../../README.md) |
| Une convention de code | ce document |

Un exemple de code cité dans la doc doit compiler tel quel avec la signature réelle :
une doc fausse coûte plus cher que pas de doc.

---

## Vérification avant commit

```bash
make full     # ruff check + ruff format --check + mypy strict + pytest
```

Le hook lance la même chose **au push**, pas au commit :

```bash
make install-hooks   # pre-commit, pre-push (gate make full) et commit-msg (identité)
```

Le hook `commit-msg` garde l'historique à une seule identité : auteur et committer
`LucasLaurens`, et un message sans trailer `Co-Authored-By` ni nom d'outil ou d'une seconde
identité. Il ne stashe rien, donc il tourne au commit sans le risque décrit plus bas.

Pourquoi au push : en pre-commit, `pre-commit` stashe le travail non-stagé avant de lancer
la suite ; interrompre le run (Ctrl+C, timeout) laisse le stash non restauré et l'arbre de
travail perd silencieusement ces modifications. Au pre-push il n'y a rien à stasher, et la
série entière est quand même vérifiée avant de quitter la machine.
