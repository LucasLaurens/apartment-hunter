# Glossaire — langage du domaine

Le vocabulaire commun de la chasse à l'appartement, tel qu'il doit être utilisé dans
le code, l'interface et les autres documents. Un mot défini ici ne doit pas avoir de
synonyme concurrent ailleurs : voir *Mots bannis* en fin de document.

## Comment lire ce document

Chaque entrée porte un statut :

| Statut | Sens |
|--------|------|
| ✅ | Le code fait déjà ça. Le terme est le bon, l'implémentation aussi. |
| ⚠️ | Le code fait autre chose que ce que le mot dit. Écart connu, à corriger. |
| 🚧 | Décidé lors du cadrage, **pas encore implémenté**. Le mot existe pour que le futur code le porte. |

Les décisions qui ont fixé ces définitions sont tracées dans
[docs/decisions/](../decisions/README.md).

---

## 1. Le bien et son annonce

### Annonce ✅
L'unité de travail de l'application : **une publication, à une URL, sur une source
donnée**. Elle porte un titre, un loyer, une localisation, une date de parution, un
annonceur. Identifiée par `SHA-256(url)` tronqué à 16 caractères.

C'est l'entité `Listing` (`domain/entities/listing.py`), stockée dans la table
`listings`. La classe s'appelait `Apartment` : elle nommait un bien alors qu'elle
modélise une publication.

### Logement ✅
Le bien physique. Un logement peut faire l'objet de **plusieurs annonces** : mandat
non exclusif confié à trois agences, ou une agence qui republie sur un portail.

Deux annonces du même logement restent deux lignes indépendantes en base (deux URLs →
deux hashs) : chacune a son prix, son annonceur, ses photos. Le regroupement est une
affaire **d'affichage** — voir [ADR-0001](../decisions/0001-annonce-est-l-unite-stockee.md).

C'est l'unité que l'interface compte : « 4 logements », pas « 4 annonces ». Le
`ListingGroup` (`domain/services/duplicates.py`) porte l'annonce à montrer (`primary`)
et celles qui la répètent (`others`).

### Doublon ✅
Deux annonces jugées porter sur le même logement : **même commune, même nombre de
pièces, même surface arrondie au m², même loyer**. Le loyer, pas le total : c'est la
provision pour charges qui diffère d'une publication à l'autre. La commune est comparée
repliée (voir *Commune*) : « Chambéry » sur un site et « Chambery » sur Laforêt sont le
même logement, et un logement écarté ne revient pas sous une autre graphie.

Regroupées en une carte portant « aussi sur N autres sources », jamais supprimées —
chaque doublon garde son lien, donc un mauvais regroupement coûte un coup d'œil et pas
un logement manqué. C'est le moins cher en total qui mène le groupe.

**Un logement n'est publié qu'une fois par source** : deux annonces identiques d'un
même site restent séparées. Une résidence publie ses lots identiques côte à côte, et
les fondre masquerait un vrai logement ; une republication, elle, traverse toujours
les sources.

Une annonce sans pièces ni surface n'est jamais regroupée — un inconnu n'est pas une
correspondance.

**Ne pas confondre** avec la déduplication par URL, qui est exacte et automatique
(`INSERT OR IGNORE`), et n'attrape que la même annonce revue au crawl suivant.

### Source ✅
**Où l'annonce a été trouvée** — le site scrapé, donc le crawler qui l'a ramenée.
Valeur technique en minuscules : `pap`, `orpi`, `foncia`, `paruvendu`,
`century21`, `laforet`, `citya`, `squarehabitat`. Champ `Listing.source`.

Deux familles de sources, à ne pas confondre dans les textes :

| Famille | Sources | Ce qu'on y trouve |
|---------|---------|-------------------|
| **Portail** | PAP, ParuVendu | Annonces de multiples annonceurs |
| **Réseau d'agences** | Orpi, Foncia, Laforêt, Century 21, Citya, Square Habitat | Uniquement les mandats du réseau |

### Annonceur ✅
**Qui publie l'annonce** : le nom exact de l'agence locale (« Laforêt Annecy »,
« Century 21 Lac Bleu »), ou personne du tout pour un particulier. Champ
`Listing.advertiser` — le champ s'appelait `agency`, ce qu'un particulier n'est pas.

C'est l'annonceur, pas la source, qui permet de dire « trois sources, même annonceur »
donc probable doublon.

### Enseigne ✅
Le **réseau** auquel l'annonceur appartient : Orpi, Century 21, Laforêt… Un même
logement passe par une seule enseigne mais peut apparaître sur son site propre *et*
sur un portail.

