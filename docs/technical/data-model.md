# Modèle de données

## Entités du domaine

### Listing — une annonce publiée

```python
@dataclass(frozen=True)  # immuable
class Listing:
    id: str                          # SHA-256(url)[:16] — clé stable
    url: str                         # lien vers l'annonce originale
    title: str                       # titre tel qu'affiché sur le site
    source: str                      # "pap", "orpi", "foncia", "paruvendu", ...
    location: Location               # value object
    price: Price                     # value object (Decimal, jamais float)
    published_at: datetime           # date de parution, ou 1er crawl en repli
    published_at_source: PublicationSource  # SITE (annoncée) | FIRST_SEEN (repli)

    # optionnels — présents selon la source
    surface_m2: float | None
    rooms: int | None
    floor: Floor | None
    dpe_rating: DpeRating | None   # énergie A→G
    ges_rating: DpeRating | None   # émissions A→G (même value object)
    furnished: bool | None
    charges_included: bool | None
    collective_heating: bool | None
    description: str | None
    advertiser: str | None   # l'agence qui publie ; None pour un particulier
    images: tuple[str, ...]          # URLs des photos
    fetched_at: datetime             # date de récupération par le crawler
    last_seen_at: datetime           # dernier crawl qui l'a renvoyée (avance, ne recule jamais)
    opened_at: datetime | None       # posé par GetTopListings, jamais stocké sur la ligne (ADR-0009)
    source_down_days: int            # posé par GetTopListings, jamais stocké ; 0 = source qui répond
    market_position: MarketAssessment # posé par GetTopListings, jamais stocké (ADR-0010)
    former_dismissal: Dismissal | None # écart à un autre loyer, jamais stocké (ADR-0009)
    restored_at: datetime | None      # écart repris par le chasseur, jamais stocké sur la ligne

    # dérivés — aucun stockage propre
    @property
    def opened(self) -> bool            # opened_at connu : plus *Nouvelle*
    @property
    def charges_unknown(self) -> bool   # ni provision publiée, ni mention « CC »
```

**Frozen dataclass :** une fois créé, un `Listing` ne peut pas être modifié. Cela garantit la cohérence des données et permet de les utiliser comme clés de dict ou éléments de set.

**`opened_at`** n'est jamais posé par un crawler ni lu sur la ligne : `GetTopListings`
le pose d'après la table `openings` (`OpenedHomes.annotate`), à la première ouverture de
n'importe quelle annonce du même logement. C'est `opened` — et non l'ordre d'arrivée —
qui décide du badge « Nouveau »
([ADR-0002](../decisions/0002-nouveau-signifie-pas-encore-ouverte.md)) ; la revue
affiche « ouverte le … ».

**`former_dismissal`** n'est jamais stocké : `DismissedHomes.annotate` y pose le dernier
écart du même logement **à un autre loyer** (même commune, pièces et surface,
`HomeKey.layout`), que le changement de loyer ne laisse plus masquer. Il ne sert qu'à la
mention « écarté le … à N € (raison) » (`Dismissal.format_mention`), lue par la revue,
la carte web (`former_dismissal`, `''` sinon) et l'alerte terminal.

**`restored_at`** n'est pas lu sur la ligne d'annonce : `RestoredHomes.annotate` le pose
d'après `dismissals.restored_at` (`list_restored_dismissals`), reconnu comme un écart
— même URL, ou même clé sur une autre source. Il donne « restauré le … » à la revue, à la
carte web (`restored`, `''` sinon) et à l'alerte terminal ; réécarter remplace la ligne, et
la mention disparaît.

**`price`** suit la source : un crawl qui renvoie l'URL réécrit le loyer de la ligne
(`_update_price_and_place`), et les charges seulement quand il les lit. Les insertions étant
`INSERT OR IGNORE`, un loyer baissé sur la même annonce restait figé à sa première
lecture.

