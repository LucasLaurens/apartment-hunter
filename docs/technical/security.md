# Sécurité

## Credentials

**Règle :** aucune donnée sensible dans le code source ou les fichiers versionnés.

### Ce qui NE doit jamais être commité

- `.env` (config locale)
- `apartment_hunter.db` (données scrapées)

`.env.example` est versionné, avec des valeurs d'exemple uniquement : `cp .env.example .env`
puis remplir.

### .gitignore recommandé

```gitignore
.env
*.db
*.db-shm
*.db-wal
__pycache__/
.pytest_cache/
dist/
```

### Chargement des credentials

Via `pydantic-settings` — lit le fichier `.env` automatiquement :

```python
class Settings(BaseSettings):
    database_url: str = "apartment_hunter.db"
    # Accès via get_settings().database_url
```

Si une variable n'est pas définie, la valeur par défaut est utilisée (jamais une erreur de démarrage).

---

## Sécurité des données scrapées

### Injection SQL

SQLite via `aiosqlite` avec requêtes paramétrées — jamais de f-string dans les requêtes SQL :

```python
# ✅ Paramétré — sûr
await self._conn.execute(
    "INSERT INTO listings (id, url) VALUES (?, ?)",
    (listing.id, listing.url)
)

# ❌ Ne jamais faire
await self._conn.execute(f"INSERT ... VALUES ('{listing.url}')")
```

### Injection via données scrapées

Un titre, une adresse ou un `href` viennent d'un tiers : ils peuvent porter des null
bytes, un texte de 400 ko, du HTML, ou un lien `javascript:`. La règle vit à **un seul
endroit** : `domain/services/sanitising.py`, appliquée à la frontière de stockage
(`SqliteRepository`), donc valable pour les 9 crawlers actuels et les suivants.

| Danger | Protection | Où |
|--------|-----------|-----|
| Null bytes, texte géant | `clean_text()` — retire `\x00`, `strip()`, coupe à `MAX_TEXT_CHARS` (500) / `MAX_DESCRIPTION_CHARS` (5000) | `_to_row()` |
| Lien non web (`javascript:`, `data:`, `file:`) | `is_web_url()` — l'annonce entière est écartée, l'image aussi | `save_many()` / `_to_row()` |
| Injection SQL | requêtes paramétrées (voir ci-dessus) | tout le repository |
| XSS dans l'interface web | `escHtml()` pour le texte et les attributs, `safeUrl()` avant tout `href` | `assets/app.js` |
| Balisage Rich dans l'alerte terminal | `rich.markup.escape()` sur chaque ligne | `terminal_notifier.py` |
| `eval` / `exec` | jamais utilisés sur des données scrapées | — |

**Piège du contexte JS** : une entité HTML (`&#39;`) est décodée par le parseur *avant*
que le corps d'un `onclick` soit compilé — échapper ne protège donc pas un attribut
d'événement. Une valeur scrapée voyage en `data-*` et le handler est branché après le
rendu (`wireSourceButtons()`), jamais interpolée dans du JS inline.

### Bornes d'un filtre

`SearchFilter.__post_init__` refuse ce que la boucle de surveillance ne peut pas honorer —
ce n'est pas cosmétique : un intervalle ≤ 0 place la prochaine échéance dans le passé et
la boucle re-crawle les 8 sources **à chaque tick** (~1 s), et un rayon énorme étend le
crawl à des milliers de communes. Dans les deux cas : martèlement des sites et ban IP.

| Champ | Borne |
|-------|-------|
| `notification_interval_minutes`, `refresh_interval_minutes` | ≥ `MIN_INTERVAL_MINUTES` (5) |
| `radius_km` | `MIN_RADIUS_KM` (1) → `MAX_RADIUS_KM` (150) |
| `max_results` | 1 → `MAX_MAX_RESULTS` (500) |
| prix, surfaces, pièces, âge, photos | jamais négatifs, toujours un nombre (`nan`, `inf` refusés) |
| `max_age_days` | ≤ `MAX_AGE_DAYS` (3650) : au-delà, `maintenant − âge` sort du calendrier et chaque page du filtre répondait 500 |
| `cities` | ≤ `MAX_CITIES` (10) : chaque ville est un appel Nominatim. Borne de saisie : les communes du rayon passées aux sources par ville (`with_crawl_cities`) n'y sont pas soumises, `_MAX_COMMUNES` (30) les borne |

