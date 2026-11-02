# Réparer PAP, Orpi et le DPE de ParuVendu

Type: task
Status: resolved
Blocked by:

## Question

Remettre en état les trois sources qui faussent la collecte, pour que l'audit voie des données réelles :

- **PAP** : `[pap] No geo ID found for 'Annecy', skipping` depuis le 2026-09-25 (marchait le 2026-08-03). Trouver pourquoi la recherche d'identifiant géographique échoue et la réparer.
- **Orpi** : 404 sur `location-immobiliere-epagny-metz-tessy`, slug d'une commune nouvelle. Réparer la construction du slug (`build_city_slug` dans `base_crawler.py`, pas une copie locale).
- **ParuVendu** : le DPE de la page de détail vaut « A » pour toutes les annonces alors que la carte dit autre chose ; `NoteEnerg_([A-G])` attrape sans doute la légende.

Livre du code (voir Notes de la map) : une branche par source, test avec fake concret et HTML d'exemple, docs dans le même commit. Une source impossible à réparer dans les limites (robots.txt, pas de CAPTCHA, pas de compte) est retirée de `build_crawlers()`.

## Answer

Aucune des trois sources n'était cassée comme la note du 2026-09-25 le laissait croire. Les vrais défauts :

- **PAP** — la résolution d'identifiant marche (Annecy = 37473, 13 annonces). Cause de la panne : un échec de `/json/ac-geo` restait en cache pour toute la durée de `hunt watch`. Corrigé : seule une réponse est mise en cache. Les **pages détail renvoient 403** : pas de date de parution ni de meublé, la carte dit « vu le ». Accepté sans contournement (sonder d'autres empreintes TLS a été refusé, à raison).
- **Orpi** — le slug `epagny-metz-tessy` est juste : Orpi n'a **pas de page** pour cette commune, et `/recherche/*` est interdit par son `robots.txt`. Le vrai coût : une commune sans stock est remplie d'annonces d'ailleurs (Limoges), chacune payée d'une page détail. Corrigé par le garde département de Citya : sur « Autour d'Annecy », 45 annonces en 61 s → 31 en 50 s, mêmes 7 dans la zone.
- **ParuVendu** — le DPE « A » partout était déjà corrigé dans le code. Mais la **page détail est derrière un captcha anti-aspiration** : 25 annonces sur 30 sans DPE. Corrigé en lisant le DPE sur la carte et en déduisant le GES des kg CO₂ (`classify_ges`) : 23 sur 30 connus. L'étage reste lu sur la page détail, donc rarement.
- **Trouvé en route** — `geo_postal.resolve_postal_code` avait le même défaut que PAP (échec mis en cache) : Foncia, ParuVendu, Laforêt et Citya pouvaient sauter une commune pour toute une veille. Corrigé.

Branches (non poussées, chacune partie de `main`, `make full` vert) :

- `fix/crawler-pap` — `fix(pap): ne met plus en cache un échec de résolution de commune` (262 tests, +2)
- `fix/crawler-orpi` — `fix(orpi): écarte le remplissage hors département avant l'enrichissement` (262, +2)
- `fix/crawler-paruvendu` — `fix(geo): …` puis `fix(paruvendu): lit le DPE et le GES sur la carte` (264, +4)

Faits pour la suite (audit) : PAP sans date ni meublé, ParuVendu sans étage, Orpi sans Epagny Metz-Tessy. Le `prix-max` de PAP n'est pas respecté côté site (2 230 € pour un plafond de 1 250 €) ; le matcher filtre, non corrigé.