**`city`** et **`title`** suivent la source de la même façon, le code postal seulement
quand le crawl le lit. Une annonce porte la commune que **sa propre carte** nomme, jamais
la commune cherchée (`parse_commune_label`, `MissingCommuneError` dans `base_crawler.py`) :
ParuVendu et Foncia rangeaient chaque carte sous la commune cherchée, et les lignes déjà
stockées ainsi sont corrigées au crawl suivant.

**`last_seen_at`** avance à chaque crawl qui renvoie l'URL (`save_many`, jamais en
arrière : deux filtres crawlés en même temps peuvent l'écrire dans le désordre) ;
`fetched_at` reste la première détection. **`source_down_days`** n'est jamais stocké :
`GetTopListings` le pose sur une annonce dont la source ne répond plus au filtre
(`domain/services/expiry.py`, voir *Annonce expirée* dans le glossaire). **`market_position`**
non plus : `RentReferenceBook.annotate` la pose d'après la Carte des loyers, soit une
`MarketPosition` (écart au loyer de référence), soit une `NoMarketPosition` qui dit pourquoi.

**`charges_unknown`** est calculé, pas stocké : vrai quand le total mensuel est un
loyer sans charges prises en compte. Un seul foyer pour les trois lecteurs (carte web,
tableau CLI, `build_summary_line()` de l'alerte) —
[ADR-0003](../decisions/0003-budget-en-charges-comprises.md).

### SearchFilter — critères de recherche

```python
@dataclass  # mutable — l'utilisateur peut modifier ses filtres
class SearchFilter:
    id: str                          # UUID court (8 chars)
    name: str                        # label lisible
    cities: list[str]
    radius_km: float
    excluded_cities: list[str]
    min_price: int | None
    max_price: int | None
    max_results: int                 # plafond de résultats (défaut 25, paginés au-delà)
    ...                              # voir docs/functional/filters.md
```

`__post_init__` refuse un filtre hors bornes (intervalles ≥ 5 min, rayon 1–150 km,
`max_results` 1–500, aucun bound négatif) : voir *Bornes d'un filtre* dans
[security.md](security.md). Une ligne écrite avant ces bornes est ramenée dedans au
chargement plutôt que de casser le démarrage.

---

## Value Objects

Les value objects encapsulent une valeur métier avec sa logique. Tous sont **immutables** (frozen dataclass ou Enum).

### Price

```python
@dataclass(frozen=True)
class Price:
    amount: Decimal       # loyer de base — Decimal, jamais float
    charges: Decimal | None   # charges mensuelles séparées
    currency: str = "EUR"

    @property
    def total(self) -> Decimal:     # loyer + charges
    def format_display(self) -> str:       # "950€/mois (+ 50€ charges)"
    def format_total(self) -> str: # "1000€/mois CC"
```

**Pourquoi `Decimal` et pas `float` ?**  
`float(950) + float(50) = 999.9999999...` — problèmes d'arrondi sur les comparaisons de prix. `Decimal` est exact.

### DpeRating

```python
class DpeRating(str, Enum):
    A = "A"  # meilleur
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"  # pire
```

Supporte les opérateurs de comparaison (`<=`, `<`, etc.) via `.compute_rank()` :

```python
DpeRating.A <= DpeRating.D  # True — A est meilleur que D
DpeRating.E <= DpeRating.D  # False — E est pire que D
```

### Floor

```python
@dataclass(frozen=True)
class Floor:
    level: int      # 0 = RDC, 1 = 1er, 2 = 2ème, -1 = inconnu
    is_top: bool    # True = dernier étage

    @property
    def is_ground(self) -> bool: return self.level == 0
    @property
    def is_first(self) -> bool:  return self.level == 1
    def format_label(self) -> str:      # "4ème étage (dernier)"
```

### Location

```python
@dataclass(frozen=True)
class Location:
    city: str
    postal_code: str | None
    latitude: float | None     # WGS84
    longitude: float | None    # WGS84
    full_address: str | None
    department: str | None

    @property
    def has_coordinates(self) -> bool
    @property
    def coordinates(self) -> tuple[float, float] | None
```

---

## Schéma SQLite

### Table `listings`

```sql
CREATE TABLE listings (
    id TEXT PRIMARY KEY,           -- SHA-256(url)[:16]
    url TEXT NOT NULL UNIQUE,      -- contrainte d'unicité sur l'URL
    title TEXT NOT NULL,
    source TEXT NOT NULL,          -- "pap", "orpi", ...
    city TEXT NOT NULL,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    full_address TEXT,
    price_amount TEXT NOT NULL,    -- stocké en TEXT pour préserver Decimal
    price_charges TEXT,
    surface_m2 REAL,
    rooms INTEGER,
    floor_level INTEGER,           -- -1 si inconnu
    floor_is_top INTEGER,          -- 0 ou 1 (SQLite n'a pas de BOOLEAN)
    dpe_rating TEXT,               -- "A", "B", ..., "G" (énergie)
    ges_rating TEXT,               -- "A", "B", ..., "G" (émissions)
    furnished INTEGER,
    charges_included INTEGER,
    collective_heating INTEGER,
    published_at TEXT NOT NULL,    -- ISO 8601 naïf, heure locale (format unique comparable)
    -- title / city / full_address / description / advertiser : nettoyés à l'écriture
    -- (null bytes retirés, longueur plafonnée) — voir security.md
    published_at_source TEXT NOT NULL DEFAULT 'first_seen',  -- 'site' | 'first_seen'
    fetched_at TEXT NOT NULL,
    description TEXT,
    images TEXT DEFAULT '[]',      -- JSON array d'URLs
    advertiser TEXT,
    opened_at TEXT,                -- n'est plus lue : vidée dans `openings` par la migration
    last_seen_at TEXT              -- dernier crawl qui l'a renvoyée ; = fetched_at à l'insertion
);

CREATE INDEX idx_listings_published ON listings(published_at DESC);
CREATE INDEX idx_listings_source ON listings(source);
```

**Pourquoi TEXT pour `price_amount` ?**  
SQLite n'a pas de type DECIMAL natif. Stocker en TEXT préserve la précision et évite la conversion float. La comparaison se fait via `CAST(price_amount AS REAL)` dans les requêtes.

### Table `filters`

```sql
CREATE TABLE filters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config TEXT NOT NULL,    -- SearchFilter sérialisé en JSON
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
```

Le filtre est stocké sérialisé en JSON dans `config`. Cela évite de faire évoluer le schéma SQL à chaque ajout de critère.

### Table `notifications`

```sql
CREATE TABLE notifications (
    listing_id TEXT NOT NULL REFERENCES listings(id),
    filter_id TEXT NOT NULL REFERENCES filters(id),
    notified_at TEXT NOT NULL,
    PRIMARY KEY (listing_id, filter_id)   -- clé composite = pas de doublon
);

CREATE INDEX idx_notifications_filter ON notifications(filter_id);
```

**Rôle :** trace quelle annonce a été notifiée pour quel filtre. La clé composite garantit qu'on ne notifie qu'une fois par couple (annonce, filtre).

### Table `dismissals`

```sql
CREATE TABLE dismissals (
    listing_id TEXT PRIMARY KEY,       -- l'annonce sur laquelle l'écart a été fait
    source TEXT NOT NULL,
    home_city TEXT,                    -- clé de logement (HomeKey, commune repliée), NULL quand pièces ou
    home_rooms INTEGER,                -- surface sont inconnues : l'écart n'est alors
    home_surface_m2 INTEGER,           -- reconnu que par l'URL
    home_rent TEXT,
    reason TEXT NOT NULL,              -- DismissalReason (valeur stockée)
    note TEXT NOT NULL DEFAULT '',     -- texte libre, pour la raison « autre » seulement
    dismissed_at TEXT NOT NULL,
    total_price TEXT NOT NULL,         -- photo figée de l'annonce jugée
    surface_m2 REAL,
    floor_level INTEGER,
    dpe_rating TEXT,
    advertiser TEXT,
    furnished INTEGER,
    restored_at TEXT               -- NULL = en vigueur ; horodaté quand le chasseur restaure
);
```

**Rôle :** un logement *écarté* par le chasseur ([ADR-0009](../decisions/0009-le-chasseur-ecarte-un-logement.md)). **Pas de clé étrangère vers `listings`, exprès** : la purge supprime les lignes d'annonce, et l'écart doit leur survivre. Une annonce est masquée quand elle serait regroupée avec une annonce écartée au sens de *Doublon* — même URL, ou même clé de logement sur une autre source (`DismissedHomes`, `domain/services/dismissals.py`). Réécarter la même annonce remplace la ligne. **Restaurer** pose `restored_at` sans supprimer la ligne : l'écart ne masque plus et ne compte plus, mais la trace « déjà jugé une fois » reste (`list_dismissals` ne rend que les écarts en vigueur). La photo figée (total CC, surface, étage, DPE, annonceur, meublé) nourrit les suggestions de critère.

### Table `app_settings`

```sql
CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,          -- 'site_rules'
    value TEXT NOT NULL            -- 'honoured' (défaut, ligne absente) | 'ignored'
);
```

**Rôle :** les choix du chasseur qui valent pour tout crawl, quel que soit l'écran qui
les a faits. Une seule clé aujourd'hui, `site_rules` (`SiteRules`,
[ADR-0012](../decisions/0012-le-chasseur-peut-ignorer-les-regles-des-sites.md)) :
absente, les règles des sites sont respectées.

