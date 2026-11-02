# Scheduler & Mode Watch

## Fonctionnement du mode watch

`hunt watch` implémente une boucle `while True` async. Pas de framework de scheduling (pas d'APScheduler, pas de cron) — la boucle est gérée directement avec `asyncio.sleep`.

```
hunt watch démarré
    │
    ▼
[pour chaque filtre actif]
    │
    ├── CrawlAllSources.execute(base, expanded)   ← radius-natives: base ; par-ville: communes
    │       ├── PapCrawler.fetch()       ─┐ parallèle  │
    │       ├── OrpiCrawler.fetch()      ─┤ semaphore(5)│
    │       ├── FonciaCrawler.fetch()    ─┤            │
    │       ├── ParuVenduCrawler.fetch() ─┤            │
    │       ├── Century21Crawler.fetch() ─┘            │
    │       └── SqliteRepository.save_many() ←─────────┘
    │
    ├── NotifyNewListings.execute(filter)
    │       ├── find_new_since(filter_id)  ← SQL: NOT EXISTS notifications
    │       ├── ListingMatcher.matches() pour chaque annonce
    │       ├── CompositeNotifier.notify()
    │       │       └── TerminalNotifier
    │       └── mark_notified(ids, filter_id)
    │
    └── [filtre suivant...]
    │
    ▼
asyncio.sleep(jusqu'à la plus proche des deux échéances)
    │
    └── → recommencer
```

---

## Les deux cadences

Un filtre porte **deux** rythmes distincts, et la boucle suit les deux séparément
(voir [ADR-0005](../decisions/0005-deux-cadences-crawl-et-alerte.md)) :

| Cadence | Champ | Défaut | Ce qu'elle déclenche |
|---------|-------|--------|----------------------|
| **Crawl** | `refresh_interval_minutes` | 30 min | interrogation des 10 sources + purge |
| **Alerte** | `notification_interval_minutes` | 15 min | remontée des annonces pas encore alertées |

Crawler est coûteux et visible côté sources ; alerter est gratuit et se groupe. Les
deux échéances sont tenues par filtre, et le sleep vise la plus proche.

La cadence de crawl règle aussi l'**expiration** (`domain/services/expiry.py`). Une
annonce que sa source a cessé de renvoyer tout en répondant est masquée au-delà de
`compute_stale_after()` = max(48 h, 3 × `refresh_interval_minutes`). Une source qui ne
répond plus au filtre depuis ce délai voit ses annonces marquées « source injoignable »,
puis masquées au-delà de 7 jours (`SOURCE_DOWN_HIDE_AFTER`). Le temps se mesure contre
les crawls du filtre, jamais contre l'horloge murale : une veille arrêtée un mois ne
vide pas la page. Aucune requête supplémentaire : tout vient des crawls déjà faits.

La politique vit dans `application/use_cases/watch_filters.py` (`WatchFilters`), un
seul foyer pour les deux points d'entrée. Elle exposait auparavant deux copies, une par
adaptateur, qui avaient divergé sur trois points : la CLI n'avait aucune branche
d'erreur, la CLI capturait ses filtres une fois pour toutes, et la veille web passait au
crawl la liste étendue de communes au lieu du filtre de base.

```python
# application/use_cases/watch_filters.py
if now >= deadlines.next_crawl_at:
    outcome = await self._refresh.execute(target, saved)   # crawl + purge
    deadlines.next_crawl_at = now + self._resolve_crawl_interval(target) * SECONDS_PER_MINUTE
if now >= deadlines.next_alert_at:
    notified = await self._notify.execute(target)
    deadlines.next_alert_at = now + self._resolve_alert_interval(target) * SECONDS_PER_MINUTE
```

`run_pass(filter_ids)` fait ce qui est dû maintenant et rend un `WatchReport` par
filtre ; `run_forever` boucle dessus, dort jusqu'à `compute_seconds_until_next_deadline()` et
temporise `ERROR_BACKOFF_SECONDS` si une passe lève. Les adaptateurs n'y ajoutent que
l'affichage — `console.print` en CLI, `logger.info` sur le web.

Les filtres sont **relus à chaque passe** : modifier une cadence prend effet dès
l'échéance suivante, sans redémarrer la veille. Une échéance déjà posée n'est pas
rembobinée — raccourcir la cadence s'applique au prochain tour, pas rétroactivement.

L'horloge est un port (`ClockPort`), ce qui rend la politique testable :
`tests/application/test_watch_filters.py` joue une après-midi de veille sans dormir.

En CLI, `--refresh` et `--interval` remplacent respectivement la cadence de crawl et
la cadence d'alerte, pour tous les filtres surveillés.

---

## Concurrence des crawlers

Dans chaque cycle, tous les crawlers d'une source tournent en parallèle grâce à `asyncio.gather` + `Semaphore` :

```python
class CrawlAllSources:
    def __init__(self, crawlers, repository, max_concurrent=5):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, filter):
        tasks = [self._crawl_one(c, filter) for c in self._crawlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ...

    async def _crawl_one(self, crawler, filter):
        async with self._semaphore:     # max 5 simultanés
            return await crawler.fetch(filter)
```

**Avantage :** avec semaphore(5), le temps total ≈ max(durée d'un crawler) et non Σ(durées).

---

## Temps d'exécution typique d'un cycle

Pour **une ville** (le crawl réel étend aux communes du rayon → multiplié par le nombre de communes) :

| Étape | Durée estimée |
|-------|--------------|
| Crawl PAP | 1–2s |
| Crawl Orpi / Foncia / ParuVendu / Century21 (curl_cffi) | 1–3s chacun |
| Enrichissement DPE/GES (pages détail) | ~RATE_LIMIT par annonce, **mis en cache 24h** |
| Save to SQLite | < 50ms |
| Matching en mémoire | < 5ms |
| Notification | < 500ms |
| **Cycle complet** | **~6–10s** |

Un intervalle de 15min laisse donc largement le temps à un cycle de se terminer avant le prochain.

---

## Gestion des interruptions

`KeyboardInterrupt` est capturé proprement :

```python
try:
    while True:
        ...
        await asyncio.sleep(interval)
except KeyboardInterrupt:
    console.print("\n[yellow]Stopped.[/]")
finally:
    await container.close()   # ferme DB + crawlers
```

Les connexions DB et clients HTTP sont toujours fermées proprement.

---

## Plusieurs filtres simultanés

Tous les filtres actifs sont vérifiés à chaque cycle. Chaque filtre a sa propre table de notifications (via `filter_id`) — les vues sont indépendantes.

```
Cycle #1:
    filtre "Paris meublé"    → 3 nouvelles annonces → notifiées → marquées
    filtre "Lyon studio"     → 1 nouvelle annonce   → notifiée  → marquée

Cycle #2:
    filtre "Paris meublé"    → 0 nouvelle → rien
    filtre "Lyon studio"     → 2 nouvelles → notifiées → marquées
```

---

## Mode one-shot vs watch

| | `hunt search` | `hunt watch` |
|--|---------------|-------------|
| Boucle | Non — une seule passe | Oui — infini |
| Notification | Non | Oui — terminal + badge web |
| Déduplication | Non | Oui — via table notifications |
| Usage | Vérification manuelle | Surveillance continue |
| Process | Se termine | Reste actif |

---

## Lancer en arrière-plan (daemon)

Pour lancer `hunt watch` sans garder le terminal ouvert :

```bash
# Avec nohup
nohup hunt watch > ~/apartment-hunter.log 2>&1 &
echo $! > ~/apartment-hunter.pid

# Arrêter
kill $(cat ~/apartment-hunter.pid)
```

Avec `launchd` (macOS, relance automatique au démarrage) :

```xml
<!-- ~/Library/LaunchAgents/com.apartment-hunter.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.apartment-hunter</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/venv/bin/hunt</string>
    <string>watch</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/apartment-hunter.log</string>
  <key>WorkingDirectory</key>
  <string>/Users/toi/Documents/projects/apartment-hunter</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.apartment-hunter.plist
```