`find_network` (`domain/services/advertiser.py`) la lit dans le nom de l'agence, par
sous-chaîne et sans tenir compte de la casse, des accents ni des espaces — « CENTURY21
Annecy » et « Century 21 Lac Bleu » désignent la même enseigne. Les noms d'enseigne et
la liste des sources de réseau partagent un seul foyer, `NETWORK_NAMES` : aucune ne peut
gagner un membre sans l'autre.

Le filtre `excluded_advertisers` fonctionne par sous-chaîne pour la même raison :
l'utilisateur tape l'enseigne, le champ contient l'annonceur complet.

### Type d'annonceur ✅
`particulier`, `agence` ou `inconnu`. **Affiché, non filtrant** : ça change ce que
coûte le logement (voir *Honoraires de location*) mais ne doit pas masquer une annonce.
PAP publie exclusivement des particuliers ; les cinq réseaux, exclusivement des
agences ; sur les portails mixtes, une annonce qui nomme un annonceur nomme une agence
— le silence reste `inconnu`, jamais deviné « particulier ».

`domain/services/advertiser.py` (`AdvertiserKind`, `detect_advertiser_kind`). La liste des
sources y est doublée de celle des crawlers :
`tests/infrastructure/test_advertiser_source_parity.py` échoue si un crawler est
ajouté sans être classé. La carte n'affiche la puce que si le pied de carte ne nomme
pas déjà l'agence.

---

## 2. L'argent

### Loyer hors charges (HC) ✅
Le loyer nu, sans les charges. Champ `Price.amount`, en `Decimal` — jamais en `float`.

### Charges (provision pour charges) ✅
La provision mensuelle pour les charges locatives récupérables (entretien des parties
communes, eau froide, chauffage collectif le cas échéant, ordures ménagères).
Régularisée annuellement : une provision n'est pas un montant définitif.
Champ `Price.charges`, **optionnel**.

### Charges comprises (CC) ✅
Loyer + charges. Propriété `Price.total`, affichée avec le suffixe `CC`.
**C'est l'unité de budget de l'application** : le filtre prix compare toujours le
total — voir [ADR-0003](../decisions/0003-budget-en-charges-comprises.md).

### Charges inconnues ✅
La source n'a pas publié de provision. Le total vaut alors le loyer nu, donc
**une annonce à 800 € HC passe un filtre « max 850 € » alors qu'elle coûtera ~900 €**.

Ces annonces restent affichées et filtrables, mais portent la mention « charges non
communiquées ». Jamais d'estimation inventée — une provision estimée est un chiffre
faux présenté comme vrai.

Le calcul vit en un seul endroit, `Listing.charges_unknown` : vrai quand il n'y a ni
provision publiée ni mention « CC ». Les trois lecteurs le portent — carte web
(« charges ? » en ambre), tableau CLI et `build_summary_line()` de l'alerte.

### Loyer de référence ✅
Le loyer au m² **charges comprises, non meublé** qu'un logement type aurait dans la
commune, selon la *Carte des loyers* (ANIL, données SeLoger et leboncoin). Choisi selon
les pièces : T1-T2 (logement type de 37 m²), T3+ (72 m²), « tous appartements » si les
pièces sont inconnues. Accompagné d'une **fourchette** (intervalle de prédiction à 95 %).

Une prédiction pour un logement type, pas une médiane : on ne peut pas la recaler sur la
surface réelle. Un millésime par an, jamais comparé à un autre. Mention obligatoire :
« Estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin ».

On ne compare pas à la médiane de nos propres annonces : elle est déjà filtrée par le
budget, et la purge l'efface — voir [ADR-0010](../decisions/0010-position-au-marche-contre-la-carte-des-loyers.md).

### Position au marché ✅
Le total CC au m² d'une annonce comparé à son *loyer de référence*, en pourcentage :
« −12 % vs réf. ». Marquée « hors fourchette » seulement quand elle sort de la fourchette
— c'est le seul cas où « sous le marché » est vrai ; en deçà, le pourcentage sert à
classer, pas à conclure.

« (repère faible) » quand le producteur appelle lui-même à la prudence : moins de 30
annonces observées dans la commune, ou modèle peu ajusté. Pas de position du tout —
« pas de repère (raison) » — pour une annonce meublée, aux *charges inconnues*, sans
surface, ou d'une commune absente de la carte : un chiffre faux classerait en tête ce
qui n'est pas comparable. Aucun repli sur une zone plus large. Si la carte elle-même n'a
pas pu être lue (téléchargement impossible), c'est « pas de repère (carte des loyers
indisponible) » : la faute n'est pas celle de la commune.