### Table `openings`

```sql
CREATE TABLE openings (
    listing_id TEXT PRIMARY KEY,   -- la première ouverture de l'annonce est gardée (INSERT OR IGNORE)
    source TEXT NOT NULL,
    home_city TEXT,                -- clé de logement : NULL quand pièces ou surface manquent
    home_rooms INTEGER,
    home_surface_m2 INTEGER,
    home_rent TEXT,
    opened_at TEXT NOT NULL
);
```

**Rôle :** les annonces que le chasseur a *ouvertes* vers leur source, seule source de vérité de *Nouvelle* depuis l'[ADR-0009](../decisions/0009-le-chasseur-ecarte-un-logement.md). **Pas de clé étrangère vers `listings`, exprès**, comme `dismissals` : une ouverture survit à la purge. Une annonce est ouverte quand elle serait regroupée avec une annonce ouverte au sens de *Doublon* — même URL, ou même clé de logement sur une autre source (`OpenedHomes`, sur le même index `RecognisedHomes` que les écarts). Écrite par `OpenHome`, que la revue (`o`) et `POST /api/listings/{id}/opened` appellent tous deux.

### Table `filter_source_successes`

```sql
CREATE TABLE filter_source_successes (
    filter_id TEXT NOT NULL,
    source TEXT NOT NULL,
    answered_at TEXT NOT NULL,     -- dernier crawl de ce filtre où la source a répondu
    PRIMARY KEY (filter_id, source)
);
```

