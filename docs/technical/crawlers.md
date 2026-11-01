# Crawlers

## BaseCrawler — comportements communs

Tous les crawlers héritent de `BaseCrawler` (`infrastructure/crawlers/base_crawler.py`).

### Rate limiting

`RATE_LIMIT_SECONDS` est un **budget par fenêtre**, pas un délai entre deux requêtes
consécutives : une source est interrogée `CITY_CONCURRENCY` communes à la fois, donc
l'espacement effectif entre deux départs est `RATE_LIMIT_SECONDS / CITY_CONCURRENCY`
(`compute_request_spacing_seconds()`). Espacer en série ferait dépasser le plafond de 180 s par
source — voir [ADR-0008](../decisions/0008-cadence-de-crawl-fenetre-partagee.md).

Une seule porte tient ce rythme, `BaseCrawler._await_turn()`, et elle vaut pour **tout**
le crawler : le chemin HTML (`_fetch_html`) comme `_get_throttled`.

```python
async with self._pace_lock:          # tenu pendant l'attente, pas seulement autour
    if (wait := self._next_slot_at - loop.time()) > 0:
        await asyncio.sleep(wait)
    started = max(loop.time(), self._next_slot_at)
    self._next_slot_at = started + self.compute_request_spacing_seconds()
```

Chaque appelant réserve ainsi le **prochain créneau libre**. Sans le verrou, quatre
recherches de communes simultanées lisaient la même échéance, dormaient la même durée et
repartaient ensemble.

> Avant cette porte, `RATE_LIMIT_SECONDS` n'était lu que par `_get_throttled` — emprunté
> par un seul crawler sur neuf. Les huit autres ne temporisaient rien du tout, et SeLoger
> réimplémentait le calcul à la main contre l'attribut privé de la classe de base.

Le budget est **par instance de crawler** (et donc par domaine), pas global. Les 9
crawlers tournent en parallèle sans se gêner mutuellement.

| Crawler | Rate limit |
|---------|-----------|
| PAP | 2s |
| Orpi | 2.0s |
| Foncia | 2.0s |
| ParuVendu | 2.0s |
| Century21 | 2.0s |
| Laforêt | 2.0s |
| Citya | 2.0s |
| Square Habitat | 2.5s |

### Un seul nom, aucun déguisement

Chaque requête porte `CRAWLER_USER_AGENT` (`base_crawler.py`), le même pour toutes les sources :

```python
CRAWLER_USER_AGENT: Final = "apartment-hunter/0.1 (personal home search)"
```

Ni rotation de User-Agent, ni en-têtes de navigateur imités (`sec-ch-ua`…), ni empreinte TLS
empruntée (`impersonate`) : un site doit pouvoir refuser ce client en le reconnaissant. Une source
qui ne répond qu'à un client déguisé est **retirée** (Figaro et EntreParticuliers, 2026-10-31).
`tests/infrastructure/test_no_evasion.py` lit le code source et échoue au premier de ces
marqueurs ; il vérifie aussi, contre un serveur local, qu'un 403 n'est demandé qu'une fois et
sous ce nom.

### robots.txt, lu et appliqué

`infrastructure/crawlers/robots.py` (`RobotsRules`) garde les deux chemins de requête,
`_fetch_html` et `_get_throttled` (requête comprise) : une URL que le `robots.txt` du site
interdit à ce client n'est jamais demandée, un warning `robots.txt disallows …` le dit. Le
fichier est lu une fois par jour et par hôte, selon la RFC 9309 :

| Réponse à `/robots.txt` | Effet |
|-------------------------|-------|
| 2xx | ses règles s'appliquent, jokers `*` et `$` compris, et son `Crawl-delay` s'il dépasse notre cadence |
| 4xx | pas de règles : rien n'est interdit |
| 5xx ou pas de réponse | règles inconnues : tout est interdit, nouvel essai une heure plus tard |

Les jokers ne sont lus par `urllib.robotparser` qu'à partir de Python 3.13 : en 3.12,
`Disallow: /*?*` laissait passer toute URL à paramètres. D'où le plancher `>=3.13` du projet,
tenu par `tests/infrastructure/test_robots_rules.py`.

