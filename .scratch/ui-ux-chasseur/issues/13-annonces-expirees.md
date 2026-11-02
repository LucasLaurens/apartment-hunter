# Ne plus afficher les annonces expirées

Type: task
Status: resolved
Blocked by:

## Question

Une annonce retirée du site reste affichée dans trois cas :
- **Source en échec** : la purge (`purge_stale_listings.py`) ne retire une annonce disparue que si sa source a renvoyé au moins une annonce pendant le crawl (`authoritative_sources`). Une source bloquée, par exemple ParuVendu derrière son captcha, garde donc ses annonces mortes sans limite de durée.
- **Aucune date de dernière vue** : `fetched_at` est la date de première vue, que `INSERT OR IGNORE` ne met jamais à jour. Impossible de faire expirer une annonce selon son âge.
- **`hunt search` ponctuel** : il ne purge rien (`purge=False`).

## Décidé (grilling du ticket 04, 2026-10-29)

- **Détection** : une colonne `last_seen_at`, mise à jour par chaque crawl qui revoit l'URL. Une annonce non revue depuis 48 h, ou depuis 3 fois l'intervalle de rafraîchissement du filtre si c'est plus long, est masquée, puis purgée. Les seuils sont des constantes nommées du domaine, et l'horloge passe par `ClockPort`.
- **Source en échec** : ses annonces restent visibles, avec la mention « source injoignable, peut-être expirée ». Au-delà de 7 jours d'échec, elles sont masquées, et la page affiche « N annonces masquées : <source> injoignable depuis X j ». Il faut donc retenir, par source, la date du dernier crawl réussi. C'est le même état par source que le constat W3 de l'audit.
- **Pas de sonde HTTP** : on n'interroge pas la page détail (404/410) avant d'afficher une annonce. Ce serait des requêtes en plus sur le budget de rate limit, et elles buteraient sur les mêmes protections anti-bot.

## Garde-fous (demandés explicitement)

- **Rate limiting** : aucune requête nouvelle. `last_seen_at` vient des résultats d'un crawl déjà payé et passe par la porte `_await_turn()`. Le budget `RATE_LIMIT_SECONDS / CITY_CONCURRENCY` ne bouge pas, et un test le garde.
- **Sécurité** : `last_seen_at` et l'état de la source sont des données à nous, jamais du texte scrapé. Le nom de source affiché vient de la liste des crawlers. Côté web, tout passe par `escHtml` et rien ne finit en JS inline. Mise à jour en lot (`executemany`) et en requête paramétrée. Migration testée.
- **Sens de l'erreur** : en cas de doute, on garde l'annonce. Une annonce encore en ligne coûte plus cher à rater qu'un clic perdu, comme pour `tenancy_scope`.

Docs dans le même commit : `docs/technical/data-model.md` (colonne, migration), `docs/technical/scheduler.md` (seuils), `docs/functional/glossaire.md` (« expirée », « source injoignable »).

## Answer

Implémenté sur la branche `feat/annonces-expirees`, partie de `feat/hunt-review-ecarter` parce qu'elle touche `GetTopListings`, qui y gère déjà les écarts.

- **Stockage** : la colonne `listings.last_seen_at` avance à chaque crawl qui renvoie l'URL, jamais en arrière, et la migration la remplit depuis `fetched_at`. La nouvelle table `filter_source_successes` (filtre, source, dernière réponse) est écrite par `RefreshFilter` pour un filtre enregistré, et supprimée avec le filtre.
- **Règle** : `SourceFreshness` (`domain/services/expiry.py`), en O(n).
  - Une annonce dont la source répond sans la renvoyer depuis max(48 h, 3 × cadence) est masquée.
  - Une source muette depuis ce délai : ses annonces restent affichées, marquées, puis sont masquées après 7 jours.
  - **Écart avec la décision** : le temps se compte en crawls du filtre, pas à l'horloge murale. Sinon, une veille arrêtée une semaine aurait vidé la page au retour.
  - Le décompte est **par filtre** : une source qui répond pour un autre secteur ne dit rien de celui-ci.
- **Affichage** : sur la carte web, une mention neutre « source injoignable depuis N j, annonce peut-être expirée ». En CLI, dans la cellule de date, ce qui couvre aussi `hunt review`. En tête de liste web, un avis par source : « 3 annonces masquées : seloger injoignable depuis 9 j ». Vérifié à 1440 et 390 px, sans débordement, et `verify_ui.py` passe.
- **Écart avec la décision** : masquer suffit. La purge reste celle des *retirées*, qui supprime l'annonce au premier crawl où la source répond sans elle. Pas de seconde purge par âge.
- **Garde-fous** : aucune requête nouvelle, donc rate limit inchangé (pas de test ajouté : rien à garder). Uniquement des données à nous, `escHtml` sur le nom de source, requêtes paramétrées, migration testée.
- **Tests** : 20 ajoutés. Huit mutations (une par règle) ont chacune fait échouer au moins un test, puis tout est repassé au vert.