**Rôle :** distinguer une annonce *expirée* d'une annonce dont la *source est injoignable*. `RefreshFilter` y écrit les *sources faisant autorité* après chaque crawl d'un filtre enregistré (jamais pour un filtre ad hoc). Par filtre et non global : une source qui répond pour un autre secteur ne dit rien des annonces de celui-ci. Supprimée avec son filtre (`delete_filter`).

### Table `criterion_refusals`

```sql
CREATE TABLE criterion_refusals (
    filter_id TEXT NOT NULL,
    reason TEXT NOT NULL,          -- DismissalReason.value
    value TEXT NOT NULL,           -- commune repliée, annonceur, étage, meublé ; '' sans valeur
    refused_at TEXT NOT NULL,
    dismissal_count INTEGER NOT NULL, -- écarts en vigueur pour cette raison et valeur au refus
    PRIMARY KEY (filter_id, reason, value)
);
```

**Rôle :** une *suggestion de critère* refusée. La question ne revient qu'une fois les écarts
de cette raison et valeur arrivés à `dismissal_count + 3` (`build_criterion_suggestion`).
Pas de lien vers `listings` : la purge n'efface jamais un refus. Supprimée avec son filtre.

---

## Requête principale — `find_new_since`

Récupère les annonces pas encore notifiées pour un filtre donné :