Quand le chasseur choisit d'ignorer les règles des sites (`SiteRules.IGNORED`,
[ADR-0012](../decisions/0012-le-chasseur-peut-ignorer-les-regles-des-sites.md)),
`CrawlAllSources` le dit à chaque crawler (`apply_site_rules`) et le garde laisse tout
passer sans lire `robots.txt`. Une source dont les CGU interdisent l'extraction se
déclare `forbids_reproduction = True` : elle n'entre dans le crawl que dans ce mode. Le
reste de la page (nom honnête, pas d'imitation, refus respecté) vaut dans les deux modes.

Constats au premier passage (2026-10-31) : PAP interdit toute URL à paramètres
(`Disallow: /*?*`), donc sa recherche de commune (`/json/ac-geo?q=`), son rayon (`?rayon=`) et
sa page 2 ; Foncia aussi (`Disallow: /*?`), sa page 2 est donc sautée.

### Retry avec backoff exponentiel

`BaseCrawler._fetch_page` (utilisé par les crawlers curl_cffi) ré-essaie les codes
**transitoires** — 408, 429, et 5xx dont le 534 non-standard — jusqu'à 3 fois avec backoff :

```
Tentative 1 → 503 → attendre 2s
Tentative 2 → 503 → attendre 4s
Tentative 3 → 503 → log "blocked — HTTP 503", page sautée (pas de plantage)
```

Un **401/403 est un refus**, pas un accident : aucun nouvel essai, la page est sautée tout de
suite. Le retry réseau côté `httpx` (`tenacity`, `TimeoutException`/`NetworkError`) reste pour
PAP, qui lit aussi ses pages détail par la session de sa recherche : PAP refuse une page détail
(403) à un client qui n'a pas ouvert sa recherche, et la sert à celui qui l'a fait.

### Boîte à outils partagée

`base_crawler.py` regroupe ce que toutes les sources refaisaient à l'identique. Un
nouveau crawler déclare son site et réutilise le reste :

| Élément | Rôle |
|---------|------|
| `BASE_URL` (attribut de classe) | Racine du site : sert aux en-têtes et à `self.resolve_url(href)` |
| `MAX_PAGES` (attribut de classe) | Plafond de pagination (4 par défaut, surchargé par source) |
| `FOLLOW_REDIRECTS` (attribut de classe) | `True` par défaut ; `False` quand une redirection veut dire « pas cette page » (ParuVendu) : `_fetch_page` la lit comme une absence de page |
| `self._fetch_html(url)` | GET cadencé via `_fetch_page`, sous `CRAWLER_USER_AGENT`, `Referer` vers l'accueil du site |
| `self._paginate(build_page_url, parse_page, label)` | Parcourt les pages jusqu'à épuisement (voir plus bas) |
| `build_city_slug(city, separator)` | « Saint-Jorioz » → `saint-jorioz` (Century21 : séparateur `+`) |
| `parse_surface_m2(text)` / `parse_rooms(text)` | « 60,3 m² » → `60.3`, « 3 pièces » / « 3 pcs » → `3` |
| `parse_floor(text)` | « Étage 3/5 », « Etage : 2 », « au 4e étage sur 5 », « RDC » → `Floor` ; `None` si le texte n'en dit rien |
| `parse_price_from_euro_node(card)` | Prix lu sur le nœud qui porte le « € », pas sur toute la carte |
| `read_tag_attr` / `read_tag_classes` | Attributs bs4 typés proprement |
| `is_in_department(listing, dept)` | Garde-fou remplissage national (voir plus bas) |
| `parse_commune_label(text)` | « Gaillard (74) », « Sevrier (74320) » → `("Gaillard", "74")` : commune + département ou code postal |
| `MissingCommuneError` | Levée par `_parse` quand la carte ne nomme aucune commune : la carte est écartée et journalisée |

### Pagination — `_paginate`

Toutes les sources SSR paginent pareil : construire l'URL de la page N, parser ses
cartes, s'arrêter dès qu'une page est illisible, vide, ou ne contient que du déjà-vu
(plusieurs sites resservent la page 1 pour un `page` hors bornes). La boucle vit une
seule fois, dans `BaseCrawler` ; chaque crawler ne fournit que ses deux fonctions :

```python
return await self._paginate(
    lambda page: base_url if page == 1 else f"{base_url}?page={page}",
    parse_page,          # html → list[Listing]
    label=city,          # pour les logs
)
```

Déduplication par id via un `set` — O(cartes) en temps, O(annonces gardées) en mémoire.

### Gestion des erreurs de parsing

Si le parsing d'une annonce individuelle échoue, elle est loggée et ignorée (les autres continuent) :

```python
def _log_parse_error(self, source, url, html_snippet, error):
    preview = html_snippet[:500]
    logger.warning(f"[{source}] Parse error at {url}: {error} — HTML: {preview}")
```

L'extrait HTML dans le log permet de diagnostiquer les changements de template.

### Identification des annonces

```python
def apartment_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]
```

L'ID est dérivé de l'URL, stable et déterministe. Deux crawlers qui trouvent la même annonce sur des sources différentes auront des IDs différents (URLs différentes) — la déduplication par URL est assurée par `INSERT OR IGNORE` en base.

---

## Architecture d'un crawler

```python
class MyCrawler(BaseCrawler):
    source_name = "mysource"           # identifiant en base de données
    BASE_URL = "https://www.mysource.fr"
    MAX_PAGES = 3                      # si le défaut (4) ne convient pas

    async def fetch(self, search_filter: SearchFilter) -> list[Listing]:
        # Recherches par commune en parallèle (bornées) + déduplication
        apts = await self._gather_cities(
            search_filter.cities, lambda c: self._fetch_city(c, search_filter)
        )
        # Une seule passe d'enrichissement page détail, après toutes les communes
        return await self._enrich_details(apts, self._fetch_details)

    async def _fetch_city(self, city: str, f: SearchFilter) -> list[Listing]:
        base_url = f"{self.BASE_URL}/location/{build_city_slug(city)}"

        def parse_page(html: str) -> list[Listing]:
            cards = BeautifulSoup(html, "lxml").select("article.card")
            return [listing for c in cards if (listing := self._parse(c, city))]

        return await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            parse_page,
            label=city,
        )

    async def _fetch_details(self, url: str) -> ListingDetails | None:
        # DPE / GES / date de parution depuis la page détail (mis en cache 24h)
        ...

    def _parse(self, card: Tag, city: str) -> Listing | None:
        # Parser une carte ; retourner None si parsing impossible
        ...
```

---

## Stratégies par type de site

> **Règle du projet :** uniquement des sources **publiques**, accessibles **sans login ni cookie de session**.
> Toute la donnée nécessaire est disponible directement pendant le crawl.

### curl_cffi + BeautifulSoup (Orpi, Foncia, ParuVendu, Century21, Laforêt, Citya)

Sites SSR (cartes dans le HTML serveur), parsés directement :
```python
soup = BeautifulSoup(resp.text, "lxml")
cards = soup.select("article.c-estate-thumb")  # ex. Orpi
```
Les pages passent par `_fetch_page` (client `curl_cffi` sans imitation de navigateur, retry des
seuls codes transitoires). Foncia/ParuVendu résolvent le code postal via geo.api.gouv.fr ;
Century21 utilise un slug ville.

### JSON Angular rendu serveur (Square Habitat)

Les annonces sont dans le `<script id="ng-state">` de la page (clé `apiBienUrl/bien`) :
prix charges comprises, surface, pièces, ville **avec ses coordonnées**, date de création et
photos (`/medias/biens/m/{externalId}.{extension}`). Une seule page **département** couvre le
rayon (`covers_radius`) : son chemin porte des slugs région et département que le filtre ne
connaît pas (`…/auvergne-rhone-alpes/haute-savoie-74`), il est donc lu dans
`sitemap-location-appartement-localisation.xml`. La page détail (son propre ng-state, clé
`apiUrl/page/details-page…`) donne DPE, GES, étage (dernier étage quand `etage` vaut
`nbEtagesBatiment`) et meublé. `robots.txt` interdit `/resultat-location` et `*/immo/*` ; la
route `/annonces/location/bien/…` n'en relève pas.

### httpx + BeautifulSoup (PAP)

`httpx` async classique, parsing des cartes `.search-list-item-alt`. Résout un geoId via une
petite API d'autocomplétion PAP. Seule une réponse est mise en cache (un id, ou « PAP ne connaît
pas cette commune ») : le crawler vit aussi longtemps que `hunt watch`, et un échec mis en cache
(403, timeout) coupait PAP pour toute la veille — c'est la panne du 2026-09-25.

