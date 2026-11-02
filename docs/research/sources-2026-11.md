# Nouvelles sources de location autour d'Annecy — novembre 2026

Recherche du 2026-11-01. Objectif : trouver des sites d'annonces de location que le projet
pourrait collecter **sans enfreindre ses règles de collecte** (`robots.txt` appliqué, ni
captcha, ni compte, ni contournement anti-bot, ni CGU interdisant la reproduction). Aucun
code de crawler n'a été écrit.

## Méthode

- Client : `curl`, User-Agent du projet `apartment-hunter/0.1 (personal home search)`
  (`CRAWLER_USER_AGENT`), `Accept-Language: fr-FR`, sans cookie, sans redirection suivie
  automatiquement, sans imitation TLS ni navigateur headless.
- Budget : 2 à 4 requêtes par site (redirections comprises), au moins 3 s entre deux
  requêtes vers un même hôte. Total : 44 requêtes sur 14 sites.
- Ordre : `robots.txt`, puis la page de liste d'une commune (Annecy 74000), puis CGU ou
  mentions légales quand la source restait plausible.
- Découverte des candidats et des motifs d'URL : moteur de recherche (aucune requête vers
  le site lui-même), plus les agences locales repérées sur la liste FNAIM d'Annecy.
- Hors champ : les sources déjà tranchées dans `docs/functional/sources.md` (actives et
  retirées), dont PAP, Jinka, Bien'ici, Locservice, Figaro, EntreParticuliers, SeLoger,
  LeBonCoin, Logic-Immo, et la liste rejetée le 2026-10-30 (lesiteimmo, 4807 Immobilier,
  Lamy, CDC Habitat, Le Partenaire, Trovit, Mitula, Zimo, Journal des Particuliers, ERA,
  Capifrance, iad, Nestenn). Rien n'indiquait un changement chez ces derniers : pas de
  nouvelle vérification.

## Résultat en une phrase

**Aucun candidat retenu.** Les deux sources qui auraient vraiment ajouté du stock (FNAIM,
2A Immobilier) sont techniquement collectables, mais leurs mentions légales interdisent
l'extraction ou la reproduction — la même raison qui a écarté Bien'ici et Locservice.

## Sites examinés

Stock = appartements à louer visibles le 2026-11-01 sur la page examinée.

