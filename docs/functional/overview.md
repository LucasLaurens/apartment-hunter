# Vue d'ensemble fonctionnelle

## Le problème résolu

Les annonces de location disparaissent en quelques heures sur les grandes plateformes. Surveiller manuellement 5 sites toutes les 15 minutes est impossible. Apartment Hunter automatise cette surveillance et t'alerte en premier.

---

## Flux de bout en bout

```
┌─────────────────────────────────────────────────────────────────┐
│  Configuration                                                   │
│  hunt filter add → critères sauvegardés en base                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Crawl (toutes les N minutes)                                   │
│                                                                  │
│  PAP ─────┐                                                      │
│  Orpi ────┤──→ [Annonces] brutes ──→ SQLite (INSERT OR IGNORE)  │
│  Foncia ──┤                              ↑ dédupliqué par URL    │
│  … (8)  ──┘                                                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Matching (en mémoire, pas de requête SQL supplémentaire)       │
│                                                                  │
│  ListingMatcher.matches(listing, filter)                          │
│  ├── prix dans fourchette ?                                      │
│  ├── ville dans rayon géo ? (Haversine + cache 24h)             │
│  ├── ville exclue ?                                              │
│  ├── surface OK ?                                                │
│  ├── étage accepté ? (RDC, 1er, dernier)                        │
│  ├── DPE dans set accepté ?                                      │
│  ├── meublé/non meublé ?                                         │
│  └── charges, chauffage, photos...                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Résultat                                                        │
│                                                                  │
│  hunt search  → affichage tableau Rich (top 10)                 │
│  hunt watch   → notification terminal + badge web (nouveaux)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Les deux modes d'utilisation

### Mode `search` — ponctuel

Lance une recherche immédiate sur toutes les sources et affiche les 10 meilleurs résultats dans le terminal. Utile pour tester un filtre ou faire une recherche manuelle.

```bash
hunt search
hunt search --filter "Paris meublé" --limit 20
```

**Ce qu'il se passe :**
1. Récupère le filtre actif (villes étendues aux communes du rayon)
2. Lance les 9 crawlers en parallèle (semaphore de 5 max)
3. Sauvegarde les nouvelles annonces en base (les doublons sont ignorés silencieusement)
4. Filtre les résultats en mémoire selon tes critères
5. Affiche un tableau trié par date de publication décroissante (jusqu'à `max_results`)

> **Affichage web** : au-delà de 25 résultats, la liste est paginée (25 par page). Le
> sélecteur « Trier par » choisit l'ordre (parution, prix, surface) — voir *Tri des résultats*.
>
> **Recherche non-bloquante** : `POST /api/search` lance le crawl en tâche de fond et répond immédiatement (jamais de timeout HTTP). L'interface interroge `/api/search/status` et rafraîchit la liste (lecture DB rapide) au fil du crawl ; les résultats apparaissent au fur et à mesure. Chaque source est plafonnée côté serveur (180 s) pour que le crawl se termine toujours. Si la lecture DB elle-même échoue, l'interface affiche « Aucun appartement disponible pour le moment ».

### Mode `watch` — surveillance continue

Tourne en arrière-plan et signale chaque nouvelle annonce (terminal + badge web). Ne resignale jamais une annonce déjà vue.

```bash
hunt watch
hunt watch --interval 10  # toutes les 10 minutes
```

**Ce qu'il se passe en boucle :**
1. Crawl toutes les sources
2. Récupère les annonces **pas encore notifiées** pour ce filtre
3. Les filtre selon tes critères
4. Affiche un bloc terminal si correspondances (le badge « Nouveau » apparaît dans l'interface web)
5. Marque ces annonces comme notifiées (table `notifications`)
6. Dort `interval` minutes → recommence

---

## Déduplication

Chaque annonce est identifiée par un hash SHA-256 de son URL (tronqué à 16 chars). Recroiser la même URL au crawl suivant ne crée pas de doublon : l'insertion est silencieusement ignorée via `INSERT OR IGNORE`.

> **La déduplication est exacte, pas sémantique.** Le même logement publié sur SeLoger **et** sur Orpi a deux URLs, donc deux hashs, donc **deux lignes**. C'est voulu : chaque annonce porte son propre loyer, son annonceur et ses honoraires. Le regroupement « même logement » est prévu à l'affichage seulement — voir [ADR-0001](../decisions/0001-annonce-est-l-unite-stockee.md) et le [glossaire](glossaire.md).

---

## Tri des résultats

Par défaut, les annonces sont triées par **date de parution décroissante** — les plus
récentes en premier. La date de publication est extraite depuis la source (pas la date de
crawl). Si la source ne la fournit pas, `datetime.now()` est utilisé comme fallback, et la
carte affiche « vu le … » au lieu de « paru le … ».

Dans l'interface web, le sélecteur **Trier par** au-dessus de la liste propose aussi :

| Choix | Ordre |
|-------|-------|
| Parution — plus récentes | date de parution décroissante (défaut) |
| Prix — moins cher | loyer + charges croissant |
| Prix — plus cher | loyer + charges décroissant |
| Surface — plus grande | surface décroissante, surface inconnue en dernier |

Changer le tri revient à la page 1, et une égalité (même prix, même surface) est départagée
par la parution la plus récente. La CLI, elle, affiche toujours l'ordre par parution.

---

## Géocodage et rayon de recherche

La correspondance par rayon (ex: "Paris ±10km") utilise :
1. **Nominatim** (OpenStreetMap, gratuit) pour convertir un nom de ville en coordonnées GPS
2. **Haversine** (via geopy) pour calculer la distance réelle en km

Les coordonnées géocodées sont **mises en cache 24h** pour éviter de spammer Nominatim. Si une annonce n'a pas de coordonnées, le matching se fait par nom de ville exact.

---

## Gestion des erreurs

- **Crawler en échec** → loggé, les autres crawlers continuent
- **Notifier en échec** → loggé, les autres notifieurs continuent
- **Parse d'annonce raté** → loggé avec extrait HTML pour debug, l'annonce est ignorée
- **Site anti-bot** → 3 tentatives avec backoff exponentiel (2s → 4s → 8s), puis abandon