`lxml` est utilisé comme parser (plus rapide que `html.parser`).

### Enrichissement page détail (DPE / GES + étage + meublé + date de parution)

DPE, GES, étage, meublé et date de parution sont rarement sur les cartes de liste.
`BaseCrawler._enrich_details(apts, fetcher)` visite la page détail de chaque annonce (throttlé) et
en tire les cinq d'un coup ; chaque crawler fournit son `_fetch_details(url)` qui renvoie un
`ListingDetails(dpe_rating, ges_rating, published_at, floor, furnished)`. La fusion carte ↔ page
détail vit dans `merge_details(listing, details)` — la page détail gagne champ par champ, un champ
qu'elle ne dit pas garde la valeur de la carte. Résultats **mis en cache 24h** par URL (`DETAIL_CACHE`) pour ne pas re-télécharger à chaque
crawl.

Une seule requête sert tous les besoins : les sites qui cachent les échelles d'énergie sur la page
détail y cachent aussi la date et l'étage. Foncia lit tout depuis la liste et ne fait donc aucune
requête détail ; ParuVendu lit sa date et son DPE/GES sur la carte, et visite la page détail pour
l'étage (souvent bloquée par un captcha) ; Laforêt n'y trouve que l'étage et le meublé (son DPE est une image) et la visite pour ça
seul.

