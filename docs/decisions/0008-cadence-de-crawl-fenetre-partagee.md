# ADR-0008 — La cadence de crawl est une fenêtre partagée, pas un délai en série

**Statut** : acceptée, en vigueur — 2026-08-05

## Contexte

`CLAUDE.md` promet « min 1.5s delay between requests per domain » et chaque crawler
déclare un `RATE_LIMIT_SECONDS`. Le code ne tenait pas la promesse :

- seul `_get_throttled` lisait la valeur, et un seul crawler sur neuf emprunte ce
  chemin — les huit autres passent par `_fetch_html` → `_fetch_with_cffi`, qui ne
  temporisait rien ;
- l'arithmétique était de toute façon fausse en concurrence : quatre recherches de
  communes simultanées lisaient le même `_last_request`, dormaient la même durée et
  repartaient ensemble ;
- SeLoger l'avait compris et réimplémentait la temporisation à la main, contre
  l'attribut privé de la classe de base.

Brancher la temporisation telle qu'annoncée n'était pas neutre. Un crawl couvre jusqu'à
30 communes (`_MAX_COMMUNES`) sur 4 pages, soit ~120 requêtes par source. Espacées de
1,5 à 2 s en série, cela dépasse le plafond de 180 s par source
(`SOURCE_TIMEOUT_SECONDS`) : chaque run rendrait des résultats partiels, et la
politesse serait payée en couverture.

## Décision

`RATE_LIMIT_SECONDS` est un **budget par fenêtre**, pas un délai entre deux requêtes
consécutives. Une source est interrogée `CITY_CONCURRENCY` communes à la fois, donc le
débit agrégé autorisé est de `CITY_CONCURRENCY` requêtes par `RATE_LIMIT_SECONDS` —
soit un espacement de `RATE_LIMIT_SECONDS / CITY_CONCURRENCY` entre deux départs.

Une seule porte, `BaseCrawler._await_turn`, tient ce rythme pour tout le crawler :
le chemin HTML et le chemin `_get_throttled` (la boucle Playwright de SeLoger aussi, jusqu'au
retrait de la source le 2026-10-30). Le
verrou est tenu pendant l'attente, de sorte que chaque appelant réserve le prochain
créneau libre au lieu de lire une échéance partagée.

## Conséquences

- La temporisation existe enfin pour les neuf sources. Avant cet ADR, il n'y en avait
  aucune sur huit d'entre elles.
- Le débit reste compatible avec le plafond de 180 s : ~120 requêtes espacées de 0,5 s
  tiennent en 60 s, contre 240 s en série.
- Le nombre est explicite et nommé : `compute_request_spacing_seconds()`. Le durcir se fait en
  un endroit, et le coût se lit directement — diviser l'espacement par deux double la
  durée d'un crawl.
- SeLoger n'a plus sa propre temporisation, et plus aucun code ne touche
  `_last_request` : l'attribut a disparu.
- Si une source se met à bloquer malgré tout, le levier est `RATE_LIMIT_SECONDS` sur
  ce crawler seul — et le plafond de 180 s reste le filet : une source lente rend une
  liste vide, n'est pas considérée comme faisant autorité, et la purge ne touche donc
  pas à ses annonces.
