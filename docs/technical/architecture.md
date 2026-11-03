# Architecture

## Principe : Clean Architecture

L'application est structurée en 4 couches concentriques. La règle fondamentale : **les couches internes ne dépendent jamais des couches externes**.

```
┌─────────────────────────────────────────────┐
│              Presentation                   │  CLI (Typer + Rich) + web (FastAPI)
│  ┌───────────────────────────────────────┐  │
│  │           Infrastructure              │  │  Crawlers, SQLite, notifs, cache
│  │  ┌─────────────────────────────────┐  │  │
│  │  │         Application             │  │  │  Use cases, orchestration
│  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │         Domain            │  │  │  │  Entités, valeurs, ports, règles
│  │  │  └───────────────────────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Les 4 couches

### Domain — le cœur métier

**Localisation :** `src/apartment_hunter/domain/`  
**Imports autorisés :** Python stdlib uniquement. Zéro dépendance externe (sauf `geopy` dans les services).

Contient :
- **Entities** — `Listing` (frozen dataclass), `SearchFilter` (mutable dataclass)
- **Value Objects** — `Price`, `Floor`, `Location`, `DpeRating` (réutilisé pour DPE et GES),
  `PublicationSource`, `ListingSort` (+ `DEFAULT_LISTING_SORT`), `RentReference` /
  `MarketPosition` / `NoMarketPosition` (position au marché, ADR-0010) + helpers
  `classify_energy`/`classify_ges`/`classify_dpe` — immutables
- **Ports** — interfaces ABCs définissant les contrats (`CrawlerPort`,
  `ListingRepositoryPort`, `NotifierPort`, `CachePort`, `GeocodingPort`, `ClockPort`,
  `RentReferencePort`)
- **Services** — `ListingMatcher` (matching pur, sans IO), `detect_furnished` /
  `detect_furnished_label` / `detect_furnished_chip` (déduction meublé/non-meublé — mot-clé
  pour le texte d'une carte, étiquette « Meublé : non » seule pour une page détail entière,
  puce de critère dont le texte *est* le mot (« Meublé ») pour les sites qui n'étiquettent
  rien ; partagées par les crawlers et le matcher), `listing_order` (`sort_listings`, `build_published_key` — l'ordre
  d'affichage et la normalisation de la date de parution en heure locale) et `sanitising`
  (`clean_text`, `is_web_url` — ce qu'une donnée scrapée doit subir avant d'être stockée)
- **Constantes de filtre** — `DEFAULT_RADIUS_KM`, `DEFAULT_MAX_RESULTS`,
  `DEFAULT_NOTIFICATION_INTERVAL_MINUTES`, `DEFAULT_REFRESH_INTERVAL_MINUTES` :
  une seule source de vérité pour les valeurs par défaut, quel que soit le point d'entrée

Le domaine ne sait pas qu'il y a un SQLite, un crawler, ou un notifieur. Il définit seulement **ce que le système fait**.

### Application — orchestration

**Localisation :** `src/apartment_hunter/application/`  
**Imports autorisés :** domain uniquement.

Contient les use cases — chaque use case = un fichier = une responsabilité :

| Use case | Rôle |
|----------|------|
| `CrawlAllSources` | Lance les crawlers en parallèle, sauvegarde en base |
| `GetTopListings` | Récupère + filtre les top N annonces (+ pagination) |
| `NotifyNewListings` | Notifie les nouvelles annonces non vues |
| `PurgeStaleListings` | Supprime les annonces hors filtre ou retirées des sources |
| `CleanListings` | `hunt clean` : supprime à la main les annonces hors filtre ou qu'aucun crawl n'a revues depuis N jours — celles que la purge ne peut plus atteindre |
| `ManageFilters` | CRUD des filtres de recherche |
| `OpenHome` | Ouvre un logement depuis l'une de ses annonces : ses doublons ne sont plus *Nouvelle* (revue et page web) |
| `RefreshFilter` | Un crawl d'un filtre, puis la purge qu'il autorise |
| `WatchFilters` | La politique de veille : quand recrawler, quand alerter, quoi faire en cas d'échec |

Les use cases reçoivent leurs dépendances par injection (constructeur). Ils ne connaissent que les **interfaces** (ports), jamais les implémentations concrètes.

### Infrastructure — implémentations concrètes

**Localisation :** `src/apartment_hunter/infrastructure/`  
**Imports autorisés :** domain, application, et toutes les librairies tierces.

Implémente les ports définis dans le domaine :

| Port | Implémentation |
|------|---------------|
| `CrawlerPort` | `PapCrawler`, `OrpiCrawler`, `FonciaCrawler`, `ParuVenduCrawler`, `Century21Crawler`, `LaforetCrawler`, `CityaCrawler`, `SquareHabitatCrawler`, `TwoAImmobilierCrawler` |
| `ListingRepositoryPort` | `SqliteRepository` |
| `NotifierPort` | `TerminalNotifier`, `CompositeNotifier` |
| `CachePort` | `TtlCache` |
| `GeocodingPort` | `NominatimGeocoding` |
| `ClockPort` | `AsyncioClock` |
| `RentReferencePort` | `CarteDesLoyers` |

Contient aussi :
- `config.py` — `Settings` via Pydantic-settings (`.env`)
- `container.py` — injection de dépendances manuelle (pas de framework DI)
- `geocoder.py` — appels Nominatim avec cache ; geo.api.gouv.fr donne aussi le code INSEE
  de chaque commune du département, et les communes déléguées rattachées à leur chef-lieu
  (`find_commune_codes`)
- `rent_map.py` — l'adaptateur du `RentReferencePort` : télécharge une fois par millésime
  les CSV de la Carte des loyers (URL en constantes, hôte data.gouv.fr vérifié, taille
  bornée), les garde sous `RENT_MAP_CACHE_DIR/{millésime}/`, les lit en cp1252. Un fichier
  illisible ne casse rien : pas de position, et pas de nouvel essai avant une heure
- `geocoding.py` — l'adaptateur du `GeocodingPort` : c'est lui qui fusionne les
  communes de plusieurs filtres, un calcul qui vivait auparavant à quatre endroits
- `clock.py` — l'adaptateur du `ClockPort` (temps monotone asyncio)
- `storage/filter_codec.py` — la forme JSON d'un filtre sauvegardé, hors de l'adaptateur SQLite
- `storage/dismissal_codec.py` — la forme d'une ligne de la table `dismissals`
- `storage/opening_codec.py` — la forme d'une ligne de la table `openings`
- `storage/home_key_codec.py` — la clé de logement sur quatre colonnes, partagée par les deux tables de jugements

### Presentation — interface utilisateur

**Localisation :** `src/apartment_hunter/presentation/`  
**Imports autorisés :** toutes les couches.

Deux interfaces partagent la même application : la CLI (Typer + Rich) et l'interface
web locale (FastAPI). Aucune règle métier ici — uniquement traduction entrée/sortie.

| Module | Rôle |
|--------|------|
| `cli/main.py` | Commandes Typer (`search`, `watch`, `review`, `serve`, `filter …`) |
| `cli/session.py` | `open_container()` — conteneur connecté puis fermé, et `setup_logging()` |
| `cli/adhoc.py` | `AdHocCriteria` — les flags de `hunt search --city …` → `SearchFilter` |
| `cli/filter_wizard.py` | Questionnaire interactif de `hunt filter add` |
| `cli/formatters.py` | Tableaux et panneaux Rich |
| `cli/review.py` | Écran de `hunt review` : liste + panneau, touches lues en mode brut |
| `web/app.py` | Routes FastAPI (filtres, annonces, écarts, recherche, watch) |
| `web/filter_payload.py` | Corps JSON du formulaire → `SearchFilter` (création **et** édition) |
| `web/dismissal_payload.py` | Corps JSON d'un écart → raison + texte libre (« autre » seulement) |
| `web/background_jobs.py` | Tâches de fond crawl/watch par filtre, et leur état |
| `web/serializers.py` | Entités → dictionnaires JSON |
| `web/request_guard.py` | Hôtes admis (rebinding DNS) et refus des écritures cross-site |
| `web/ui.py` + `web/assets/` | Page unique assemblée depuis `index.html`, `styles.css`, `app.js` |
| `tri_state.py` | Réponses oui / non / indifférent → `True` / `False` / `None` (CLI + web) |
| `dismissal_reasons.py` | Raisons d'écart avec leurs touches et libellés (CLI + web) |

---

## Injection de dépendances

Pas de framework DI — injection manuelle via `Container`.

```python
# infrastructure/container.py
class Container:
    def __init__(self, settings: Settings):
        self.repository = SqliteRepository(settings.database_url)
        self.crawlers = build_crawlers(settings)
        self.notifiers = build_notifiers()

    def make_crawl_use_case(self) -> CrawlAllSources:
        return CrawlAllSources(
            crawlers=self.crawlers,
            repository=self.repository,
            max_concurrent=self.settings.max_concurrent_crawlers,
        )

    def make_get_top_use_case(self) -> GetTopListings:
        return GetTopListings(repository=self.repository, geocoding=self.geocoding)