**L'étage** n'est presque jamais sur une carte : les sites l'écrivent soit en label structuré
(« Etage : 2 » chez ParuVendu), soit en prose au milieu de la
description (« se trouve au 4e étage sur 5 »). `parse_floor` couvre les deux — un seul propriétaire
de la règle, plus une copie par crawler. Sans lui, `exclude_ground_floor` / `exclude_first_floor` /
`top_floor_only` restent inertes : le matcher considère un étage inconnu comme un laissez-passer.

**Le meublé** n'est jamais sur une carte non plus : les sites le mettent dans le tableau de
critères de la page détail (« Meublé : non » chez ParuVendu, « Meublé Non » chez Orpi).
`detect_furnished_label` ne lit **que** cette forme étiquetée, et c'est volontaire : le mot nu
apparaît dans la navigation et le pied de page de tous ces sites (« Location meublée Annecy »), donc
`detect_furnished` — la règle par mot-clé, réservée au texte d'une carte — lirait presque toutes les
pages comme meublées et le filtre *non meublé* viderait les résultats. Sans cette lecture le filtre
est inerte dans l'autre sens : le matcher considère un meublé inconnu comme un laissez-passer.

**Tous les sites n'étiquettent pas.** Laforêt écrit le meublé en **puce nue** du tableau de critères
(« Meublé », à côté de « Ascenseur » et « Terrasse »), jamais « Meublé : oui » : la lecture étiquetée
trouvait donc `None` sur *toutes* ses pages et un meublé s'affichait comme inconnu. D'où
`detect_furnished_chip(chips)` : une puce compte seulement si son texte **entier** est le mot
(`fullmatch`), et le crawler ne lui passe que les puces des sections de critères
(`_collect_criteria_chips`, ancré sur les titres « Intérieur / Extérieur / Autres ») — le lien
« Location meublée Annecy » du pied de page et la ligne de critères d'une annonce similaire restent
dehors. Une puce « Non meublé » l'emporte sur une puce « Meublé ». Ordre de lecture chez Laforêt :
puce d'abord, étiquette en secours.

**Lire la lettre du bien, pas celle de la légende.** Toutes ces pages dessinent l'échelle complète
A→G à côté de la note réelle, avec les mêmes classes CSS. Un `re.search` sur le HTML entier renvoie
donc toujours `A`, silencieusement — et le filtre DPE laisse alors passer toute la source. Chaque
crawler doit viser le bloc qui porte la note : `.DPE_consEnerNote` / `.DPE_effSerreNote` chez
ParuVendu (`ParuVenduCrawler.parse_details`, couvert par
`tests/infrastructure/test_paruvendu_energy.py`), l'élément actif chez Orpi.
Chez ParuVendu la classe GES est millésimée (`NoteGES2022_E`) : le suffixe `_<lettre>` est
l'ancrage stable, pas le préfixe. Depuis le 2026-10-28, la page détail ParuVendu répond par un captcha
anti-aspiration (`/communfo/antiaspiration/…/getCaptcha`) : le DPE est lu sur la **carte** (le badge
du bouton « DPE : », jamais une légende) et le GES déduit des kg CO₂ de son infobulle par
`classify_ges` (barème 2021). La page détail, quand elle passe encore, garde le dernier mot.