L'API web renvoie **400** avec le message d'erreur (le `min`/`max` du formulaire n'est
qu'un confort client). Les overrides CLI `hunt watch --interval/--refresh` contournent
l'entité : ils sont refusés séparément dans `main.py`. Un filtre enregistré avant ces
bornes n'empêche pas le démarrage : il est **ramené dans les bornes** au chargement, avec
un warning (`_filter_from_json`).

---

## Rate limiting et respect des sites

### Pourquoi c'est aussi une mesure de sécurité

Un crawler trop agressif peut :
- Déclencher un ban IP permanent
- Affecter les performances d'un site tiers
- Engager la responsabilité légale (atteinte à un STAD en France)

### Ce qui est en place

| Mesure | Implémentation |
|--------|----------------|
| Délai minimum entre requêtes | `RATE_LIMIT_SECONDS` par domaine |
| Un nom honnête | `CRAWLER_USER_AGENT` sur chaque requête : ni rotation, ni en-têtes ou empreinte TLS de navigateur imités (`test_no_evasion.py`) |
| Un refus est respecté | 401/403 : pas de nouvel essai ; une source qui refuse durablement est retirée |
| Backoff sur erreur transitoire | 408/429/5xx : 3 essais, 2 s puis 4 s (`_fetch_page`, `tenacity` pour PAP) |
| Semaphore global | `max_concurrent=5` — pas plus de 5 connexions simultanées |

| Nominatim à une requête par seconde | `RateLimiter` de geopy dans `geocode_cities` (`_NOMINATIM_MIN_DELAY_SECONDS`) : sa politique d'usage, sinon ban IP |

### Ce qui est recommandé

- Ne pas descendre en dessous de 10 minutes d'intervalle entre cycles
- `robots.txt` est appliqué par le code (`RobotsRules`, voir crawlers.md) : rien à surveiller à la main, sauf si le chasseur choisit d'ignorer les règles des sites (ADR-0012) ; les protections anti-bot restent respectées dans tous les cas
- En cas de 429 (Too Many Requests), augmenter `RATE_LIMIT_SECONDS` dans `.env` (le retry `_fetch_page` absorbe déjà les 429 passagers)

---

## Données personnelles

L'application stocke des données publiques d'annonces immobilières — aucun compte, aucune
donnée personnelle d'utilisateur. La base SQLite locale ne sort jamais du poste (pas de
cloud sync).

Le seul notifieur est le terminal (`build_notifiers()`) : aucun credential n'est lu ni
stocké. Les notifieurs e-mail, bureau et macOS ont été supprimés le 2026-10-31.

## Surface d'écoute de l'interface web

L'API n'a **aucune authentification** : elle est conçue pour `127.0.0.1`
(défaut de `hunt serve`). `--host 0.0.0.0` expose crawl, watch et suppression de filtres à
tout le réseau — à éviter hors machine isolée.

Ce qui protège contre une page tierce ouverte dans le même navigateur
(`presentation/web/request_guard.py`, tenu par `tests/presentation/test_request_guard.py`) :

- **Rebinding DNS** : une page peut faire pointer son propre domaine vers 127.0.0.1 et lire
  l'API comme si elle était de même origine. `TrustedHostMiddleware` n'accepte que
  `127.0.0.1`, `localhost` et l'hôte passé à `hunt serve --host` (400 sinon).
- **Écritures cross-site** : `POST /api/listings/{id}/opened` n'a pas de corps, donc le
  refus des corps `text/plain` ne le protégeait pas ; un simple `<form method=post>` d'un
  autre site effaçait un badge « Nouveau ». Toute écriture dont le navigateur annonce une
  autre origine (`Sec-Fetch-Site`, à défaut `Origin`) reçoit 403. Une requête sans ces
  en-têtes (curl, la CLI) n'est pas une page de navigateur et passe.
- Aucun middleware CORS : une lecture cross-origin reste bloquée par le navigateur.

`GET /api/area` est la seule route de lecture qui déclenche un appel sortant (le géocodage
des communes du rayon). Une page tierce peut l'appeler sans en lire la réponse ; le rayon
est borné (1–150 km, 422 au-delà) et le géocodage est en cache 24 h, donc l'effet se limite
à des requêtes déjà permises.

## Code tiers dans la page (carte, ticket 14)

La carte est le seul code tiers de la page : MapLibre GL, depuis unpkg, et les tuiles
d'OpenFreeMap.

- **Épinglé et vérifié** : version exacte (`maplibre-gl@4.7.1`), `integrity` sha384 et
  `crossorigin="anonymous"` sur le script et la feuille de style (`MAP_LIBRARY` dans
  `app.js`). Mettre à jour = changer la version **et** recalculer les deux empreintes :
  `curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A`.
- **Chargé à la demande** : rien n'est demandé à unpkg ni à OpenFreeMap tant qu'aucune
  carte n'est ouverte (bascule « Carte » ou modale du filtre). Ouvrir une carte révèle à
  OpenFreeMap la zone consultée ; la page le dit sous la carte.
- **Aucune donnée scrapée en HTML** : les pastilles et le détail d'une commune sont
  construits en DOM avec `textContent`, jamais `setHTML` ; un lien passe par `safeUrl`.
  Les coordonnées viennent de notre géocodage, jamais d'un champ scrapé.
- **Hors ligne** : si la bibliothèque ou l'API ne répondent pas, la carte affiche
  « Carte indisponible » et la liste comme le filtre restent utilisables.

`tests/presentation/test_web_asset_guards.py` échoue sur une version flottante, une empreinte
manquante, une balise externe sans `integrity` ou un `setHTML`.

---

## Dépendances

Maintenir les dépendances à jour :

```bash
uv lock --upgrade     # met à jour le lockfile
uv sync               # installe les nouvelles versions
```

Vérifier les vulnérabilités connues :

Dernier passage le 2026-10-31 : 6 paquets vulnérables (anyio, certifi, filelock, geopy,
soupsieve, virtualenv), mis à jour dans le lockfile ; aucune vulnérabilité connue ensuite.

```bash
make audit   # le lockfile exporté, passé à pip-audit le temps de l'exécution
```