```sql
SELECT a.* FROM listings a
WHERE NOT EXISTS (
    SELECT 1 FROM notifications n
    WHERE n.apartment_id = a.id AND n.filter_id = ?
)
ORDER BY a.published_at DESC
LIMIT 200
```

Utilise `NOT EXISTS` (plus efficace qu'un `LEFT JOIN ... WHERE n.id IS NULL` sur SQLite).

## Requête principale — `find_top`

Pré-filtre **grossier** en SQL (prix avec marge, DPE, fraîcheur), puis le matching fin (rayon géo, surface, pièces, étage, meublé, charges…) se fait en mémoire dans `ListingMatcher` :

```sql
SELECT * FROM listings
WHERE CAST(price_amount AS REAL) <= ?       -- prix max × 1.2 (marge communes proches)
  AND CAST(price_amount AS REAL) >= ?       -- prix min × 0.8
  AND (dpe_rating IS NULL OR dpe_rating IN (?, ?, ?, ?))  -- DPE dans le set accepté
  AND datetime(published_at) >= datetime('now', 'localtime', '-' || ? || ' days')  -- max_age_days
ORDER BY published_at DESC                    -- ou prix / surface, selon le tri demandé
LIMIT ?                                       -- min(limit × 50, 500)
```

Le SQL **ne filtre pas par ville** : le rayon géographique couvre des communes voisines, et le matcher décide de l'inclusion via les coordonnées (annonce ou commune géocodée). Le gros sur-fetch (× 50) laisse de la marge au matcher pour le filtrage géo et les autres critères, faits ensuite en Python.

Les deux comparaisons de date passent par `datetime(...)` : la valeur stockée garde le
séparateur ISO `T`, qui comparé brut à la sortie de `datetime('now')` (séparée par un
espace) est toujours « plus grand » — la fenêtre `max_age_days` gardait alors des annonces
trop vieilles d'un jour.

### Ordre d'affichage

Le tri par défaut est **la date de parution décroissante** (plus récent d'abord). L'API web
accepte `?sort=` avec les valeurs de l'enum `ListingSort` : `published_desc` (défaut),
`price_asc`, `price_desc`, `surface_desc`, `price_per_m2_asc` (total CC au m², sans surface
en fin) et `market_position` (le plus bas face au loyer de référence d'abord, sans repère
en fin, ADR-0010) ; une valeur inconnue retombe sur le défaut. `hunt review` s'ouvre, lui,
sur `market_position` et la touche `s` fait tourner position → €/m² → parution.

L'ordre décide **quels candidats survivent au `LIMIT`**, donc il est exprimé deux fois :
en SQL (`_ORDER_BY` dans `sqlite_repository`) pour couper la fenêtre sur la bonne clé, et
en Python (`domain/services/listing_order.py`) qui fait foi sur le résultat final. Les deux
représentations sont verrouillées par `tests/infrastructure/test_sqlite_sort_parity.py` :
le test échoue dès qu'elles divergent. Le tri parution s'applique d'abord et le `sorted`
de Python est stable, donc une égalité de prix ou de surface est départagée par la parution.

La **position** n'a pas de forme SQL : elle demande la Carte des loyers, que la base n'a
pas. `ListingSort.window_sort` dit sur quel ordre couper la fenêtre : pour la position,
le €/m², son plus proche substitut ; la position elle-même est triée en Python sur toute
cette fenêtre, avant la limite du nombre de résultats, pour classer le vivier et pas les
seules annonces récentes. Le test de parité couvre donc tous les ordres sauf celui-là, et
le €/m² y compris les annonces sans surface.

`published_at` est stocké en ISO **naïf, heure locale** (`build_published_key`) : les sources
mélangent dates tz-aware (SeLoger) et `datetime.now()` naïf, et un décalage conservé tel
quel classait une annonce plus récente sous une plus ancienne. Une migration de données
idempotente (`DATA_MIGRATIONS`) convertit au démarrage les lignes historiques qui portent
encore un offset.

---

## Migrations

Les migrations sont appliquées au démarrage si la table `schema_version` n'existe pas. Chaque `CREATE TABLE IF NOT EXISTS` est idempotent.

```python
# infrastructure/storage/migrations.py
MIGRATIONS: list[str] = [
    "CREATE TABLE IF NOT EXISTS listings ...",
    "CREATE INDEX IF NOT EXISTS ...",
    ...
]
```

Les tables ajoutées après la première version (`dismissals`, `openings`,
`filter_source_successes`, `criterion_refusals`) vivent dans `TABLE_MIGRATIONS`, des `CREATE TABLE IF NOT EXISTS` rejoués à chaque démarrage comme les index.

`dismissals.home_city` est stocké **replié** (`fold_commune_name`, voir *Commune* dans le glossaire) depuis que la clé de logement compare les communes repliées. Les écarts écrits avant gardaient la graphie du site (« Chambéry ») et ne reconnaissaient plus le même logement republié en « Chambery ». Une migration de `DATA_MIGRATIONS` les réécrit : SQLite ne sait pas retirer un accent, donc `SqliteRepository` enregistre `fold_commune_name` comme fonction SQL (`FOLD_COMMUNE_SQL_FUNCTION`) avant de rejouer les migrations de données. Le repli est idempotent, la rejouer à chaque démarrage ne change rien. `tests/infrastructure/test_sqlite_dismissals.py` remet une graphie d'origine dans un fichier SQLite réel et vérifie qu'à la réouverture l'écart masque le logement republié sous l'autre graphie.

Pour les colonnes ajoutées après coup (ex. `ges_rating`, `published_at_source`, `opened_at`, `last_seen_at`), `COLUMN_MIGRATIONS` contient des `ALTER TABLE ... ADD COLUMN` idempotents rejoués à chaque démarrage (l'erreur « duplicate column » est ignorée), pour que les bases existantes récupèrent les nouvelles colonnes.

`last_seen_at` est rempli depuis `fetched_at` par `DATA_MIGRATIONS` pour les lignes antérieures : faute de mieux, une annonce a été vue pour la dernière fois quand elle l'a été pour la première.

`opened_at` était `NULL` par défaut, ce qui décrivait exactement l'existant : avant cette colonne, le badge « Nouveau » était local à la session et rien n'était enregistré. Depuis la table `openings`, la colonne n'est plus lue : à chaque démarrage, `SqliteRepository._migrate_row_openings` change chaque horodatage restant en ouverture (clé de logement calculée par `build_home_key`, en Python pour ne pas recopier la règle en SQL), puis vide la colonne. Une base déjà migrée n'a plus rien à déplacer : la migration ne joue qu'une fois. `tests/infrastructure/test_sqlite_opened.py` pose un horodatage à l'ancienne dans un fichier SQLite réel et vérifie l'ouverture produite, puis qu'un second démarrage n'en crée pas d'autre.

`RENAME_MIGRATIONS` renomme en place ce que le glossaire a rebaptisé — table `apartments` → `listings`, colonne `agency` → `advertiser`, `notifications.apartment_id` → `listing_id` — puis rejoue `INDEX_MIGRATIONS`, seul foyer de la liste des index. SQLite réécrit seul les clés étrangères visant la table renommée, et rejouer un renommage déjà fait lève une erreur qui est ignorée : c'est ce qui le rend idempotent. `tests/infrastructure/test_sqlite_rename_migration.py` ouvre une base à l'ancien schéma et vérifie que les annonces, leur annonceur et leurs notifications survivent, et que le schéma migré est identique à un schéma neuf.

`published_at_source` a pour défaut `'first_seen'` : les lignes écrites avant son existence contenaient précisément une date de premier crawl, le défaut les qualifie donc correctement. Les insertions étant `INSERT OR IGNORE`, `_backfill_site_dates` met ensuite à jour ces lignes dès qu'une source publie une vraie date de parution — sans jamais écraser une date déjà marquée `'site'`.
