# Notifications

Deux canaux, sans config : **terminal** (mode `watch`/`search`) et **signal in-app** (badge « Nouveau » de l'interface web). Aucun email, aucune notification push OS.

---

## Terminal

`TerminalNotifier` imprime un bloc clair quand de nouvelles annonces correspondent à un filtre :

```
🔔 3 nouvelles annonces · Annecy centre
  • Appartement 3p 65m² · 65m² · 3p · 1 210 € CC · DPE C · GES B · paru 30/10/2026 · −12 % vs réf.
    https://www.pap.fr/annonces/...
  • Appartement 2p 48m² · 48m² · 2p · 780 € · charges non communiquées · vu 31/10/2026 · pas de repère (charges inconnues)
    https://...
  … +1 de plus
  Estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin
```

Chaque ligne finit par la **position au marché** (même libellé que `hunt review`, voir
*Position au marché* dans le glossaire), ou par « pas de repère (raison) ». La ligne de
résumé vient du domaine (`Listing.build_summary_line`), qui ne connaît pas la Carte des
loyers : `NotifyNewListings` pose la position, `format_alert_line` assemble les deux. La
mention de source ANIL ferme le bloc (licence).

Le titre, l'URL et le nom du filtre passent par `rich.markup.escape` : un titre comme
`[link=…]Offre[/link]` s'affiche tel quel au lieu d'être lu comme du balisage
(`tests/infrastructure/test_notification_escaping.py`).

C'est le notifieur par défaut (et unique) câblé dans `build_notifiers`.

---

## Signal in-app (web)

Dans l'interface web (`hunt serve`), les annonces récentes portent un badge **« Nouveau »**. C'est le canal visuel — pas de cloche à configurer, le badge apparaît automatiquement sur les cartes fraîchement ajoutées.

---

## Pipeline de notification

```
NotifyNewListings
      │
      ▼
CompositeNotifier
  └── TerminalNotifier  → bloc stdout
```

`CompositeNotifier` orchestre la liste des notifieurs ; les échecs sont loggés sans bloquer.

### Garantie « une seule fois »

Une annonce notifiée est marquée dans la table `notifications` (clé composite `apartment_id + filter_id`). Elle ne sera **jamais** renotifiée pour ce filtre, même après redémarrage.

> Pour revoir toutes les annonces depuis le début : supprimer et recréer le filtre (nouvel ID = nouvelle table de notifications).

---

## Email / push OS — retirés

Les notifieurs email (`aiosmtplib`), desktop (`plyer`) et macOS (`osascript`) ont été retirés : trop de bruit pour un outil local. Les nouvelles annonces se voient dans le terminal et dans l'interface web. Aucune variable `SMTP_*` / `NOTIFY_EMAIL` n'est nécessaire.

---

## Logs

```
07:42:13 | INFO | Notified 3 new listings for filter 'Annecy meublé'
```

Niveau configurable via `LOG_LEVEL=DEBUG`.