Une ancienne commune fusionnée (« Seynod », « Cran-Gevrier ») reçoit la référence de la
commune nouvelle (Annecy) : la carte ne connaît que celle-ci. `hunt review` montre la
position sur chaque ligne (« −12 % », en gras hors fourchette), la phrase entière et la
référence utilisée dans le panneau, et la mention de source en pied d'écran. La carte web
la porte juste sous le total, et la page propose le tri « Position au marché : plus bas »
(la parution reste l'ordre par défaut). Une maison, que le
modèle ne distingue pas, est comparée aux appartements : limite connue.

### Honoraires de location 🚧
Ce que l'agence facture au locataire à la signature : visite, constitution du dossier,
rédaction du bail, état des lieux. Plafonnés au m² par zone. Un particulier n'en
facture pas — c'est la conséquence concrète du *type d'annonceur*.

Hors périmètre du filtre prix (paiement unique, pas mensuel) mais à afficher.

### Dépôt de garantie
Un mois de loyer hors charges en location vide, deux en meublé. Restitué en fin de
bail. Ni stocké, ni filtré, ni affiché — présent ici pour que le mot ne soit pas
confondu avec les honoraires.

---

## 3. Le logement décrit

### Surface habitable ✅
La surface au sol déduction faite des murs, cloisons, marches, gaines et des parties
de hauteur sous plafond inférieure à 1,80 m (loi Boutin, obligatoire au bail
d'habitation). **N'inclut pas** balcon, terrasse, cave, garage, combles non aménagés.
Champ `surface_m2`, en m².

À ne pas confondre avec la loi Carrez, qui concerne la vente en copropriété.

### Annexes 🚧
Balcon, terrasse, jardin, cave, parking, box. Hors surface habitable.
**Affichées, non filtrantes** : une annonce ne doit pas disparaître parce que la
source a omis de mentionner le balcon.

### Pièce ✅
Pièce principale : séjour et chambres. **Ne comptent pas** cuisine, salle de bains,
WC, dégagements, cellier. Champ `rooms`, affiché `Np`.

C'est l'unité de recherche retenue.

### Chambre
Pièce principale destinée au couchage. **Non modélisée.** Conversion à garder en tête
en lisant une annonce :

| Notation | Pièces | Chambres |
|----------|--------|----------|
| T1 / studio | 1 | 0 (séjour = chambre) |
| T2 / F2 | 2 | 1 |
| T3 / F3 | 3 | 2 |
| T4 / F4 | 4 | 3 |

`T` (type) et `F` (fonction) sont employés indifféremment par les annonceurs ;
la distinction historique (le T comptait la cuisine séparée) n'est plus respectée.

### Étage ✅
Niveau dans l'immeuble. Value object `Floor` :

| Valeur | Sens |
|--------|------|
| `level = 0` | Rez-de-chaussée (RDC) |
| `level = -1` | **Étage inconnu** — sentinelle, pas un sous-sol |
| `is_top = True` | Dernier étage |

L'étage est extrait par `parse_floor` (`base_crawler.py`), source unique pour toutes
les sources, depuis un libellé *ou* depuis la prose de l'annonce.

### Dernier étage ✅
`is_top`. Recherché pour l'absence de voisin au-dessus ; à mettre en regard du DPE,
un dernier étage mal isolé chauffant plus.

### Étage inconnu ✅
La source n'a rien dit. Un filtre « dernier étage uniquement » **exclut** l'inconnu
(impossible à confirmer) ; un filtre « pas de RDC » le **garde**, sauf si le texte
contient « RDC » ou « rez-de-chaussée ».

### Meublé ✅
Logement contenant les éléments mobiliers permettant d'y dormir, manger et vivre
convenablement — liste fixée par décret (literie, plaques de cuisson, four ou
micro-ondes, réfrigérateur, vaisselle, ustensiles, table, sièges, rangements,
luminaires, matériel d'entretien). Un logement avec un canapé n'est pas meublé.

Le bail meublé diffère du bail vide (durée, préavis, dépôt de garantie) : ce n'est pas
un détail de confort mais un régime juridique.

**Critère fort** : une erreur de détection coûte cher. Trois heuristiques, dans cet
ordre de priorité (`domain/services/furnishing.py`), la page détail primant la carte :

1. `detect_furnished_label` — page détail, uniquement sur un libellé explicite
   (« Meublé : non »). Le mot nu est ignoré : il figure dans la navigation de tous les sites.
2. `detect_furnished_chip` — puce de critère dont le texte **entier** est le mot,
   pour les sites qui n'étiquettent rien (Laforêt).
3. `detect_furnished` — texte de la carte, par mot-clé.

Résultat tri-état : `True`, `False`, ou `None` = indéterminé. Un `None` n'est jamais
converti en `False`.

### Chauffage collectif ✅
Production de chaleur commune à l'immeuble, facturée dans les charges. Champ
`collective_heating`, tri-état. Explique souvent des charges élevées et un DPE moyen
que le locataire ne peut pas améliorer.

---

## 4. Énergie

### DPE ✅
Diagnostic de performance énergétique. Classe **A** (meilleure) à **G** (pire),
mesurant la consommation d'énergie primaire. Obligatoire dans toute annonce de
location. Champ `dpe_rating` (`DpeRating`).

Ordre du domaine : `A < B < C < D < E < F < G`, du meilleur au pire.

### GES ✅
Étiquette climat, émissions de gaz à effet de serre, même échelle A→G, **calculée
séparément**. Un logement chauffé à l'électricité peut avoir un bon GES et un mauvais
DPE ; au gaz, l'inverse. Champ `ges_rating`.

Les deux étiquettes sont restituées par lettre **et** par couleur — jamais par
couleur seule, la palette réglementaire vert→rouge étant illisible en daltonisme.

### Passoire thermique ✅
Un logement classé **F ou G** au DPE. Notion de premier ordre du domaine, pas une
simple valeur de filtre : la loi Climat et Résilience interdit progressivement leur
mise en location (logements d'habitation, France métropolitaine, nouveaux baux) :

| Classe | Interdite à la location depuis / à partir du |
|--------|---------------------------------------------|
| G | 1ᵉʳ janvier 2025 |
| F | 1ᵉʳ janvier 2028 |
| E | 1ᵉʳ janvier 2034 |

Une annonce F ou G est **affichée avec un avertissement daté**, jamais masquée
d'office : elle existe, elle est publiée, et c'est au chasseur de décider —
voir [ADR-0004](../decisions/0004-passoire-thermique-notion-du-domaine.md).

Le calendrier et la formulation vivent dans `domain/services/energy_regulation.py`
(`RENTAL_BAN_DATES`, `is_thermal_sieve`, `build_rental_ban_warning`). La date du jour est un
**paramètre**, pas une lecture d'horloge : la phrase bascule du futur au passé à une
date fixe, et un test doit pouvoir se placer des deux côtés. La classe E figure au
calendrier parce que la loi l'y met, mais n'est pas une passoire et ne déclenche aucun
avertissement.

### DPE non communiqué ✅
Absence d'étiquette : diagnostic pas encore réalisé par l'agence, mention « vierge »
ou « en cours », ou extraction ratée. **Ce n'est pas un signal négatif** — le plus
souvent le bien n'a simplement pas encore été diagnostiqué.

Traitement retenu : l'annonce reste affichée et passe les filtres DPE, mais porte la
mention « DPE non communiqué ». Ne jamais laisser confondre *absence de DPE* et
*bon DPE* — la carte l'énonce pour les lecteurs d'écran (`energyBadge`), et une note
absente n'est jamais traitée comme une passoire.

---

## 5. Périmètre géographique

### Commune ✅
L'unité administrative française. La « ville » d'une annonce est une commune : celle que
**sa propre carte** nomme sur le site, jamais celle qu'on y a cherchée (un site répond
souvent à une commune avec ses voisines, voire tout le département). Une carte qui ne nomme
aucune commune est écartée plutôt que devinée.
Repliée pour toute comparaison : minuscules, sans accents, tirets, apostrophes et espaces
confondus. « Saint Felix » (Laforêt), « Saint-Félix » (nom INSEE) et « SAINT-FÉLIX » sont la
même commune. Sans ce repli, une annonce dont le site écrit la commune autrement que l'INSEE
ne retrouvait pas ses coordonnées et était écartée en silence (aucun crawler ne relève de
coordonnées), et deux publications d'un même logement n'étaient pas reconnues comme
*Doublon*. Le même repli sert au matcher, au regroupement des doublons et aux écarts. Une
commune renommée ou fusionnée (« Vallieres » pour Vallières-sur-Fier) n'est pas couverte.
Code : `fold_commune_name` dans `domain/services/commune_names.py`.

### Rayon ✅
Distance en kilomètres autour des villes du filtre, à vol d'oiseau (géodésique).
Bornes : 1 à 150 km, défaut 20. Champ `radius_km`.

C'est bien un rayon, pas un temps de trajet : autour d'un lac ou d'un col, 15 km à vol
d'oiseau peuvent faire 40 minutes de route.

### Expansion en communes ✅
Avant le crawl, le rayon est converti en **liste de communes** pour les sources qui ne
savent pas chercher par rayon. Les sources capables portent l'attribut
`covers_radius` et reçoivent le filtre d'origine — voir `CrawlAllSources.execute_detailed`.

### Ville exclue ✅
Commune rejetée quel que soit le rayon (`excluded_cities`). Évaluée avant le calcul de
distance.

### Géocodage ✅
Conversion nom de commune → coordonnées GPS via Nominatim (OpenStreetMap), mis en
cache 24 h. Une annonce sans coordonnées propres hérite de celles de sa commune ; une
commune inconnue du géocodeur n'est gardée que sur correspondance exacte avec une
ville du filtre.

---

## 6. Le temps

### Parution ✅
La date à laquelle **la source** dit que l'annonce a été publiée. `published_at` avec
`published_at_source = SITE`. Affichée « paru le … ».

### Première détection ✅
Le moment où **notre crawl** a vu l'annonce pour la première fois, faute de date
publiée par la source. `published_at` avec `published_at_source = FIRST_SEEN`.
Affichée « vu le … », jamais « paru le … » : ne pas prêter à la source une information
qu'elle n'a pas donnée.

### Fraîcheur ✅
Âge depuis la parution. Le filtre `max_age_days` borne ce qu'on accepte de voir.

### Nouvelle (badge) ✅
Une annonce **que le chasseur n'a pas encore ouverte**. Le badge s'éteint au clic vers
la source, pas au simple défilement de la liste —
voir [ADR-0002](../decisions/0002-nouveau-signifie-pas-encore-ouverte.md). Lu depuis
`Listing.opened`, donc stable d'une session à l'autre ; le sens n'a pas changé avec
l'[ADR-0009](../decisions/0009-le-chasseur-ecarte-un-logement.md), seule l'unité
retenue est passée de l'annonce au logement (voir *Ouverte*).

Trois notions voisines gardent leur sens mais **pas ce nom** :

| Notion dans le code | Ce qu'elle mesure | Nom à employer |
|---------------------|-------------------|----------------|
| `CrawlOutcome.new_count` | Insérée en base à ce crawl | **Découverte** |
| `find_new_since(filter_id)` | Pas encore notifiée pour ce filtre | **Non alertée** |
| `published_at` récent | Fraîcheur côté source | **Récente** |

Le bandeau de l'interface après un rafraîchissement compte des *découvertes* et le dit
ainsi (« N annonces détectées »), pour ne pas rejouer l'ambiguïté.

### Ouverte ✅
Le chasseur a ouvert le **logement** vers sa source, par l'une de ses annonces — c'est
l'événement qui éteint le badge *Nouvelle*. `o` dans la revue et le clic sur la page web
passent par le même cas d'usage (`OpenHome`), qui garde la première ouverture de chaque
annonce dans la table `openings`. La revue affiche « ouverte le … ».

Comme *Écarté*, l'ouverture se souvient du logement
([ADR-0009](../decisions/0009-le-chasseur-ecarte-un-logement.md)) : une annonce est
ouverte quand elle serait regroupée avec une annonce ouverte au sens de *Doublon* —
même URL, ou même clé de logement sur une autre source. Ouvrir une annonce ouvre donc
ses doublons, et une annonce purgée puis recrawlée sous la même URL reste ouverte. Deux
lots identiques d'une même source restent distincts, et une annonce sans pièces ni
surface n'est reconnue que par son URL.

Non liée au filtre : un logement lu l'est pour de bon, quel que soit le filtre qui l'a
fait remonter.

### Retirée (delisted) ✅
L'annonce ne figure plus dans le dernier crawl d'une source **qui a répondu**
(voir *Source faisant autorité*) alors qu'elle correspond au filtre crawlé : le bien
est loué ou l'annonce a été dépubliée. **L'annonce est supprimée de la base**, pas
marquée : une annonce partie est du bruit.

### Expirée ✅
L'annonce n'a plus été renvoyée par sa source alors que celle-ci **répondait** au filtre,
depuis plus de max(48 h, 3 × cadence de crawl). Masquée, pas supprimée : la purge des
*retirées* s'en charge au crawl suivant. Le temps se compte en crawls du filtre, pas à
l'horloge : une veille arrêtée ne fait rien expirer. `SourceFreshness`,
`domain/services/expiry.py`.

### Source injoignable ✅
Une source qui n'a plus *fait autorité* pour ce filtre depuis le même délai, alors qu'une
autre a répondu. Ses annonces ne sont pas expirées : on n'en sait rien. Elles restent
affichées, marquées « source injoignable depuis N j, annonce peut-être expirée », puis
masquées après 7 jours, la page disant combien et pourquoi. Dans le doute on garde :
une annonce encore en ligne coûte plus cher à rater qu'un clic perdu.

### Hors critères (irrelevant) ✅
L'annonce ne correspond plus à **aucun** filtre enregistré — typiquement après une
modification de critères. Supprimée également. Jugée contre tous les filtres, jamais
contre un seul : le vivier d'annonces est partagé.

### Écarté ✅
Un **logement** que le chasseur a décidé de ne plus voir, avec une raison. C'est son
geste à lui, là où *retirée* est celui de la source et *hors critères* celui du filtre.

On écarte un logement, pas une annonce : toute annonce qui serait regroupée avec une
annonce écartée au sens de *Doublon* est écartée aussi — la même URL revenue après une
purge, ou le même logement publié par une **autre** source. Deux annonces identiques
d'une même source restent distinctes (les lots d'une résidence) : une republication par
la même source sous une nouvelle URL n'est donc pas reconnue, et revient. Une annonce
sans pièces ni surface n'est jamais regroupée, donc n'est reconnue que par son URL.

Non lié au filtre, comme *Ouverte*. Pas d'expiration : un logement écarté le reste
jusqu'à ce que le chasseur le **restaure**, et il reste alors marqué « restauré le … »
pour dire qu'il a déjà été jugé une fois — dans la revue, sur la carte web et dans
l'alerte, doublons compris. La raison d'un écart restauré ne compte plus ; un nouvel
écart remplace l'ancien, raison comprise, et efface la mention.

Dans `hunt review`, `d` bascule entre « à revoir » et « écartés » (`hunt review
--dismissed` ouvre directement les écartés) ; là, `u` restaure le logement sélectionné.
Dans « à revoir », `u` annule le dernier écart, ce qui revient au même geste.

Si son loyer change, le logement n'est plus reconnu et réapparaît, même sous la même
URL, avec la mention « écarté le 12/10/2026 à 1 210 € (trop cher) » — la date, le total
CC au moment de l'écart et la raison : une baisse de loyer est une information. L'écart
est retrouvé par la commune, les pièces et la surface, sans le loyer ; cette
comparaison sert à **afficher**, jamais à masquer. Un logement sans pièces ni surface
ne reçoit jamais la mention, faute de quoi le comparer. Masqué partout, et la mention
lue partout — revue, page web, alerte. Voir [ADR-0009](../decisions/0009-le-chasseur-ecarte-un-logement.md).

Sur la page web : bouton « Écarter » sur chaque carte, ou au clavier `j`/`k` puis `x`, puis
la touche de la raison, les mêmes que `hunt review`. « Annuler » dans le message qui suit
vaut restauration ; la page « Écartés » (barre latérale) liste les écarts en vigueur, chacun
avec « Restaurer ».

« Déjà vu » se dit *ouverte* : « vu le … » est réservé à la *première détection*.

### Raison d'écart ✅
Pourquoi le chasseur a écarté un logement, choisie dans une liste fermée — trop cher,
trop petit, étage, DPE, commune, annonceur, meublé, aspect — ou *autre* avec un texte
libre, éventuellement vide. Toujours donnée : sans raison, pas d'écart.

*Aspect* couvre ce que seul l'œil juge (photos, luminosité, état) et ne correspond à
aucun critère. On dit **commune**, jamais « quartier » : le modèle ne connaît pas les
quartiers. Un *autre* qui revient souvent devient une valeur de la liste, à la main.

L'écart garde une photo figée du logement ce jour-là (total CC, surface, étage, DPE,
annonceur, meublé) : c'est elle qui donne sa valeur à une *suggestion de critère*.

### Suggestion de critère ✅
Une modification de filtre proposée au chasseur après **3 écarts pour la même raison**
(et la même valeur, quand elle en a une : même commune, même annonceur). La valeur est
la plus prudente qui couvre les écarts — pour *trop cher*, la dizaine sous le plus petit
total CC écarté — et la question dit combien de logements non écartés la modification
masquerait aussi.

Jamais appliquée sans confirmation : un filtre modifié en silence, c'est des logements
manqués sans le savoir. Refusée, elle ne revient qu'après 3 nouveaux écarts pour la même
raison. Proposée pour chaque filtre qui laisse encore passer ces logements.

Ce que chaque raison propose : *trop cher*, le loyer max à la dizaine sous le plus petit
total CC écarté (1 230 € → 1 220 €) ; *trop petit*, la surface min au m² entier au-dessus
de la plus grande surface écartée ; *étage*, l'exclusion du rez-de-chaussée ou du 1er (un
étage inconnu ne compte pas, un autre étage n'a pas de critère) ; *DPE*, le retrait de la
meilleure lettre écartée et des plus mauvaises ; *commune* et *annonceur*, l'exclusion —
jamais celle d'une commune sur laquelle le filtre est centré ; *meublé*, le critère
inverse, sur un filtre encore indifférent. *Aspect* et *autre* n'en proposent jamais. Un
écart restauré ne compte plus. Dans `hunt review`, la question `[o/N]` suit l'écart qui
l'a déclenchée ; `o` enregistre le filtre par le chemin d'édition habituel, tout autre
touche refuse.

---

## 7. La veille

### Filtre ✅
L'objet enregistré qui porte à la fois les **critères** (villes, rayon, prix, surface,
pièces, étage, DPE, meublé…) et la **surveillance** (cadences, activé/désactivé).
Entité `SearchFilter`. C'est le mot retenu pour l'interface — pas « veille », pas
« recherche enregistrée ».

