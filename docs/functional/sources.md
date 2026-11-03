# Sources de données

14 sites scrapés, dont six (Bien'ici, Locservice, FNAIM, 2A Immobilier, SBM Immobilier, Agence BFM)
seulement quand les règles des sites sont ignorées. Données disponibles et limites pour chacun.

> **Règle du projet :** seules les plateformes exposant **publiquement** toute l'info nécessaire,
> **sans login ni cookie de session**, et **filtrant par ville**, sont utilisées. Une source
> qui refuse un client honnête (anti-bot, captcha), ou qui ne filtre pas par ville, est **retirée**
> plutôt que contournée ou laissée en échec. Aucun contournement : ni imitation de navigateur
> (empreinte TLS, en-têtes), ni rotation de User-Agent, ni solveur de captcha, ni compte.
> Le `robots.txt` est appliqué, et un site dont les conditions d'utilisation interdisent
> l'extraction de ses annonces n'est pas crawlé.

---

## Règles des sites : respectées, ou ignorées sur votre choix

Par défaut, les règles ci-dessus s'appliquent. Le réglage **Règles des sites** (page
Paramètres, ou `hunt rules ignore`) les met de côté à vos risques
([ADR-0012](../decisions/0012-le-chasseur-peut-ignorer-les-regles-des-sites.md)) :
`robots.txt` n'est plus lu (recherche et rayon de PAP, pagination de Foncia), et les
sources refusées pour leurs seules conditions d'utilisation entrent dans le crawl. Il
ne change rien aux protections anti-bot : un site qui bloque un client honnête
(Cloudflare, DataDome, captcha) reste bloqué, et aucun compte n'est créé.

## État des sources

| Source | Type | Méthode | DPE / GES | Date de parution | Rayon |
|--------|------|---------|-----------|------------------|-------|
| **PAP** | Direct proprio | httpx + BS4 | DPE (liste) | ✅ détail (même session que la recherche) | 1 requête (rayon natif) |
| **Century21** | Réseau agences | curl_cffi + SSR HTML | DPE + GES (détail) | ❌ non publiée | 1 requête (communes voisines retournées) |
| **Orpi** | Réseau agences | curl_cffi + SSR HTML | DPE + GES (détail) | ✅ détail | par commune |
| **Foncia** | Gestionnaire | curl_cffi + SSR HTML | DPE + GES (carte) | ✅ liste | par commune |
| **ParuVendu** | Généraliste | curl_cffi + SSR HTML | DPE (carte) + GES (déduit des kg CO₂) | ✅ liste | par commune |
| **Laforêt** | Réseau agences | curl_cffi + SSR HTML | — (image) | ❌ non publiée | 1 requête (agences alentour incluses) |
| **Citya** | Gestionnaire | curl_cffi + SSR HTML | DPE + GES (détail, SVG) | ❌ non publiée | par commune |
| **Square Habitat** | Réseau agences | curl_cffi + JSON `ng-state` | DPE + GES (détail) | ✅ liste | 1 requête (par département) |
| **Bien'ici** — règles des sites ignorées seulement | Portail | curl_cffi + API JSON publique | DPE + GES (liste) | ✅ liste | 1 requête (carré autour de la ville) |
| **Locservice** (règles des sites ignorées seulement) | Direct proprio | curl_cffi + SSR HTML | DPE + GES (détail) | ❌ non publiée | 1 requête (communes voisines, ~20 km) |
| **FNAIM** — règles des sites ignorées seulement | Fédération d'agences | curl_cffi + SSR HTML | DPE + GES (détail) | ❌ non publiée | par commune |
| **2A Immobilier** — règles des sites ignorées seulement | Agence locale | curl_cffi + SSR HTML | DPE (détail), pas de GES | ❌ non publiée | stock entier (8 pages) |
| **SBM Immobilier** — règles des sites ignorées seulement | Agence locale | curl_cffi + SSR HTML + JSON-LD | DPE + GES (détail) | ✅ liste (« Ajout : … ») | stock entier (4 pages) |
| **Agence BFM** — règles des sites ignorées seulement | Agence locale | curl_cffi + état JSON Netty | DPE + GES (détail) | ✅ liste (mise en ligne) | stock entier (1 page) |