| Site | URL de liste (commune) | `robots.txt` sur ce motif | HTML serveur | Champs sur la liste | Stock près d'Annecy | CGU / mentions légales | Verdict |
|------|------------------------|---------------------------|--------------|---------------------|---------------------|------------------------|---------|
| **FNAIM** (fnaim.fr) | `/liste-annonces-immobilieres/18-location-appartement-{ville}-{cp}.htm`, page 2 : `…-{cp}-page-2.htm?localites=[…]` | Liste autorisée (le paramètre `localites=` n'est pas visé ; seuls `UTB_*`, `fontSize`, `style`, `reset` le sont). **Page détail interdite** : `Disallow: /annonce-immobiliere/*/18-location*`, sitemaps de location interdits aussi | Oui | Loyer « par mois » (CC/HC non précisé), surface, pièces, chambres, meublé, balcon/ascenseur, agence. Pas de DPE ni de date sur la carte ; détail inaccessible | **49** à Annecy 74000 (« 25 résultats sur 49 », dont quelques annonces « haute-savoie-74 » en remplissage). Agrège des agences absentes de nos sources : 2A Immobilier, Agence BFM, Entre 2 Lacs, Like My Home | Mentions légales : « Toute extraction ou réutilisation de tout ou partie de cette base de données est interdite » ; reproduction interdite | **Rejeté** (mentions légales, et `robots.txt` qui ferme le détail des locations) |
| **2A Immobilier** (2a-immo.fr) | `/location` (filtre `geolocations[]`, pagination `?page=N`) ; annonce : `/location/appartement/{ville}/…-ref-{n}` | Autorisé (Drupal standard, seuls `/search/`, `/admin/`, `/user/*` interdits) | Oui | Loyer **CC**, surface, pièces, chambres, meublé, ville, référence. Pas de DPE ni de date sur la liste | 12 biens sur la page 1 (8 pages au total, caves et locaux compris) ; appartements à moins de 15 km sur cette page : Annecy ×2, Villaz ×1 (+ Collonges-sous-Salève, Gex, Aix-les-Bains plus loin) | Mentions légales : « toute reproduction, représentation, transmission, diffusion, partielle ou totale, est interdite » ; « Toute utilisation de données figurant sur ce site nécessite une autorisation préalable et expresse » | **Rejeté** (mentions légales) |
| **in'li** (inli.fr) | `/locations/offres/haute-savoie_d:74/` ; ville : `/locations/offres/{ville}-{cp}_v:{cp}/` | Autorisé (seul `/espace-membre/` interdit) | Oui | Loyer **CC**, pièces, surface, commune, neuf/meublé | 8 logements dans le 74, **1** près d'Annecy (Allonzier-la-Caille, ~13 km) ; les autres dans le Genevois (Douvaine, Chenex, Chevrier, Ambilly) | CGU : ne pas « télécharger, reproduire, vendre ou distribuer le contenu […] sans l'autorisation expresse d'in'li » ; usage « privé ou familial » seulement. Logement intermédiaire sous plafonds de ressources, candidature via compte | **Rejeté** (CGU, et 1 seul logement dans le rayon) |
| **Vivastreet** (vivastreet.com) | `/immobilier-location-appartements-meubles/{ville}-{cp}` ; la catégorie non meublée redirige vers une page générique `/annonces/{ville}-{cp}` | Liste autorisée ; `/search/*`, `?type=`, `?view=`, filtres particulier/professionnel interdits | Oui | Titre, description libre, prix, ville | 5 meublés « dans un rayon de 50 km », tous vers la frontière suisse (Viry, Saint-Julien, Annemasse), aucun à Annecy | CGU : interdit d'« utiliser de robot-araignée, grattoir ou autre moyen automatisé pour […] collecter des données […] sans l'autorisation écrite expresse » | **Rejeté** (CGU explicites contre la collecte automatisée) |
| **Cimm Immobilier** (cimm.com, ex-cimm-immobilier.fr) | `/search/location/appartement/{ville}-{cp}` | Tout autorisé (`Allow: /`) | Non : gabarits `{{price}}` remplis en JavaScript | — | 0 (« 0 bien correspondant à vos critères », Annecy 74000) | Non consultées | **Rejeté** (aucun stock, liste rendue côté client) |
| **Oralia** (oralia.fr) | `/location/nos-biens-a-louer/auvergne-rhone-alpes/haute-savoie-74` | Autorisé | Oui | — | 0 (page département vide ; cabinets dans l'Ain, l'Isère, la Loire, le Rhône) | Non consultées | **Rejeté** (aucun stock dans le 74). Le sitemap pointe vers lamy-immobilier.fr : même groupe que Lamy, déjà écarté |
| **SAFTI** (safti.fr) | `/annonces/location/appartement/{ville}-{cp}` | Liste autorisée ; `/recherche` et `?location`, `?sort`… interdits | Oui | — | 0 (« 0 Appartement à louer, ANNECY (74000) ») | Non consultées | **Rejeté** (aucun stock ; réseau de mandataires orienté vente) |
| **Immonot** (immonot.com, notaires) | `/immobilier-notaire/annonces/Ccom_74010_74000/location-appartement-a-louer-74000-annecy-haute-savoie.html` | Autorisé (seuls `/api/`, `/account/`… interdits) | Oui | — | 0 location à Annecy (la page propose des ventes en remplacement) | Non consultées | **Rejeté** (aucun stock) |
| **immobilier.notaires.fr** | Non trouvée : `/fr/annonces-immobilieres/location/appartement/annecy-74` → 404 ; liste en `?typeTransaction=LOCATION` | `Crawl-delay: 10` ; `/search/`, `?latitude=`, `?longitude=`, `?p=` interdits | Non : application AngularJS (`ng-app`) | — | Non vérifié | Non consultées | **Rejeté** (rendu client ; Immonot, même offre notariale, n'a aucune location à Annecy) |
| **Acheter-Louer** (acheter-louer.fr) | Non trouvée : `/annonces/immobilier/location-appartement-annecy` → 404 | `Disallow: /recherche` et `/geolocalisation` : la recherche par commune est interdite | Oui (accueil) | — | Non vérifié (« 0 annonces trouvées » sur l'accueil) | Non consultées | **Rejeté** (`robots.txt` ferme la recherche) |
| **Optimhome** (optimhome.com) | Non atteinte | Filtres `?city=`, `?place=`, `?page=`… interdits | — | — | — | — | **Rejeté** : HTTP 403 « Just a moment… » (challenge Cloudflare) |
| **Location-etudiant.fr** | `/logement-etudiant/{Ville}-{code}.html` | Autorisé (sauf `*&loyer*`) | Oui | Loyer, type (T1…), surface, disponibilité, annonceur | 33 « logements étudiants » à Annecy, en majorité résidences de services et aparthotels (Adagio à 1 700 €) | Non consultées | **Rejeté** (hors périmètre : résidences et logements étudiants, que `tenancy_scope` écarte) |
| **ImmoJeune** (immojeune.com) | `/location-appartement/{ville}-{dept}.html` | Autorisé (sauf `/user/*`) | Oui | Loyer CC, surface, type | Quelques annonces, surtout chambres et colocations (« chambre à louer… 3 mois ») | Non consultées | **Rejeté** (hors périmètre : chambres, colocations, courtes durées) |
| **Studapart** (studapart.com) | `/fr/logement-etudiant-{ville}` | Page autorisée, mais tous les filtres (`?minPrice=`, `?roomsCount=`, `?furnished=`…) interdits | Oui (page guide) | — | Non vérifié | Non consultées | **Rejeté** (location étudiante payée sur la plateforme, compte requis ; filtres interdits) |

## Candidats retenus

Aucun.

Si le projet décidait de **demander une autorisation écrite** (la seule voie que les règles
laissent ouverte à ces sources), l'ordre par stock près d'Annecy serait :

1. **FNAIM** — 49 annonces à Annecy 74000, agrège plusieurs agences locales que nos
   sources ne couvrent pas. Même avec un accord, le `robots.txt` interdit les pages détail
   des locations : pas de DPE, d'étage ni de date, et loyer sans mention CC/HC.
2. **2A Immobilier** — au moins 3 appartements dans le rayon d'Annecy, loyer CC, liste propre.
   Ces annonces paraissent déjà sur la FNAIM.
3. **in'li** — 1 logement dans le rayon, et réservé aux ménages sous plafonds de
   ressources.

## Non vérifié

- **Sites d'agences locales** vues sur la FNAIM (Agence BFM, Entre 2 Lacs Immobilier, Like
  My Home, Tour des Lacs Immobilier, 74immo) : sites propres non trouvés ou non sondés.
  Like My Home propose surtout des baux mobilité ou étudiants, hors périmètre.
- **Stock FNAIM des autres communes** du rayon (Annecy-le-Vieux, Seynod, Cran-Gevrier,
  Pringy…) : seule la page Annecy 74000 a été lue.
- **CGU** de Cimm, Oralia, SAFTI, Immonot, immobilier.notaires.fr, Acheter-Louer,
  Location-etudiant, ImmoJeune, Studapart : non lues, ces sites étant déjà écartés pour une
  autre raison.
- **Stock d'immobilier.notaires.fr** : la liste est rendue en JavaScript, le motif d'URL
  par commune n'a pas été trouvé.
- **Bailleurs sociaux** (Haute-Savoie Habitat, Halpades…) : non sondés ; l'attribution
  passe par une commission, pas par une annonce de marché.

## Constat à remonter

Dans cet échantillon, la clause type « toute reproduction […] est interdite » du Code de la
propriété intellectuelle figure sur **chaque** site dont les mentions légales ont été lues
(FNAIM, 2A Immobilier, in'li, Vivastreet). Elle est probablement présente aussi sur les
réseaux déjà actifs (Orpi, Foncia, Century21…), non vérifiés ici. Appliquer la règle « CGU
interdisant la reproduction » avec la même rigueur partout pourrait donc retirer des sources
actives. Cette incohérence relève d'une décision du projet (ADR), pas de cette recherche.