### Crawl ✅
Un passage sur toutes les sources pour un filtre donné. Concurrence plafonnée
(sémaphore de 5), chaque source plafonnée à 180 s pour qu'une source pendue ne bloque
jamais le tour. Une source en échec est journalisée, les autres continuent.

À l'écran, un crawl se dit **recherche** (« Recherche en cours… », « Dernière recherche : il y a
12 min ») : « crawl » reste le mot du code et de la doc technique. Pendant une recherche lancée
depuis la page, chaque source dit où elle en est : en cours, N annonces, aucune annonce, échec.

### Source faisant autorité ✅
Source ayant renvoyé **au moins une annonce** à ce crawl. Seules celles-là peuvent
faire conclure qu'une annonce a été retirée : un résultat vide peut être un parse raté
silencieux ou un blocage anti-bot, pas un marché vide.
Champ `CrawlOutcome.authoritative_sources`.

### Cadence de crawl ✅
Fréquence à laquelle on interroge les sources (`refresh_interval_minutes`, défaut
30 min). Coûteuse et visible côté sites : c'est elle qui doit rester raisonnable.
Dans la modale de filtre : « Chercher sur les sites toutes les … min ».

### Cadence d'alerte ✅
Fréquence à laquelle les nouveautés sont remontées au chasseur
(`notification_interval_minutes`, défaut 15 min). Groupe les annonces pour ne pas
harceler. Dans la modale de filtre : « M'alerter au plus toutes les … min ».