Les insertions étant `INSERT OR IGNORE`, `SqliteRepository._backfill_detail_fields` réécrit le
DPE/GES, **l'étage et le meublé** des lignes déjà stockées dès qu'un crawl parvient à les lire —
sinon une annonce vue pendant que sa page détail était bloquée (ou lue par un parser fautif)
garderait ce trou pour toujours, et les filtres DPE, étage et meublé continueraient de la laisser
passer. Un crawl qui ne lit rien laisse la valeur en place.

### Date de parution

`Listing.published_at` est doublé d'un `published_at_source` (`PublicationSource`) :

- `SITE` — la date vient de l'annonce elle-même. `format_published_label()` l'affiche telle quelle.
- `FIRST_SEEN` — le site n'en publie aucune : la valeur est l'heure du premier crawl, affichée
  préfixée « vu » (CLI en italique atténué, web en `title` explicite) pour ne pas passer pour une
  parution réelle.

`parse_french_date` (`crawlers/french_dates.py`) absorbe toutes les formulations rencontrées : ISO
avec ou sans heure, `03/08/2026`, `3 août 2026`, `il y a 2 jours`, `aujourd'hui`, `hier`.

Où chaque source publie sa date :

| Source | Où | Coût |
|--------|-----|------|
| **Foncia** | `datePublication` dans l'état SSR Angular de la liste | gratuit |
| **ParuVendu** | date `jj/mm/aaaa` sur la carte (libellée « dernière mise à jour ») | gratuit |
| **Orpi** | `dateCreation` de la page détail (celui des cartes est tamponné au jour du crawl) | requête déjà faite |
| **PAP** | `p.item-date` « Publié le 3 août 2026 » sur la page détail, lue par la session de la recherche (un client sans elle reçoit 403) | +1 requête / annonce |
| **Century21, Laforêt, Citya** | aucune date publiée | — |

Les insertions étant `INSERT OR IGNORE`, `SqliteRepository._backfill_site_dates` met à jour les
lignes déjà stockées en `first_seen` dès qu'une source commence à publier une date — sans jamais
écraser une date `SITE` existante (le classement par ancienneté ne doit pas bouger à chaque crawl).

### Garde-fou département

Plusieurs sites répondent à une commune inconnue (ou sans stock) par du **remplissage national** :
Citya complète une page ville avec ses carrousels inter-villes, Foncia bascule sur tout son stock,
Orpi remplit la page d'une commune sans stock avec des annonces d'ailleurs (Limoges sur le filtre
« Autour d'Annecy » : 45 annonces dont 38 hors zone, ramenées à 31 en 50 s au lieu de 61 s,
mesuré le 2026-10-28). Orpi n'a pas de page du tout pour certaines communes (404 sur
`location-immobiliere-epagny-metz-tessy`) : le slug est juste, et la recherche `/recherche/*` est
interdite par son `robots.txt`, donc ces communes ne sont couvertes que par les autres sources.
`is_in_department(listing, dept)` (dans `base_crawler.py`) les écarte dès le parsing sur le code
postal ; une annonce sans code postal est conservée, et le contrôle de rayon du matcher la juge
sur sa propre commune.

### Commune de la carte, jamais la commune cherchée

