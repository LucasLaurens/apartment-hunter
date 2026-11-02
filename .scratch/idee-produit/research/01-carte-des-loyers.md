# Recherche 01 : « Carte des loyers » comme loyer de référence au m²

**Question** : les « indicateurs de loyers d'annonce par commune » (ministère du
Logement / DHUP, portés par l'ANIL, publiés sur data.gouv.fr) peuvent-ils servir de
loyer de marché de référence au m² pour situer une annonce ?

**Date de la recherche** : 2026-09-25. Fichiers CSV téléchargés et inspectés localement
(non versionnés).

## Verdict

**Oui, utilisable**, avec trois réserves de lecture qui doivent se voir à l'écran :

1. c'est un **loyer prédit pour un bien type** (surface fixe), pas une médiane : on
   compare un ordre de grandeur, pas un prix ;
2. il est **charges comprises, non meublé** : une annonce meublée ou sans charges
   connues (`charges_unknown`) n'est pas comparable telle quelle ;
3. la fiabilité varie par commune (`TYPPRED`, `nbobs_com`, `R2_adj`, largeur de
   l'intervalle) et le producteur demande lui-même la prudence en dessous de seuils
   précis (voir § 2).

La clé est le **code INSEE** (`INSEE_C`). Le moyen le moins cher de l'obtenir est
d'ajouter `code` aux `fields` de l'appel `geo.api.gouv.fr` que le dépôt fait **déjà**
(`_fetch_dept_communes`) : zéro requête en plus. Les 4 communes cibles sont couvertes ;
Annecy est sous le code de la commune nouvelle **74010**.

---

## 1. Format, millésime, fréquence, licence, URL

| Point | Constat | Source |
|---|---|---|
| Dernier millésime | **2025**, publié le 2025-12-11 (loyers au T3 2025, annonces 2019-2025). Aucun millésime 2026 publié à la date de la recherche. | [S1], [S2] p. 1 |
| Fréquence | Annuelle, publiée en décembre (2020, 2022, 2023, 2024, 2025) ; « continuera à être actualisée annuellement ». Le champ data.gouv `frequency` vaut pourtant `punctual` : chaque millésime est un **jeu de données distinct**. | [S2] p. 2, [S1] |
| Licence | `lov2` = Licence Ouverte v2.0, **avec mention obligatoire** : « Estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin ». | [S1], [S2] p. 2 |
| Format | 4 CSV (un par segment) + guide + note méthodologique PDF. | [S1] |
| Encodage CSV | **Windows-1252** (pas UTF-8 : octets `0x8C`/`0x9C` = Œ/œ), séparateur `;`, champs texte entre guillemets, **virgule décimale**, fins de ligne CRLF. ~4,7 Mo par fichier, 34 900 lignes. | inspection locale |
| Couverture | France entière hors Mayotte, géographie communale au 1er janvier 2025. 34 900 lignes = communes, Paris/Lyon/Marseille remplacées par leurs 45 arrondissements (75056, 69123, 13055 absents). Un code INSEE = une ligne (aucun doublon). | [S2] p. 1, [S3] p. 13 note 4, inspection |

### Fichiers du millésime 2025

| Segment | Fichier | Lien stable (redirection data.gouv) |
|---|---|---|
| Appartement, toutes typologies | `pred-app-mef-dhup.csv` | `https://www.data.gouv.fr/fr/datasets/r/55b34088-0964-415f-9df7-d87dd98a09be` |
| Appartement 1-2 pièces | `pred-app12-mef-dhup.csv` | `https://www.data.gouv.fr/fr/datasets/r/14a1fe11-b2d1-49b3-9f6b-83d12df9482c` |
| Appartement 3 pièces et plus | `pred-app3-mef-dhup.csv` | `https://www.data.gouv.fr/fr/datasets/r/5e3b28a4-cf56-43a3-ae79-43cceeb27f8c` |
| Maison | `pred-mai-mef-dhup.csv` | `https://www.data.gouv.fr/fr/datasets/r/129f764d-b613-44e4-952c-5ff50a8c9b73` |

`/fr/datasets/r/{id}` répond 301 vers `/api/1/datasets/r/{id}` puis vers le fichier
`static.data.gouv.fr` horodaté. L'URL est stable **pour un millésime** ; le millésime
suivant sera un nouveau dataset avec de nouveaux identifiants de ressource. Pour le
découvrir : `GET https://www.data.gouv.fr/api/1/datasets/?q=carte des loyers` et
retenir le titre « … par commune en {année} » le plus récent.

Le schéma est **identique** entre 2024 et 2025 (même en-tête, mêmes noms de fichiers),
vérifié sur `pred-app12-mef-dhup.csv` 2024.

## 2. Granularité et colonnes

Segments : appartement (tous), **T1-T2**, **T3 et plus**, maison : un fichier chacun.
Loyer **charges comprises**, logements **non meublés**, annonces mises en ligne au
**T3 2025** [S2] p. 1-3.

En-tête réel (identique dans les 4 fichiers) :

```
"id_zone";"INSEE_C";"LIBGEO";"EPCI";"DEP";"REG";"loypredm2";"lwr.IPm2";"upr.IPm2";"TYPPRED";"nbobs_com";"nbobs_mail";"R2_adj"
```

| Colonne | Sens (dictionnaire officiel [S2] p. 3) |
|---|---|
| `id_zone` | Identifiant de la maille utilisée pour l'estimation |
| `INSEE_C` | Code INSEE de la commune, géographie au 1er janvier 2025 |
| `LIBGEO` | Nom de la commune |
| `EPCI` | SIREN de l'EPCI |
| `DEP`, `REG` | Codes département, région |
| `loypredm2` | **Indicateur de loyer en €/m²**, charges comprises, bien de référence non meublé |
| `lwr.IPm2`, `upr.IPm2` | Bornes basse / haute de l'**intervalle de prédiction à 95 %** (€/m²) : pas un intervalle de confiance, il est plus large [S3] p. 23 note 8 |
| `TYPPRED` | Niveau de prédiction. Valeurs réelles dans les fichiers : `commune`, `maille`, `EPCI` (le guide écrit « maile », coquille) |
| `nbobs_com` | Nombre d'annonces observées dans la commune ; < 30 = fiabilité faible |
| `nbobs_mail` | Nombre d'annonces dans la maille (≥ 500 par construction) |
| `R2_adj` | R² ajusté du modèle hédonique de la maille ; jugé bon > 0,5 |

Répartition `TYPPRED` constatée : app 4 871 `commune` / 30 029 `maille` ;
app12 3 139 / 31 761 ; app3 3 378 / 31 459 / 63 `EPCI`.

### Ce que « loyer prédit » veut dire

- Modèle hédonique log-linéaire par maille : spline de la surface, surface moyenne par
  pièce, trimestre, année, source, effet fixe commune ou EPCI [S3] p. 21.
- L'indicateur est la prédiction pour un **bien de référence** [S2] p. 1, [S3] p. 24 :

  | Segment | Surface | Surface / pièce |
  |---|---|---|
  | Appartement (tous) | 52 m² | 22,2 m² |
  | T1-T2 | 37 m² | 22,9 m² |
  | T3+ | 72 m² | 21,3 m² |
  | Maison | 92 m² | 22,4 m² |

  « Il ne s'agit donc pas de loyers médians ou moyens » [S2] p. 2. Les coefficients
  (dont l'effet surface) **ne sont pas publiés** : impossible de recaler l'indicateur
  sur la surface exacte d'une annonce. Un 25 m² aura naturellement un €/m² supérieur
  à la référence T1-T2 de 37 m², un 60 m² T2 inférieur.
- Seuils de prudence du producteur : `R2_adj` < 0,5, `nbobs_com` < 30, ou intervalle
  « très large » [S2] p. 2, [S3] p. 28.
- Pas de série temporelle : les millésimes ne sont pas comparables entre eux (maillage
  et bien type changent) [S2] p. 2, [S3] p. 28.
- Sources : leboncoin (84 % de l'échantillon final) et SeLoger ; loyer d'annonce, pas
  loyer de bail [S3] p. 12, 27.

### Correspondance avec le modèle du dépôt

| Donnée carte | Donnée `Listing` | Remarque |
|---|---|---|
| charges comprises | `Price.total` | Cohérent avec l'ADR-0003. Si `charges_unknown`, le total est un loyer nu : le €/m² de l'annonce est **sous-estimé** face à la référence. |
| non meublé | `furnished` | Une annonce meublée paraîtra au-dessus du marché ; à signaler ou exclure. |
| T1-T2 / T3+ | `rooms` | `rooms` ≤ 2 → `app12`, ≥ 3 → `app3`, inconnu → `app` (tous). |
| €/m² | `Price.total / surface_m2` | `surface_m2` est optionnel : sans surface, pas de comparaison. |

## 3. Clé : du nom de commune au code INSEE

La jointure se fait sur `INSEE_C` (5 caractères, zéros de tête conservés : à lire en
chaîne, jamais en entier : cf. `05066`). `LIBGEO` n'est pas une clé : les homonymes
abondent (3 communes nommées exactement « Montagny », dans le 42, le 69 et le 73).

`Location` porte `city`, `postal_code` et `department`, tous optionnels sauf `city` -
pas de code INSEE.

### Ce que fait le dépôt aujourd'hui

- `infrastructure/geocoder.py` : Nominatim via `geopy` pour les coordonnées des villes
  de base (`geocode_cities`, requête `"{city}, France"`, sans `addressdetails` ni
  `extratags`), puis **geo.api.gouv.fr** pour tout le reste :
  `/communes?lat=&lon=&fields=codeDepartement` (`_resolve_dept_of_point`) et
  `/departements/{dept}/communes?fields=nom,centre,codesPostaux`
  (`_fetch_dept_communes`, cache 24 h).
- `infrastructure/crawlers/geo_postal.py` : `/communes?nom=&fields=codesPostaux`.

### Nominatim : possible, mais piégé

Avec `extratags=1`, Nominatim renvoie le tag OSM `ref:INSEE` quand le résultat est la
relation administrative de la commune (vérifié) :

- « Villaz, France » → `ref:INSEE: 74303`, `admin_level: 8`.
- « Seynod, France » → `ref:INSEE: 74268`, `admin_type:FR: commune déléguée`,
  `admin_level: 9` : **code de la commune déléguée, absent de la carte des loyers**.

Autres pièges : le champ `address.municipality` vaut « Annecy » pour Villaz (c'est
l'arrondissement, pas la commune) ; la politique d'usage Nominatim limite à 1 req/s.
À écarter comme source du code INSEE.

### Recommandation : geo.api.gouv.fr, déjà appelé

L'API Découpage administratif expose `code` (« Code de la commune », i.e. code
INSEE) sur `/communes` et `/departements/{code}/communes` [S4]. Vérifié :

```
GET /departements/74/communes?fields=nom,code,centre,codesPostaux
→ 279 communes ; ensemble des codes identique aux 279 lignes DEP=74 de la carte
```

Donc l'approche la plus légère :

1. Ajouter `code` aux `fields` de `_fetch_dept_communes` → table
   `(nom normalisé, département) → code INSEE` gratuite pour chaque commune du rayon,
   déjà en cache 24 h.
2. Désambiguïser par `postal_code` quand il est présent (`codesPostaux` est déjà dans
   la même réponse).
3. Fusions de communes : un nom d'ancienne commune (« Seynod », « Cran-Gevrier »…) ne
   sort pas de `/communes?nom=Seynod` (réponse `[]`, vérifié). L'endpoint
   `/communes_associees_deleguees?codeDepartement=74&fields=nom,code,type,chefLieu`
   [S4] liste en un appel les 16 communes déléguées/associées du 74, avec `chefLieu`
   = code de la commune nouvelle (Seynod 74268 → `chefLieu` 74010, vérifié).

Le code postal seul **ne suffit pas** : 74370 couvre 7 communes (dont Annecy et
Villaz), 74600 couvre Annecy et Montagny-les-Lanches (vérifié via
`/communes?codePostal=`).

Alternative sans réseau : le fichier COG INSEE (communes + mouvements) couvre la même
chose, mais le dépôt ne l'embarque pas et geo.api.gouv.fr en est déjà la projection ;
pas de raison de l'ajouter.

## 4. Couverture des 4 communes (millésime 2025)

Valeurs en €/m² charges comprises ; IP95 = `[lwr.IPm2 ; upr.IPm2]`.

| Commune (INSEE) | Segment | `loypredm2` | IP95 | `TYPPRED` | `nbobs_com` | `nbobs_mail` | `R2_adj` |
|---|---|---|---|---|---|---|---|
| Annecy (74010) | tous | 20,45 | 14,84 ; 28,18 | commune | 16 239 | 16 447 | 0,79 |
| | T1-T2 | 20,92 | 15,69 ; 27,89 | commune | 9 216 | 9 286 | 0,63 |
| | T3+ | 17,97 | 12,77 ; 25,27 | commune | 7 017 | 7 275 | 0,59 |
| Veyrier-du-Lac (74299) | tous | 22,17 | 16,98 ; 28,93 | maille | 77 | 441 | 0,83 |
| | T1-T2 | 20,40 | 15,30 ; 27,21 | maille | 45 | 9 286 | 0,63 |
| | T3+ | 18,04 | 12,82 ; 25,38 | maille | 33 | 7 275 | 0,59 |
| Villaz (74303) | tous | 18,89 | 14,21 ; 25,11 | commune | 220 | 1 223 | 0,82 |
| | T1-T2 | 20,52 | 15,83 ; 26,59 | commune | 104 | 572 | 0,71 |
| | T3+ | 19,55 | 14,47 ; 26,42 | commune | 114 | 757 | 0,61 |
| Montagny-les-Lanches (74186) | tous | 16,27 | 12,52 ; 21,15 | maille | 43 | 484 | 0,82 |
| | T1-T2 | 19,36 | 15,45 ; 24,26 | maille | **19** | 1 048 | 0,67 |
| | T3+ | 16,25 | 12,24 ; 21,56 | maille | **23** | 1 244 | 0,57 |

Constats :

- **Annecy** est sous **74010**, le code de la commune nouvelle (fusion au 1er janvier
  2017 avec Annecy-le-Vieux, Cran-Gevrier, Meythet, Pringy, Seynod). Les codes
  délégués 74011, 74093, 74182, 74217, 74268 sont **absents** du fichier : une annonce
  « Seynod » doit être ramenée à 74010.
- Toutes les lignes ont `R2_adj` > 0,5.
- **Montagny-les-Lanches** T1-T2 et T3+ passent sous le seuil `nbobs_com` < 30 : à
  afficher comme indicatif faible.
- Veyrier-du-Lac en T1-T2 et T3+ est estimé dans la même maille qu'Annecy
  (`id_zone` 152 et 1638, `nbobs_mail` identique à Annecy) mais avec sa propre valeur
  (effet fixe moyen de la maille pour les communes < 100 observations [S3] p. 24).
- Les intervalles sont larges (Annecy, tous : -27 % / +38 % autour de la valeur) : un écart de 10 % à la
  référence n'est pas un signal ; seul un écart qui sort de l'intervalle l'est.
- Pour info, les lignes 74 du fichier : 279, exactement les 279 communes que renvoie
  geo.api.gouv.fr pour le département.

## 5. Bloquants et risques

Aucun bloquant technique. Points à trancher avant d'implémenter :

- **Fraîcheur** : la référence date du T3 2025 et le prochain millésime est attendu en
  décembre 2026. Le fichier est à embarquer (ou à télécharger une fois) par millésime,
  pas à interroger en ligne : il n'y a pas d'API par commune.
- **Mention de source obligatoire** dans l'interface (licence).
- **Surface** : pas de correction possible faute de coefficients publiés ; le
  wording doit dire « loyer de référence pour un T1-T2 de 37 m² », pas « prix du
  marché ».
- **Annonces non comparables** : meublées (`furnished=True`), charges inconnues
  (`charges_unknown`), sans surface. Les exclure du calcul plutôt que d'afficher un
  écart faux.
- **Encodage** : lire en `cp1252`, décimales à virgule, `INSEE_C` en chaîne.
- Ne pas faire de tendance entre millésimes : le producteur l'interdit explicitement.

## Sources

- [S1] data.gouv.fr, « "Carte des loyers" - Indicateurs de loyers d'annonce par commune
  en 2025 », Ministère de la Transition écologique -
  https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025
  (métadonnées via `https://www.data.gouv.fr/api/1/datasets/693aa2feed1bf4da603faa49/`).
- [S2] ANIL / Ministère de la Ville et du Logement, « Guide d'utilisation de la carte
  des loyers », décembre 2025 -
  https://static.data.gouv.fr/resources/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025/20251211-145105/guide-dutilisation-des-donnees.pdf
- [S3] ANIL (d'après Breuillé, Grivault, Le Gallo, INRAE/CESAER), « Les indicateurs de
  loyers dans le parc locatif privé : Note méthodologique », décembre 2025 -
  https://static.data.gouv.fr/resources/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025/20251211-145128/note-methodologique.pdf
- [S4] geo.api.gouv.fr, API Découpage administratif : doc
  https://geo.api.gouv.fr/decoupage-administratif/communes et définition OpenAPI
  https://geo.api.gouv.fr/definition.yml (paramètres `fields`, `codePostal`, `type`,
  endpoint `/communes_associees_deleguees`). Réponses vérifiées en direct le
  2026-09-25.
- Nominatim (OpenStreetMap), `/search?format=jsonv2&addressdetails=1&extratags=1`,
  réponses vérifiées en direct pour « Villaz » et « Seynod ».
- Code du dépôt : `src/apartment_hunter/infrastructure/geocoder.py`,
  `src/apartment_hunter/infrastructure/geocoding.py`,
  `src/apartment_hunter/infrastructure/crawlers/geo_postal.py`,
  `src/apartment_hunter/domain/value_objects/location.py`,
  `src/apartment_hunter/domain/entities/listing.py`, `docs/decisions/0003-budget-en-charges-comprises.md`.