Les deux échéances sont tenues par `WatchFilters`
(`application/use_cases/watch_filters.py`), un seul foyer pour les deux points d'entrée,
et les filtres sont relus à chaque passe — voir
[ADR-0005](../decisions/0005-deux-cadences-crawl-et-alerte.md). La cadence de crawl est
elle-même un budget par fenêtre côté source, pas un délai en série
([ADR-0008](../decisions/0008-cadence-de-crawl-fenetre-partagee.md)).

### Minimum de cadence ✅
5 minutes, refusé en dessous à la construction du filtre. Ce n'est pas cosmétique : un
intervalle non positif place la prochaine échéance dans le passé, la boucle recrawle
toutes les sources à chaque tick (~1 s) et l'IP se fait bannir.

### Alerte ✅
Remontée des annonces correspondant à un filtre et **pas encore alertées** pour ce
filtre. Une annonce alertée est enregistrée comme telle (`mark_notified`) et ne
repasse jamais. Canal actuel : terminal + badge web.

### Purge ✅
Passage de nettoyage qui supprime les annonces *hors critères* et *retirées*.

La purge suit un crawl et ne juge que ce qu'il a vu : une annonce qu'aucun crawl
n'atteint plus (sa commune a quitté tous les rayons, ou un ancien crawler l'a rangée
sous la mauvaise commune) n'est jamais revue, donc jamais purgée. `hunt clean` la
supprime à la main : hors de tout filtre, ou non revue depuis N jours (7 par défaut).
Les écarts et les ouvertures restent mémorisés.