PAP/Century21/Laforêt/Square Habitat/Bien'ici/Locservice/2A Immobilier/SBM Immobilier/Agence BFM couvrent la zone en **une recherche** (`covers_radius`) — Square Habitat par département, Bien'ici par un carré autour de la ville, Locservice par ses communes voisines (~20 km), 2A Immobilier, SBM Immobilier et Agence BFM par leur stock entier, les autres par ville/rayon ; Orpi/Foncia/ParuVendu/Citya/FNAIM itèrent les communes. Le matcher filtre ensuite au rayon exact.

### Date de parution

Chaque ligne affiche la date que la source annonce. Quand la source n'en publie aucune (Century21,
Laforêt, Citya, 2A Immobilier), la date affichée est celle du **premier crawl** où l'annonce est apparue, préfixée
« vu » (italique atténué en CLI, infobulle explicite sur le web) — c'est une borne haute : l'annonce
n'est jamais plus récente que ça. Détail technique et provenance par source :
[Crawlers — date de parution](../technical/crawlers.md#date-de-parution).

Nuance ParuVendu : la seule date publiée est libellée « dernière mise à jour » — c'est celle qui
pilote son propre tri par fraîcheur, elle tient donc lieu de date de parution.

### Anti-bot et fiabilité

Chaque requête se présente sous le même nom, `CRAWLER_USER_AGENT` (« apartment-hunter/0.1 »),
sans imiter de navigateur. `BaseCrawler._fetch_page` ré-essaie les codes **transitoires** (408,
429, 5xx dont 534) **3× avec backoff**. Un 401/403 est un **refus** : pas de nouvel essai, un log
clair `blocked — HTTP 403` est émis et la page est sautée pour ce run (pas de plantage). Une
source qui refuse durablement est retirée.

---

## DPE et GES

Le DPE (énergie) et le GES (émissions) sont affichés par annonce, sur deux échelles A→G.

- **Foncia** : les deux figures sont sur la carte de résultat (consommation kWh + émissions kgCO₂) → calculées sans requête supplémentaire.
- **ParuVendu** : lettre DPE sur la carte, GES déduit des kg CO₂ de la carte (la page détail est derrière un captcha depuis le 2026-10-28).
- **Orpi, Century21, Citya, FNAIM** : absentes des cartes → lues sur la **page détail** de chaque annonce (1 requête de plus par annonce, résultat mis en cache 24h, même requête que la date de parution).
- **PAP** : DPE sur la liste, GES généralement absent.
- **2A Immobilier** : DPE sur la page détail. Le GES n'est jamais lu : l'agence ne le renseigne pas et le site affiche alors « A » par défaut.
- **Laforêt** : rend son DPE en image (`/ajax/properties/{id}/dpe`) → non lu, DPE/GES restent inconnus (le matcher laisse alors passer l'annonce).

Conversion : les valeurs chiffrées (kWh/m².an et kgCO₂/m².an) sont mappées vers les lettres A→G via les seuils officiels français ; le DPE final est le pire des deux. Réutilise `DpeRating` pour les deux métriques.

**Piège récurrent** : ces pages dessinent l'échelle complète A→G à côté de la note réelle, avec les mêmes classes CSS. Une recherche sur le HTML entier renvoie donc systématiquement « A », en silence — et le filtre DPE laisse alors passer toute la source. Il faut viser le bloc qui porte la note (voir `docs/technical/crawlers.md`).

---

## Étage

Presque aucune source ne met l'étage sur ses cartes de résultat. Il est lu sur la **page détail**, soit en label structuré (« Etage : 2 » chez ParuVendu), soit dans la prose de la description (« au 4e étage sur 5 » chez Laforêt).

| Source | Étage |
|--------|-------|
| **Orpi** | label de la liste de caractéristiques |
| **ParuVendu** | page détail (label + prose), souvent bloquée par un captcha → étage inconnu |
| **Laforêt** | page détail, uniquement dans la description |
| **2A Immobilier** | page détail, ligne « Etage » (« N.C. » → inconnu) |
| **SBM Immobilier** | page détail, fiche JSON-LD (« Etage ») |
| **Agence BFM** | liste, champ `floor` de l'état JSON (0 = non renseigné → inconnu) |
| **Foncia, Century21, PAP, Citya** | non publié → étage inconnu |

Tant que l'étage reste inconnu, `exclude_ground_floor`, `exclude_first_floor` et `top_floor_only` n'écartent rien sur cette source (règle « données manquantes » ci-dessous) — sauf si le texte dit explicitement « RDC » / « rez-de-chaussée ».

---

## Détail par source

### PAP — Particulier à Particulier
**pap.fr** · httpx + BeautifulSoup. Locations entre particuliers (aucune agence).
Données : prix, surface, pièces, localisation, DPE, meublé (déduit du texte). Rate limit 2s. ⚠️ Son `robots.txt` interdit toute URL à paramètres (`Disallow: /*?*`) : la recherche de commune, le rayon et la pagination dont dépend ce crawler sont refusés depuis que le `robots.txt` est appliqué (2026-10-31), PAP ne ramène donc plus rien.

### Orpi
**orpi.com** · curl_cffi + SSR. Réseau national d'agences. Données : prix, surface, pièces, ville, DPE + GES (détail).
Pas de page pour toutes les communes (Epagny Metz-Tessy renvoie 404) : celles-là ne passent que par les autres sources. Les annonces d'un autre département, servies en remplissage, sont écartées.

### Foncia
**fr.foncia.com** · curl_cffi + SSR. Code postal résolu via geo.api.gouv.fr. Données : prix (CC), surface, pièces, DPE + GES (carte), meublé. Première page seulement : son `robots.txt` interdit les URL à paramètres (`?page=2`).

### ParuVendu
**paruvendu.fr** · curl_cffi + SSR. Code postal résolu via geo.api.gouv.fr. Une page par commune ; une commune sans annonce redirige vers la page du département, cette redirection n'est pas suivie (elle retéléchargeait la même page pour chaque commune vide). Données : prix (CC), surface, pièces, DPE + GES (carte), **étage** (détail, souvent bloqué par un captcha anti-aspiration), meublé.

### Century21
**century21.fr** · curl_cffi + SSR. Slug ville (sans code postal). Données : prix (CC), surface, pièces, ville/département, DPE + GES (détail, SVG), meublé.

### Laforêt
**laforet.com** · curl_cffi + SSR. URL `/ville/location-appartement-{ville}-{cp}` (code postal résolu via geo.api.gouv.fr). La page ville liste aussi le stock des **agences alentour** (Seynod, Rumilly, Thônes… depuis Annecy) → `covers_radius`, le matcher réduit au rayon. Les cartes n'ont aucune statistique en texte : tout est sur les attributs d'analytics du bouton favori (`data-gtm-item-price-param`, `-size-param`, `-rooms-nb-param`, `-city-param`, `-zipcode-param`), joints à l'URL par l'id d'annonce. Données : prix, surface, pièces, ville, code postal, **étage** (lu dans la description de la page détail — la seule raison de la visiter). Pas de DPE (rendu en image), pas de date.

### Citya
**citya.com** · curl_cffi + SSR. URL `/annonces/location/appartement/{ville}-{cp}`. Deux pièges : les villes à arrondissements résolvent vers l'un d'eux (Lyon → 69001), inconnu de Citya → repli automatique sur `{dept}000` ; et une ville sans stock est **remplie de carrousels inter-villes** (Lyon, Riom… sur une page Annecy) → écartés par le garde-fou département. Données : prix, surface, pièces, ville, code postal, DPE + GES (détail, nom de fichier des SVG Inkscape).

### Locservice
**locservice.fr** · curl_cffi + SSR. **Crawlé seulement quand les règles des sites sont ignorées** : ses mentions légales interdisent toute reproduction sans accord écrit ([ADR-0012](../decisions/0012-le-chasseur-peut-ignorer-les-regles-des-sites.md)). URL `/{département}-{code}/location-appartement-{commune}.html` puis `-p2.html`, `-p3.html` (département lu sur geo.api.gouv.fr, « Saint » écrit « st »). La page commune liste aussi les communes voisines jusqu'à ~20 km, Savoie comprise depuis Annecy → `covers_radius`. Annonces de particuliers ; les cartes « Logement partenaire » (annonces d'agence reprises d'ailleurs, « Professionnel » sur la page détail) sont écartées. Données : loyer **charges comprises** (dit par la page détail seulement), surface, pièces (T1–T6), commune, code postal, meublé, photo, extrait de description ; DPE + GES et étage sur la page détail. Pas de date. Contacter un propriétaire y est payant ; le crawler ne fait que lire l'annonce et son lien.
### FNAIM — règles des sites ignorées seulement
**fnaim.fr** · curl_cffi + SSR. Fédération d'agences indépendantes : elle apporte des agences locales qu'aucune autre source ne publie (2A Immobilier, Agence BFM, Entre 2 Lacs, Like My Home…). Ses mentions légales interdisent l'extraction et la réutilisation de sa base, et son `robots.txt` interdit les pages détail de location : la source ne tourne donc **que si vous avez choisi d'ignorer les règles des sites**. URL `/liste-annonces-immobilieres/18-location-appartement-{ville}-{cp}.htm`, une commune par page (49 annonces pour Annecy le 2026-11-01). Données : loyer mensuel (la carte ne dit ni CC ni HC → « charges ? »), surface, pièces, meublé (puce), ville, code postal, **agence** (annonceur), photos, DPE + GES et étage (détail). Pas de date de parution.
### SBM Immobilier — règles des sites ignorées seulement
**sbm-immo.com** · curl_cffi + SSR (WordPress) + JSON-LD. Une agence d'Annecy. Ses mentions légales interdisent de reproduire, copier ou stocker tout élément du site sans son accord écrit : la source n'entre dans le crawl que si vous avez choisi d'ignorer les règles des sites. Son `robots.txt` autorise tout. Le stock entier tient dans `/locations-immobilieres/` (12 biens par page, 4 pages le 2026-11-02, garages compris, écartés). Données : loyer **charges comprises** (la page détail le décompose en loyer + provision), type (T1, T2, studio → pièces), commune et code postal, position de la carte, surface, photo, **date d'ajout** ; DPE, GES, étage et meublé sur la page détail.

### Agence BFM — règles des sites ignorées seulement
**agencebfm-immo.com** · curl_cffi + état JSON (plateforme Netty). Une agence d'Annecy, déjà vue à travers la FNAIM ; ses annonces reprises des deux sources se regroupent en un logement. Ses mentions légales interdisent toute reproduction du site sans autorisation : la source n'entre dans le crawl que si vous avez choisi d'ignorer les règles des sites. Son `robots.txt` autorise tout (sauf les PDF) et demande 5 s entre deux requêtes. Le stock entier tient dans `/location` (9 biens le 2026-11-03, parkings et une maison compris, écartés). Données : loyer **et provision sur charges séparés** (sans provision, le site écrit « HC » → « charges ? »), surface, pièces, étage, commune, code postal, position, photos, description, **date de mise en ligne** ; DPE et GES sur la page détail (« Classe énergie D, Classe climat D »).

### 2A Immobilier — règles des sites ignorées seulement
**2a-immo.fr** · curl_cffi + SSR. Une seule agence, implantée à Annecy, Aix-les-Bains, Rumilly et Chambéry. Ses mentions légales interdisent toute reproduction et utilisation des données du site sans autorisation : la source n'entre dans le crawl que si vous avez choisi d'ignorer les règles des sites ([ADR-0012](../decisions/0012-le-chasseur-peut-ignorer-les-regles-des-sites.md)). Le stock de location entier tient dans une liste (`/location`, 8 pages le 2026-11-01, caves, parkings et locaux compris) lue d'un bloc ; seuls les appartements sont gardés, le matcher réduit au rayon. Données : loyer charges comprises, surface, pièces, commune (sans code postal), meublé (bandeau « Meublé » ; sans bandeau, inconnu), photo, DPE et étage (détail). Pas de GES fiable, pas de date. Le 2026-11-01 : 37 appartements, dont 31 à 20 km d'Annecy au plus (Annecy, Annecy-le-Vieux, Cran-Gevrier, Pringy, Villaz, Chavanod, Sevrier, Saint-Jorioz, Menthon, Thônes, Rumilly).

---

## Données manquantes : comportement

Si une annonce ne renseigne pas un champ (étage, DPE, meublé…), le critère correspondant est **ignoré** — l'annonce est incluse. Mieux vaut voir une annonce sans info que la manquer.

Exceptions :
- `min_photos > 0` + aucune photo → **exclue**.
- Filtre **non meublé** : une annonce annoncée meublée est **exclue**. Le meublé est lu sur la page détail (« Meublé : non/oui » du tableau de critères, lecture qui fait autorité) et, à défaut, sur le texte de la carte (mot-clé, négations « non meublé / vide » prioritaires). Foncia ne visitant aucune page détail, ses annonces ne comptent que sur le texte de la carte.

---

## Sources retirées (et pourquoi)

| Site | Raison |
|------|--------|
| **Jinka** | Annonces derrière connexion (`/sign/in`), `/api/` interdit par `robots.txt` |
| **Figaro Immo, EntreParticuliers** | Cloudflare répond 403 à un client qui se présente sous son nom ; ils ne passaient qu'en imitant l'empreinte TLS de Chrome, ce que les règles de collecte interdisent. Retirés le 2026-10-31 |
| **SeLoger** | DataDome + rendu JS : le crawler ne passait qu'en masquant l'automatisation (script « stealth »), ce que les règles de collecte interdisent. Retiré le 2026-10-30 |
| **LeBonCoin** | Captcha DataDome systématique — non contournable sans solveur captcha / proxies résidentiels |
| **Logic-Immo** | SPA : aucune URL ville (toutes en 404), dépend d'une API geoId + données en JSON intégré, pas de cartes HTML serveur |
| **Nexity, Ouest-France, Stéphane Plaza** | Aucune location publiée dans le 74, `Disallow: /louer/`, ou aucun stock en Haute-Savoie |
| **ERA, Capifrance, iad, Nestenn** | Rendus côté serveur et autorisés, mais 1 à 3 annonces chacun dans le rayon d'Annecy : pas pour l'instant (2026-10-30) |
| **L'Adresse** | `robots.txt` : `Disallow: /` — le site refuse explicitement le crawl |
| **Guy Hoquet, Avendrealouer, Superimmo, Bellesdemeures** | Captcha / DataDome / 404 |
| **Arthur Immo, Sergic, Immo de France** | Scrapables mais aucun stock en Haute-Savoie |

Réintégrés depuis : **Laforêt** (répond à un client honnête, vérifié le 2026-10-31) et **Citya** (le HTML serveur filtre bien par ville, à condition d'utiliser le slug
`{ville}-{cp}` du site — le repli national précédemment observé venait d'un code postal invalide).

Pour ajouter une source, voir [Crawlers — ajouter une source](../technical/crawlers.md#ajouter-une-source).