```

Aucune fabrique ne prend de table de communes géocodées : les use cases qui matchent
reçoivent le `GeocodingPort` et construisent leur `ListingMatcher` eux-mêmes. Le
contenu de cette table était auparavant décidé par chaque appelant — par filtre côté
web, fusionné tous-filtres côté CLI — et la même annonce pouvait donc matcher d'un côté
et pas de l'autre.

Le `Container` est construit dans la couche `presentation` (CLI), qui est le seul endroit où toutes les dépendances sont connues.

---

## Flux de dépendances

```
presentation
    └── instancie Container (infrastructure)
    └── appelle use cases (application)
              └── utilise ports (domain)
                        ↑
              implémentés par infrastructure
```

---

## Pourquoi cette architecture ?

**Testabilité :** Les use cases sont testés avec des fakes (`InMemoryCrawler`,
`InMemoryListingRepository`, `InMemoryGeocoding`, `ManualClock`) — aucun réseau, aucune
base réelle, et pour la veille aucune attente : l'horloge étant injectée, une
après-midi simulée s'exécute en quelques microsecondes.

**Évolutivité :** Ajouter une source = créer un nouveau `XxxCrawler` qui implémente `CrawlerPort` + l'ajouter dans `container.py`. Le reste de l'application ne change pas.

**Swappabilité :** Remplacer SQLite par PostgreSQL = écrire `PostgresRepository` qui implémente `ListingRepositoryPort`. Zéro impact sur domain/application.

---

## Structure des fichiers

```
src/apartment_hunter/
├── domain/
│   ├── entities/
│   │   ├── dismissal.py          ← Dismissal (écart d'un logement, photo figée)
│   │   ├── listing.py            ← Listing (frozen dataclass)
│   │   ├── opening.py            ← Opening (ouverture d'une annonce, clé de logement)
│   │   └── search_filter.py      ← SearchFilter + valeurs par défaut partagées
│   ├── value_objects/
│   │   ├── dismissal_reason.py   ← DismissalReason (raison d'écart, liste fermée)
│   │   ├── dpe_rating.py         ← DpeRating (enum ordonné A→G)
│   │   ├── energy_class.py       ← kWh / kg CO₂ → lettre A–G
│   │   ├── floor.py              ← Floor (level + is_top)
│   │   ├── home_key.py           ← HomeKey (ce qui fait « le même logement »)
│   │   ├── listing_sort.py       ← ListingSort (ordre d'affichage demandé)
│   │   ├── location.py           ← Location (city + GPS)
│   │   ├── market_position.py    ← RentReference, MarketPosition, NoMarketPosition (ADR-0010)
│   │   ├── price.py              ← Price (Decimal, charges séparées)
│   │   ├── publication_source.py ← SITE ou FIRST_SEEN
│   │   └── site_rules.py         ← SiteRules (règles des sites respectées ou ignorées, ADR-0012)
│   ├── ports/
│   │   ├── listing_repository.py
│   │   ├── cache_port.py
│   │   ├── clock_port.py         ← ClockPort (l'heure et l'attente, injectées)
│   │   ├── crawler_port.py
│   │   ├── geocoding_port.py     ← GeocodingPort + GeocodedCities
│   │   ├── notifier_port.py
│   │   └── rent_reference_port.py ← RentReferencePort (références de la Carte des loyers)
│   └── services/
│       ├── advertiser.py         ← detect_advertiser_kind + find_network (particulier / agence / enseigne)
│       ├── arrondissements.py    ← build_arrondissement_name (Paris, Lyon, Marseille sur la carte des loyers)
│       ├── commune_names.py      ← fold_commune_name (une commune, quelle que soit sa graphie)
│       ├── criterion_suggestions.py ← build_criterion_suggestion (la modification de filtre la plus prudente)
│       ├── dismissals.py         ← DismissedHomes (quelles annonces un écart masque)
│       ├── duplicates.py         ← build_home_key + group_duplicates (même logement, plusieurs annonces)
│       ├── energy_regulation.py  ← passoire thermique + calendrier d'interdiction
│       ├── expiry.py             ← SourceFreshness (annonce expirée / source injoignable)
│       ├── furnishing.py         ← detect_furnished(_label/_chip) (règle unique meublé)
│       ├── listing_matcher.py    ← Logique de matching pure
│       ├── listing_order.py      ← sort_listings / build_published_key (ordre affiché)
│       ├── openings.py           ← OpenedHomes (quelles annonces une ouverture éteint)
│       ├── recognised_homes.py   ← RecognisedHomes (même logement : même URL, ou même clé ailleurs)
│       ├── rent_reference_book.py ← RentReferenceBook (position de chaque annonce)
│       ├── sanitising.py         ← clean_text / is_web_url (données scrapées)
│       └── tenancy_scope.py      ← is_out_of_scope_tenancy (coloc, bail mobilité)
│
├── application/
│   └── use_cases/
│       ├── clean_listings.py      ← `hunt clean` : annonces hors filtre ou non revues, à la main
│       ├── crawl_all_sources.py
│       ├── dismiss_home.py        ← écarter un logement, avec sa raison
│       ├── get_top_listings.py
│       ├── manage_filters.py
│       ├── manage_site_rules.py   ← lire / changer les règles des sites (web et `hunt rules`)
│       ├── map_filter_homes.py    ← la carte : logements par commune, communes du rayon
│       ├── notify_new_listings.py
│       ├── open_home.py           ← ouvrir un logement (revue et page web)
│       ├── purge_stale_listings.py
│       ├── refresh_filter.py      ← crawl + purge d'un filtre (un seul foyer)
│       ├── suggest_criteria.py    ← suggestion après un écart : proposer, appliquer, refuser
│       └── watch_filters.py       ← la politique de veille, horloge injectée
│
├── infrastructure/
│   ├── cache/
│   │   └── ttl_cache.py          ← Cache mémoire avec TTL
│   ├── clock.py                  ← AsyncioClock
│   ├── geocoding.py              ← NominatimGeocoding (adaptateur du port)
│   ├── crawlers/
│   │   ├── base_crawler.py       ← Rate limit, retry anti-bot, pagination, helpers
│   │   ├── french_dates.py       ← Dates françaises → datetime
│   │   ├── geo_postal.py         ← ville → code postal, code postal → département (geo.api.gouv.fr)
│   │   ├── robots.py             ← RobotsRules : robots.txt lu et appliqué (RFC 9309)
│   │   ├── pap_crawler.py
│   │   ├── orpi_crawler.py
│   │   ├── foncia_crawler.py
│   │   ├── paruvendu_crawler.py
│   │   ├── century21_crawler.py
│   │   ├── laforet_crawler.py
│   │   ├── citya_crawler.py
│   │   ├── squarehabitat_crawler.py
│   │   ├── bienici_crawler.py    ← règles des sites ignorées seulement (ADR-0012)
│   │   ├── locservice_crawler.py ← règles des sites ignorées seulement
│   │   ├── fnaim_crawler.py      ← règles des sites ignorées seulement
│   │   ├── twoa_immobilier_crawler.py ← règles des sites ignorées seulement
│   │   ├── sbm_immobilier_crawler.py  ← règles des sites ignorées seulement
│   │   └── agence_bfm_crawler.py      ← règles des sites ignorées seulement
│   ├── notifications/
│   │   ├── terminal_notifier.py
│   │   └── composite_notifier.py
│   ├── storage/
│   │   ├── dismissal_codec.py    ← ligne de la table dismissals
│   │   ├── filter_codec.py       ← forme JSON d'un filtre sauvegardé (pur, sans SQL)
│   │   ├── home_key_codec.py     ← clé de logement sur quatre colonnes
│   │   ├── migrations.py         ← DDL SQL
│   │   ├── opening_codec.py      ← ligne de la table openings
│   │   └── sqlite_repository.py
│   ├── config.py                 ← Pydantic-settings
│   ├── container.py              ← DI manuel
│   ├── geocoder.py               ← Nominatim + geo.api.gouv.fr (+ codes INSEE) + cache
│   └── rent_map.py               ← CarteDesLoyers (CSV ANIL, cache par millésime)
│
└── presentation/
    ├── tri_state.py              ← oui / non / indifférent
    ├── dismissal_reasons.py      ← raisons d'écart : touches + libellés
    ├── cli/
    │   ├── main.py               ← Commandes Typer
    │   ├── session.py            ← Conteneur + logging
    │   ├── adhoc.py              ← Flags ad-hoc → SearchFilter
    │   ├── filter_wizard.py      ← Assistant interactif
    │   ├── formatters.py         ← Affichage Rich
    │   └── review.py             ← Écran de hunt review
    └── web/
        ├── app.py                ← Routes FastAPI
        ├── background_jobs.py    ← Tâches crawl / watch
        ├── filter_payload.py     ← JSON formulaire → SearchFilter
        ├── dismissal_payload.py  ← JSON écart → raison + texte
        ├── serializers.py        ← Entités → JSON
        ├── request_guard.py      ← hôtes admis, écritures cross-site refusées
        ├── ui.py                 ← Assemblage de la page
        └── assets/               ← index.html, styles.css, app.js
```
