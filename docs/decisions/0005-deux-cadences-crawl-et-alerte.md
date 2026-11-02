# ADR-0005 — Deux cadences distinctes : crawl et alerte

**Statut** : acceptée, déjà en vigueur — 2026-08-04

## Contexte

`SearchFilter` porte deux champs d'intervalle :

- `refresh_interval_minutes` (défaut 30)
- `notification_interval_minutes` (défaut 15)

Deux mots pour une seule chose seraient une erreur de modélisation à supprimer. Mais
les deux choses sont réellement distinctes : interroger neuf sites est coûteux et
visible côté sources (rate limiting, bannissement d'IP), tandis que remonter les
nouveautés au chasseur est gratuit et peut être groupé pour ne pas harceler.

> **Correction.** La première rédaction de cet ADR affirmait que
> `refresh_interval_minutes` n'était lu par aucun code — sur la foi de
> `docs/technical/scheduler.md`, qui décrivait une boucle dormant
> `min(notification_interval_minutes)`. C'est le **document** qui était périmé : les
> deux boucles de veille, web (`presentation/web/app.py`) et CLI
> (`presentation/cli/main.py`), tiennent déjà deux échéances séparées.

## Décision

Conserver **deux cadences, nommées pour ce qu'elles font** :

- **Cadence de crawl** (`refresh_interval_minutes`) — à quelle fréquence on interroge
  les sources. C'est le réglage de courtoisie et d'auto-protection.
- **Cadence d'alerte** (`notification_interval_minutes`) — à quelle fréquence les
  nouveautés sont remontées. C'est le réglage de confort.

La boucle de veille tient les deux échéances par filtre, relit les deux intervalles à
chaque cycle, et dort jusqu'à la plus proche.

Le minimum de 5 minutes s'applique aux deux, pour la raison déjà documentée : une
échéance dans le passé fait recrawler toutes les sources à chaque tick.

## Conséquences

- Rien à écrire : le comportement est déjà celui-là, dans les deux boucles.
- Une cadence d'alerte plus courte que la cadence de crawl n'apporte rien (aucune
  nouveauté entre deux crawls) mais n'est pas absurde ; ne pas l'interdire, ne pas la
  suggérer.
- L'interface expose les deux réglages ; ils doivent porter les mots du glossaire,
  sinon le champ redeviendra invisible par ignorance — c'est exactement ce qui a fait
  croire à un champ mort.
- `docs/technical/scheduler.md` décrit désormais les deux échéances. Un document qui
  ment sur le code coûte plus cher qu'un document absent : celui-ci a suffi à faire
  écrire un ADR sur un problème inexistant.