---

## 8. Hors périmètre

Décidé : l'application **détecte et affiche**, elle ne suit pas une candidature. Ces
mots ne doivent pas apparaître dans le code ni dans l'interface.

- **Dossier de location**, garant, Visale, caution solidaire, justificatifs
- **Visite**, contact agence, relance
- **Bail**, préavis, état des lieux
- **Statut de candidature** (à contacter, contacté, dossier envoyé, refusé)

Le seul état conservé côté chasseur est *ouverte* (voir ci-dessus), qui sert le badge
et rien d'autre.

### Types de biens exclus ✅
Écartés avant affichage, parce qu'ils polluent la comparaison des prix :

- **Colocation / chambre chez l'habitant** — ce n'est pas un logement entier ; son
  loyer bas fausse les tris.
- **Bail mobilité / location saisonnière** — 1 à 10 mois, meublé touristique, hors
  sujet pour une location durable.

`domain/services/tenancy_scope.py` (`is_out_of_scope_tenancy`), appliqué
inconditionnellement par `ListingMatcher` : ce n'est pas une option de filtre, c'est
la définition de ce que l'outil cherche. **Conservateur par construction** — seules les
formulations décrivant l'offre elle-même comptent : un T4 « idéal colocation » est un
T4 et passe. Un titre qui **commence** par « Colocation » (« Colocation à louer », l'annonce
d'une chambre sur un portail) propose la colocation elle-même et est exclu ; « Grand T5
pour colocation » loue l'appartement entier et passe. Une annonce ratée coûte bien plus
cher qu'une chambre à écarter de l'œil.

**Non exclues** : les maisons. Une maison au bon prix dans le bon rayon reste
recevable, malgré le nom `Listing`.

---

## 9. Mots bannis

| N'écris pas | Écris | Pourquoi |
|-------------|-------|----------|
| « appartement » pour désigner la ligne stockée | **annonce** (`Listing`) | La ligne est une publication, pas un bien |
| « annonce » pour compter les résultats affichés | **logement** | La liste montre un logement par groupe, doublons repliés |
| « nouveau » sans préciser | **découverte** / **non alertée** / **récente** / **non ouverte** | Quatre notions distinctes se cachent derrière un mot |
| « agence » pour un particulier | **annonceur** | PAP ne publie aucune agence |
| « site » | **source** | Le champ s'appelle `source` |
| « prix » seul | **loyer HC** ou **total CC** | L'écart est de l'ordre de 10 % |
| « surface » sans précision | **surface habitable** | Balcon et cave n'y sont pas |
| « F/G » sans mention | **passoire thermique** | Le mot porte la conséquence légale |
| « supprimée » pour une annonce partie | **retirée** | Distingue le geste de la source du nôtre |
| « écart » pour la différence de loyer | **position au marché** | « Écart » est le geste du chasseur (*écarté*) |
| « prix du marché » | **loyer de référence** | C'est une prédiction pour un logement type, pas un prix constaté |

---

## 10. Écarts connus, ouverts

Ce qui reste à porter au code. Chaque ligne est une décision déjà prise, pas une idée.

1. **Photos** : aucun crawler ne remplit `images`. Le critère `min_photos` ne rejette
   donc rien — un ensemble vide se lit « non collecté », jamais « zéro photo ». Le
   compter comme zéro faisait rejeter toutes les annonces.
2. **Chauffage collectif** : jamais renseigné par une source, donc le critère laisse
   tout passer. Affiché quand la base le contient.
3. **Annexes** (balcon, terrasse, cave, parking) : décidées « affichées, non
   filtrantes », mais aucun crawler ne les extrait.
4. **Honoraires de location** : conséquence concrète du type d'annonceur, jamais lus
   ni affichés. Les extraire suppose de lire le barème de chaque agence.
5. **Chambres** : la recherche se fait en pièces, décision assumée. Si les chambres
   deviennent un critère, il faudra les extraire — aucune source ne les donne partout.

### Corrigé depuis la rédaction initiale

- Le premier jet annonçait que `refresh_interval_minutes` n'était lu par personne.
  C'était faux : les deux boucles de veille tenaient déjà deux échéances, et le
  document périmé était `docs/technical/scheduler.md`.
- `Apartment` → `Listing`, `agency` → `advertiser`, table `apartments` → `listings` :
  faits, migration de renommage comprise
  (`tests/infrastructure/test_sqlite_rename_migration.py`). Le paquet Python
  `apartment_hunter` et le nom du produit, eux, ne changent pas — le glossaire
  interdit « appartement » pour la ligne stockée, pas pour l'outil.
