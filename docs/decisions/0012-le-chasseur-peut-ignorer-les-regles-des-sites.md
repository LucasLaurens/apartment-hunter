# ADR-0012 — Le chasseur peut ignorer robots.txt et les CGU des sites, jamais l'anti-bot

**Statut** : acceptée, implémentée — 2026-11-01. Assouplit, sur choix explicite du
chasseur, les règles de collecte posées le 2026-10-30 (`docs/functional/sources.md`).

## Contexte

Les règles de collecte écartaient trois familles de sources :

1. celles dont le `robots.txt` interdit les pages utiles (PAP : toute URL à paramètres ;
   Foncia : la pagination) ;
2. celles dont les conditions d'utilisation interdisent l'extraction automatique de
   leurs annonces (Bien'ici, Locservice, FNAIM, 2A Immobilier) ;
3. celles qui refusent un client honnête par une protection anti-bot (Cloudflare,
   DataDome, captcha : SeLoger, Figaro, EntreParticuliers, et PAP depuis le
   2026-11-01).

Le chasseur veut le plus de sources possible, et prend sur lui le risque des deux
premières familles : c'est son outil, pour sa recherche, à petit volume. Les décisions
de justice contre Jinka (2024 à 2026) montrent que les portails défendent leurs
annonces ; le risque est réel, et c'est le sien.

## Décision

**Un réglage, « Règles des sites » (`SiteRules`), respectées par défaut, ignorées sur
choix du chasseur, dans Paramètres (page web) comme dans `hunt rules`. Ignorées, il lève
les familles 1 et 2. La famille 3 ne bouge jamais.**

- Ignorées : `robots.txt` n'est plus lu ni appliqué, et les sources marquées
  `forbids_reproduction` entrent dans le crawl.
- Toujours : un seul nom honnête (`CRAWLER_USER_AGENT`), aucune imitation de navigateur
  (empreinte TLS, en-têtes), aucun défi Cloudflare ni captcha résolu, aucun compte, la
  même cadence. Un 401/403 reste un refus. `tests/infrastructure/test_no_evasion.py`
  continue de lire le code source.

## Conséquences

- Le réglage est stocké en base (`app_settings`), pas dans le navigateur : il vaut pour
  la page web, `hunt watch` et `hunt search`, et `CrawlAllSources` le relit à chaque
  crawl, donc une veille en cours l'applique au tick suivant.
- Le défaut reste « respectées » : une base neuve ou un chasseur qui n'a rien choisi
  suit les règles.
- Choisir « ignorées » se fait en connaissance de cause : la page dit ce qui s'ouvre et
  que le chasseur en est seul responsable, `hunt rules ignore` le répète et demande
  confirmation.
- PAP, Figaro et EntreParticuliers ne reviennent pas par ce réglage tant que Cloudflare
  les bloque : c'est la famille 3.