Une annonce porte la commune que **sa carte** nomme. La commune cherchée ne sert qu'à construire
l'URL : aucune source ne garantit que sa page ne montre qu'elle. ParuVendu redirigeait une
commune **sans annonce** vers la page du **département entier** (`haute-savoie-74`, constaté le
2026-11-01 ; la redirection n'est plus suivie, voir « ParuVendu : une commune vide » plus bas), et Foncia complète la page d'une petite commune avec
ses voisines (la page Veyrier-du-Lac n'avait aucune annonce de Veyrier). Estampiller la commune
cherchée rangeait un T2 de Gaillard sous « Veyrier-du-Lac », sur la carte comme dans le rayon.

- ParuVendu : dernière ligne du titre, `h3 a span` → « Gaillard (74) » ;
- Foncia : `p.foncia-card-place` → « Sevrier (74320) » ;
- Citya : premier paragraphe du lien, même forme ;
- Orpi, PAP, Century 21, Laforêt : leur propre champ de localisation, sans repli.

Les trois premières passent par `parse_commune_label`. Une carte sans commune lève
`MissingCommuneError` : écartée et journalisée, jamais devinée. Les lignes déjà stockées sous la
commune cherchée sont corrigées au crawl suivant (`_update_price_and_place`). Couvert par
`tests/infrastructure/test_commune_on_card.py`.

### Détection meublé

`detect_furnished(text)` (dans `domain/services/furnishing.py`) déduit meublé/non-meublé du texte de l'annonce
(« meublé » vs « non meublé / vide », négation prioritaire). Câblé dans chaque crawler ; le
`ListingMatcher` fait aussi cette déduction en secours, pour qu'un filtre « non meublé » exclue
réellement les meublés. Deux variantes plus strictes pour une page détail entière :
`detect_furnished_label` (forme étiquetée « Meublé : non » seule) et `detect_furnished_chip`
(puce de critère dont le texte entier est le mot — voir ci-dessus).

---

## Concurrence

Les crawlers tournent en parallèle via `asyncio.gather` avec un `Semaphore(5)` :

```
CrawlAllSources.execute()
    │
    ├── PapCrawler.fetch()        ──→ httpx async
    ├── OrpiCrawler.fetch()       ──→ curl_cffi
    ├── FonciaCrawler.fetch()     ──→ curl_cffi
    ├── ParuVenduCrawler.fetch()  ──→ curl_cffi
    ├── Century21Crawler.fetch()  ──→ curl_cffi
    ├── LaforetCrawler.fetch()    ──→ curl_cffi
    ├── CityaCrawler.fetch()      ──→ curl_cffi
    ├── SquareHabitatCrawler.fetch() ──→ curl_cffi
    └── await all → save_many()
```

`MAX_CONCURRENT_CRAWLERS=5` est configurable dans `.env` (semaphore).

### Couverture du rayon — `covers_radius`

Pour éviter de relancer chaque source commune par commune, le crawl dispatche deux filtres :

- **Sources `covers_radius = True`** (PAP, Century21, Laforêt, Square Habitat) : le site couvre
  déjà la zone (rayon natif PAP, communes voisines pour Century21 et Laforêt — dont la page ville
  liste aussi le stock des agences alentour —, département entier pour Square Habitat).
  Elles reçoivent le filtre **de base** → **une seule recherche** par ville cible.
- **Sources par ville exacte** (Orpi, Foncia, ParuVendu, Citya) : reçoivent le filtre **étendu** aux
  communes du rayon et itèrent dessus (elles n'ont pas de paramètre rayon). Ce filtre étendu
  vient de `SearchFilter.with_crawl_cities` : jusqu'à 30 communes (`_MAX_COMMUNES`), au-delà de
  `MAX_CITIES` (10), qui ne borne que les villes saisies. `dataclasses.replace` re-validerait et
  refuserait la liste (tout filtre de plus de 10 communes dans le rayon plantait au crawl).

#### ParuVendu : une commune vide coûte une redirection, pas une page département

ParuVendu reste **par ville exacte**. Mesuré le 2026-11-01 autour d'Annecy (20 km, 30 communes) :

- `/immobilier/recherche/location/appartement/{commune}-{cp}/` répond **200** avec les seules
  annonces de la commune quand elle en a (10 communes) ; l'ancien chemin
  `/immobilier/location/appartement/…` ne fait que rediriger (301) vers celui-ci, il est donc
  demandé directement ;
- une commune **sans annonce** (20 communes) répond **301 vers la page du département**. Suivre
  la redirection téléchargeait cette même page (~560 Ko) une fois par commune vide, et envoyait
  ses cartes hors rayon à l'enrichissement détail. `ParuVenduCrawler.FOLLOW_REDIRECTS = False` :
  `BaseCrawler._fetch_page` lit alors une redirection comme « pas de page » (journal debug) ;
- la page département ne remplace pas les communes : elle s'arrête à **5 pages** (`?p=6` → 404),
  150 annonces sur 206, et en ratait 11 sur les 40 du rayon (les plus anciennes). Pas de rayon
  natif utilisable : le formulaire poste sur `/immobilier/annoncefo/`, interdit par `robots.txt`.

Avant / après sur ce filtre : ~80 requêtes HTTP (301 compris) et ~14 Mo → 30 requêtes et 2,8 Mo ;
64 visites détail → 40 ; les 40 annonces du rayon restent. Une page par commune
(`MAX_PAGES = 1`, 30 cartes ; Annecy en avait 29) : un `?p=2` inexistant répond un 404 de taille
pleine. Couvert par `tests/infrastructure/test_paruvendu_empty_commune.py`.

Le `ListingMatcher` filtre ensuite tout au rayon exact, donc la couverture reste identique.

Chaque source est en outre plafonnée par `SOURCE_TIMEOUT_SECONDS` (180 s, `asyncio.wait_for`) :
une source qui traîne est sautée (résultat vide) plutôt que de bloquer le crawl. Côté web, le
crawl tourne en **tâche de fond** (`/api/search` répond aussitôt), donc aucune requête HTTP ne
peut expirer.

### Parallélisme interne à une source

Les sources par-ville ne bouclent plus les communes en série :

- `BaseCrawler._gather_cities` lance les recherches par commune en parallèle, borné par
  `CITY_CONCURRENCY` (4), et déduplique par id.
- L'enrichissement page détail (`_enrich_details`) visite les pages en parallèle, borné par
  `ENERGY_CONCURRENCY` (5), au lieu d'une à la fois ; les URLs en cache 24h ne refont aucune requête.
- L'enrichissement est fait **une seule fois** dans `fetch()` après avoir rassemblé toutes les
  communes — ainsi concurrence-communes et concurrence-enrichissement ne se multiplient pas
  (au pire `CITY_CONCURRENCY` puis `ENERGY_CONCURRENCY` en phases séparées).

Gain mesuré : Orpi sur 3 communes (11 annonces enrichies) ≈ 3 s contre ~25 s en séquentiel.

---

## Ajouter une source

### 1. Créer le crawler

```python
# src/apartment_hunter/infrastructure/crawlers/avendre_crawler.py
from datetime import datetime
from decimal import Decimal

from ...domain.entities import Listing, SearchFilter
from ...domain.value_objects import Location, Price
from .base_crawler import BaseCrawler, apartment_id, build_city_slug

class AvendreCrawler(BaseCrawler):
    source_name = "avendre-alouer"
    BASE_URL = "https://www.avendre-alouer.fr"

    async def fetch(self, f: SearchFilter) -> list[Listing]:
        # _gather_cities parallélise les communes et log les échecs par ville
        return await self._gather_cities(f.cities, lambda c: self._fetch_city(c, f))

    async def _fetch_city(self, city: str, f: SearchFilter) -> list[Listing]:
        base_url = f"{self.BASE_URL}/location/appartement/{build_city_slug(city)}"
        return await self._paginate(
            lambda page: base_url if page == 1 else f"{base_url}?page={page}",
            lambda html: self._parse_page(html, city),
            label=city,
        )

    def _parse(self, item: dict) -> Listing | None:
        try:
            url = item["url"]
            return Listing(
                id=apartment_id(url),
                url=url,
                title=item.get("title", "Appartement"),
                source=self.source_name,
                location=Location(city=item.get("city", "")),
                price=Price(amount=Decimal(str(item.get("price", 0)))),
                # Pas de date publiée par la source → repli premier-vu (défaut
                # `PublicationSource.FIRST_SEEN`). Si la source en publie une :
                # published_at=parse_french_date(item["date"]),
                # published_at_source=PublicationSource.SITE,
                published_at=datetime.now(),
            )
        except Exception as exc:
            self._log_parse_error(self.source_name, item.get("url", "?"), str(item), exc)
            return None
```

### 2. Exporter depuis `__init__.py`

```python
# infrastructure/crawlers/__init__.py
from .avendre_crawler import AvendreCrawler
```

### 3. Enregistrer dans le container

```python
# infrastructure/container.py
def build_crawlers(settings: Settings) -> list[CrawlerPort]:
    timeout = settings.request_timeout_seconds
    return [
        PapCrawler(timeout=timeout),
        OrpiCrawler(timeout=timeout),
        FonciaCrawler(timeout=timeout),
        ParuVenduCrawler(timeout=timeout),
        Century21Crawler(timeout=timeout),
        LaforetCrawler(timeout=timeout),
        CityaCrawler(timeout=timeout),
        SquareHabitatCrawler(timeout=timeout),
        AvendreCrawler(timeout=timeout),   # ← ajouter ici
    ]
```

### 4. Écrire le fake de test

```python
# tests/fakes/in_memory_crawler.py
# Déjà générique — aucun changement nécessaire
```

Le `InMemoryCrawler` existant est réutilisable pour toutes les sources.

---
