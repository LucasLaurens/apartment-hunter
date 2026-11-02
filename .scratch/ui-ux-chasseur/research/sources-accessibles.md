# Sources accessibles autour d'Annecy (74)

Réponse au ticket [02 — Quelles sources sont accessibles autour d'Annecy ?](../issues/02-sources-accessibles.md).

Relevé du **2026-10-28**. Chaque site a reçu une poignée de requêtes (2 à 6), espacées de 2,5 s,
avec l'outillage du projet : `curl_cffi` empreinte `chrome124` (comme `BaseCrawler._fetch_with_cffi`)
et, pour deux SPA, Chromium headless lancé comme `PlaywrightCrawler`. Aucun compte, aucun identifiant,
aucun CAPTCHA tenté : un défi rencontré arrête l'évaluation du site.

Le `robots.txt` de chaque site a été lu **avant** toute autre requête ; sa règle applicable est citée
dans la fiche. Les volumes sont des instantanés du jour, pas des moyennes.

## Verdicts

Retenues d'abord, par intérêt décroissant.

| Source | Verdict | Format | Champs clés | Volume observé | Raison |
|---|---|---|---|---|---|
| **Bien'ici** | retenue | API JSON publique (`/realEstateAds.json`) | prix, charges, surface, pièces, étage, DPE, GES, date, meublé, type d'annonceur | 83 appartements, commune d'Annecy ; 309 en Haute-Savoie | Aucun login ni défi ; le chemin JSON n'est pas couvert par `robots.txt` |
| **Square Habitat** | retenue | SSR Angular, JSON `ng-state` | prix CC, surface, pièces, ville, CP, GPS, date de création ; détail : DPE, GES, étage, meublé, charges | 16 (page Annecy, avec Seynod, Pringy, Meythet, Annecy-le-Vieux) | Agence Crédit Agricole des Savoie, stock local réel ; route autorisée |
| **EntreParticuliers** | retenue | SSR HTML + `ItemList` JSON-LD | carte : prix, pièces, surface, ville ; détail : DPE, GES, `datePosted` | 14 par page en 74 (2 pages), dont 6 à Annecy en page 1 | Particuliers, complément de PAP ; `Allow: /` pour `*` |
| **ERA** | retenue, priorité basse | SSR Angular (cartes rendues serveur) | carte : prix, pièces, chambres, surface, ville ; détail : charges, étage, DPE et GES (kWh), meublé | 1 à Annecy, 7 en Haute-Savoie | Plus une SPA : le rendu serveur suffit, pas besoin de Playwright ; stock minime |
| **Capifrance** | retenue, priorité basse | SSR HTML, page département | carte : prix CC, ville, CP, titre (pièces, surface) ; détail : charges, DPE en SVG inline | 8 en Haute-Savoie (Talloires, Cran-Gevrier, Saint-Martin-Bellevue près d'Annecy) | Mandataires, route sans paramètre autorisée ; stock minime |
| **iad** | retenue, priorité basse | SSR Nuxt, page département | carte : prix CC, pièces, surface, ville ; détail non vérifié | 5 en Haute-Savoie (1 à Annecy, 1 à Faverges) | Route autorisée ; page complétée par des annonces hors département |
| **Nestenn** | retenue, priorité basse | SSR HTML | carte : prix CC, surface, pièces, chambres, distance ; DPE en image (chemin interdit) | 7 sur la page Annecy, dont 2 ou 3 dans le rayon | Route autorisée ; page complétée par la Savoie (Bassens, Pont-de-Beauvoisin) |
| **Leboncoin** | rejetée | SSR Next, JSON `__NEXT_DATA__` | tous les champs (prix, charges, surface, pièces, étage, DPE, GES, date, meublé, particulier/pro) | 328 locations en 74000 (première page) | Défi DataDome dès la **deuxième** requête ; à ne pas contourner |
| **Jinka** | rejetée | app Next, annonces derrière connexion | — | — | Aucune route publique d'annonces : tout passe par `/sign/in`, `/api/` est interdit |
| **Logic-Immo** | rejetée | SPA Aviv | — | — | Défi DataDome (403) sur la page SEO ville ; même stock que SeLoger (groupe Aviv) |
| **Avendrealouer** | rejetée | — | — | — | DataDome renvoie un CAPTCHA dès `robots.txt` |
| **Stéphane Plaza** | rejetée | SPA Vue, JSON `/search-goods` | prix, surface, pièces, description | 0 appartement en Haute-Savoie | Faisable avec Playwright, mais aucun stock dans le 74 ; l'API appelée hors navigateur est bloquée par Cloudflare |
| **Guy Hoquet** | rejetée | page jQuery, résultats en XHR | — | 0 à Annecy (« Aucun résultat… ») | Pas de stock ; l'endpoint de résultats `/biens/search-properties` est interdit par `robots.txt` |
| **Nexity** | rejetée | — | — | — | Aucune annonce de location publiée : l'URL location d'Annecy redirige vers l'accueil, le sitemap ne liste que des biens à vendre |
| **Ouest-France Immo** | rejetée | — | — | — | `robots.txt` : `Disallow: /louer/` |
| **Oralia** | rejetée | SSR | — | 0 | Aucun département 74 dans la liste des biens à louer (Ain, Isère, Loire, Rhône seulement) |
| **Cimm Immobilier** | rejetée | SSR | — | 0 dans le rayon d'Annecy | Stock 74 dans la vallée de l'Arve (Sallanches, Passy, Magland) ; la recherche ignore le filtre de ville |

Non revues, comme le demandait le ticket (aucun fait nouveau rencontré) : L'Adresse, SuperImmo,
immoregion.fr, Arthur Immo, immojeune, acheter-louer, vivastreet, fnaim, notaires.

## Fiches des sources retenues

### Bien'ici — la plus grosse prise

- **`robots.txt`** ([bienici.com/robots.txt](https://www.bienici.com/robots.txt), [res.bienici.com/robots.txt](https://res.bienici.com/robots.txt)) :
  interdit `/recherche/*&*`, `/recherche/*,*`, `/annonces-*`, `/*?mode=*`, `/*tri=*`. Ni
  `/realEstateAds.json` ni `res.bienici.com/suggest.json` ne sont couverts.
- **Sans connexion** : oui. L'ancienne note « login / cookie de session » (`docs/functional/sources.md`)
  ne tient plus : deux requêtes sans cookie ont répondu 200 en JSON.
- **Route** :
  1. Zone : `GET https://res.bienici.com/suggest.json?q=annecy` → `zoneIds: ["-6791758"]` (commune
     nouvelle, CP 74000/74370/74600/74940/74960).
  2. Annonces : `GET https://www.bienici.com/realEstateAds.json?filters=<JSON url-encodé>` avec
     `{"size":24,"from":0,"filterType":"rent","propertyType":["flat"],"page":1,"sortBy":"publicationDate","sortOrder":"desc","onTheMarket":[true],"zoneIdsByTypes":{"zoneIds":["-6791758"]}}`.
     Réponse : `total`, `perPage`, `realEstateAds[]`. Pagination par `from`.
  - Une zone département marche aussi : `-7407` (Haute-Savoie) → `total: 309`, et les 24 annonces de la première page sont toutes dans le 74.
    Une requête département plus le `ListingMatcher` couvre donc le rayon (`covers_radius`).
- **Champs par annonce** (tous dans la liste, aucune page détail à visiter) : `price` (CC),
  `charges`, `rentWithoutCharges`, `surfaceArea`, `roomsQuantity`, `floor`, `floorQuantity`,
  `energyClassification`, `energyValue`, `greenhouseGazClassification`, `greenhouseGazValue`,
  `publicationDate`, `modificationDate`, `isFurnished`, `city`, `postalCode`, `accountType`
  (`agency` / `mandatary` / `network`), `id`, `reference`, `photos`, `description`.
- **Remplissage observé** (24 annonces) : DPE 24/24, charges 23/24, étage 21/24.
- **Recouvrement** : Bien'ici agrège les flux d'agences (un id `laforet-immo-facile-…` vu dans la
  liste). Doublons attendus avec Laforêt, Century21 ou Orpi : c'est le travail de `duplicates.py`,
  qui regroupe sans jamais supprimer. Les agences sans crawler dédié restent un vrai gain.
- **Non vérifié** : les CGU de Bien'ici sur l'accès automatisé (le ticket fixe la limite à
  `robots.txt`, CAPTCHA et compte, qui sont tous respectés).

### Square Habitat

- **`robots.txt`** ([lien](https://www.squarehabitat.fr/robots.txt)) : interdit `/resultat-location`,
  `/sh-*/louer-appartement-*.aspx` et `*/immo/*`. La route SEO `/annonces/location/bien/…` ne tombe
  dans aucune règle (`/immobilier/` n'est pas `/immo/`).
- **Route** (trouvée dans `sitemap-location-appartement-localisation.xml`) :
  `https://www.squarehabitat.fr/annonces/location/bien/appartement/immobilier/auvergne-rhone-alpes/haute-savoie/annecy-74000`.
  Il existe aussi des pages pour `annecy-74370`, `-74600`, `-74940` et `-74960`.
- **Format** : Angular rendu serveur. Les annonces sont dans `<script id="ng-state">` (JSON) :
  `codeRef`, `typeBien`, `ville`, `codePostal`, `nbPieces`, `nbChambres`, `surfaceHabitable`,
  `prix` (charges comprises), `latitude`, `longitude`, `dateCreation`, `texteAnnonce`. La page
  détail
  (`/square-habitat-des-savoie/annonces/biens/location/appartement/{ville}/{uuid}`) ajoute
  `dpeInfos` (`dpeLettre`, `gesLettre` et leurs valeurs), `etage`, `meuble`, le montant des charges
  et `dateDisponibilite`.
- **Volume** : 16, dont `offerCount: 16` dans le JSON-LD de la page. La page Annecy inclut Seynod,
  Pringy, Meythet et Annecy-le-Vieux.

### EntreParticuliers

- **`robots.txt`** ([lien](https://www.entreparticuliers.com/robots.txt)) : `Allow: /` pour `*`.
  Il interdit nommément des robots d'IA (`ClaudeBot`, `GPTBot`, `anthropic-ai`…), avec
  `Content-Signal: ai-train=no`. Le crawler du projet n'en fait pas partie (UA navigateur, usage
  personnel de recherche), mais le choix reste à faire en connaissance de cause.
- **Route** : `https://www.entreparticuliers.com/annonces-immobilieres/location/appartement/haute-savoie-74`,
  paginée en `?page=2`. Le niveau département suffit (14 annonces par page) ; le matcher réduit au rayon.
- **Format** : SSR HTML, plus un JSON-LD `ItemList` (`numberOfItems`, URLs). Une carte donne le prix
  (« 1 081 € /mois »), la ville et le département, les pièces et la surface. L'URL suit le modèle
  `/annonces-immobilieres/appartement/location/annecy-74000/appartement-3-pieces-65-m2/ref-22727835`.
  La page détail ajoute DPE et GES (« Classe D · 181 à 250 kWh/m²·an ») et `datePosted` (ISO).
  Le meublé et les charges n'ont pas été vus sur l'annonce testée.
- **Piège** : la même liste mélange des **demandes** de locataires
  (`/annonces-demandes-immobilieres/…`) ; ne garder que `/annonces-immobilieres/…/ref-…`.
- Le marqueur `challenge-platform` présent dans la page est le script de télémétrie Cloudflare, pas
  un défi : le contenu est servi en 200.

### ERA (priorité basse)

- **`robots.txt`** ([lien](https://www.eraimmobilier.com/robots.txt)) : interdit `/louer` et
  `/acheter`. Les pages « silo » `/location-appartement/…` ne le sont pas, et figurent dans
  `sitemap_silo_location_appartement.xml`.
- **Route** : `/location-appartement/auvergne-rhone-alpes-16/haute-savoie-79/annecy-29029` (ids
  internes, à lire dans le sitemap) ou le niveau département `…/haute-savoie-79`.
- **Format** : Angular **rendu serveur** (`ng-server-context`) : les cartes sont dans le HTML, il
  n'y a plus besoin de Playwright. Le rejet d'août 2026 (« Angular SPA ») ne tient plus. Détail
  `/annonces/{id}` : charges, `etage`, DPE et GES en kWh, meublé dans le texte.
- **Volume** : 1 à Annecy, un studio de 10 m² ; 7 dans le 74.

### Capifrance, iad, Nestenn (priorité basse)

Toutes trois sont en SSR, et leur `robots.txt` n'interdit que des paramètres de requête. En revanche,
chacune ne compte que 1 à 3 annonces dans le rayon d'Annecy.

- **Capifrance** : `https://www.capifrance.fr/fr/immobilier/location/appartement/haute-savoie`
  (8 annonces, sans pagination). `robots.txt` interdit `?page=`, `?city=`, `?place=` et d'autres
  paramètres : rester sur la route sans paramètre. Le DPE est un SVG inline sur la page détail, à
  lire à la façon de Citya.
- **iad** : `https://www.iadfrance.fr/annonces/haute-savoie-74/location/appartement`, vue dans
  `sitemap/fr/propertylisting/department.xml`. `robots.txt` interdit `/liste/annonces*`, `?location=`
  et `/*&*`. La page affiche 5 annonces du 74, puis des annonces d'autres départements (Grenoble,
  Bassens) : appliquer le garde-fou `is_in_department`.
- **Nestenn** : `https://nestenn.com/location/appartement/annecy-74000` (7 annonces). `robots.txt`
  interdit `/listing*`, `/?action=listing*` et `/public/img/dpe/*` : le DPE, rendu en image, est hors
  limites, comme chez Laforêt. Les cartes affichent « À 1.9 km de 74000 Annecy » et sont complétées
  par des annonces de Savoie et du Chablais : là encore, `is_in_department` et le matcher font le tri.

## Fiches des sources rejetées (preuves)

- **Leboncoin**. **Fait nouveau** : `https://www.leboncoin.fr/cl/locations/cp_annecy_74000` a
  répondu 200 avec `__NEXT_DATA__` complet (`total: 328`, 40 annonces avec `first_publication_date`,
  `price`, `monthly_charges`, `square`, `rooms`, `floor_number`, `energy_rate`, `ges`, `furnished`
  et `owner.type`). Le `robots.txt` n'a pas de groupe `*` et `/cl/` n'est interdit dans aucun groupe
  nommé (seul `/recherche` l'est). Mais la requête suivante,
  `/cl/locations/cp_annecy_74000/real_estate_type:2`, 2,5 s plus tard, a reçu un **défi DataDome**
  (403, `captcha-delivery.com`). La source est rejetée : la tenir supposerait de contourner un défi.
- **Jinka** : le sitemap ([pages.xml](https://www.jinka.fr/sitemaps/pages.xml)) ne liste que des pages
  éditoriales. L'accueil ne mène aux annonces que par `/sign/in` ; `robots.txt` interdit `/api/`,
  `/alerts` et `/alert_result`.
- **Logic-Immo** : les pages SEO `/recherche-immo/location/appartement/…/annecy-74000/ad08fr37304`
  (vues dans le sitemap, non interdites) reçoivent un défi DataDome (403). `robots.txt` interdit
  `*/classified-search?*` et `/serp-bff/*`.
- **Avendrealouer** : `robots.txt` lui-même renvoie la page DataDome (403).
- **Stéphane Plaza** : `robots.txt` autorise tout (`Allow: /`). L'API `/search-goods` appelée
  directement reçoit le blocage Cloudflare « Sorry, you have been blocked ». Chargée par Chromium,
  `/louer/departement/haute-savoie_74/appartement/` interroge `/search-goods` et obtient
  `pagination.total: 0` : la source serait faisable via `_intercept_json_responses`, mais elle n'a
  rien à crawler dans le 74.
- **Guy Hoquet** : rendue par Chromium, `/location/annonces-annecy-74000` affiche « Aucun résultat… ».
  `robots.txt` interdit `/biens/search-properties`, `/transaction-location` et `/villes/search`.
- **Nexity** : `/annonces-immobilieres/location/appartement/annecy-74000` et `…/annecy-74` redirigent
  vers l'accueil (une fois en 502) ; [sitemap.xml](https://www.nexity.fr/sitemap.xml) ne contient
  que `bien-vente`, `achat-vente-neuf`, `achat-vente-tout` et des fiches d'agences de location.
- **Ouest-France Immo** : `robots.txt` interdit `/louer/`.
- **Oralia** : `/location/nos-biens-a-louer` ne liste, pour Auvergne-Rhône-Alpes, que l'Ain,
  l'Isère, la Loire et le Rhône.
- **Cimm Immobilier** : `robots.txt` autorise tout. Les biens du 74 vus dans
  [sitemap.xml](https://cimm.com/sitemap.xml) sont à Sallanches, Passy, Magland, Domancy et
  Araches, à plus de 45 km d'Annecy. `search?…&location=Annecy&citycode=74010` renvoie la même liste
  nationale (Grenoble) : la ville n'est pas filtrable par l'URL.

## Ce que cela change dans la doc

Il n'y a rien à modifier dans ce ticket. Deux phrases de `docs/functional/sources.md` § Sources
retirées sont devenues fausses et devront changer dans les tickets de collecte :

- « **Jinka**, **Bien'ici** — Nécessitent login / cookie de session » : vrai pour Jinka, faux pour
  Bien'ici.
- « **Square Habitat**, …, **ERA Immobilier**, **Stéphane Plaza**, **Nestenn** — SPA … pas de cartes
  HTML scrapables » : Square Habitat et ERA rendent maintenant leurs cartes côté serveur, et Nestenn
  a une route ville SSR. Stéphane Plaza reste à écarter, mais pour une autre raison : aucun stock
  dans le 74.

## Ordre suggéré pour les tickets `task`

1. Bien'ici (`feat/crawler-bienici`) : httpx ou curl_cffi en JSON, une requête département,
   tous les champs sur la liste.
2. Square Habitat (`feat/crawler-squarehabitat`) : `ng-state` sur la liste, page détail pour
   DPE, GES, étage et meublé.
3. EntreParticuliers (`feat/crawler-entreparticuliers`) : page département et pagination, page
   détail pour DPE, GES et date.
4. Lot à faible volume, à réunir dans un seul ticket si l'utilisateur le juge utile : ERA,
   Capifrance, iad, Nestenn.
