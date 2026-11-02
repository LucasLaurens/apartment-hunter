# Map — Décider au lieu de lister

Label: wayfinder:map

## Destination

Une spec prête à implémenter pour faire passer l'app de « liste d'annonces » à « aide à la décision » : la position au marché (total CC au m² comparé au loyer de référence), et un état « écarté + raison » qui retire le bruit, le tout piloté depuis le terminal (`hunt review`).

## Notes

Cadre verrouillé au chartage (2026-09-25), à respecter par chaque session :

- **Projet dormant** : pas de recherche en cours. Refonte autorisée, mais rien n'est validé par l'usage ; d'où le ticket de collecte réelle.
- **Mono-utilisateur, local** (SQLite, `.env`). Pas de `user_id` ni de compte « pour plus tard ».
- **Surfaces** : toute nouveauté va dans le terminal (`hunt review`) ; page web gelée (bugs seulement, pas supprimée) ; alerte terminal (`hunt watch`) = déclencheur, aucun email ; l'API JSON existante (`/api/listings`) reste.
- **Python conservé** : goulot = réseau et `RATE_LIMIT_SECONDS`, pas le CPU ; SeLoger dépend de `playwright-stealth`, sans équivalent Go.
- **Score en deux marches** : (1) tri par €/m² dans `ListingSort` ; (2) position au marché contre la Carte des loyers (data.gouv.fr). Pas de médiane de la base : elle est déjà filtrée par budget, effacée par la purge (`DELETE FROM listings`), et trop petite.
- **« Écarté »** ([ADR-0009](../../docs/decisions/0009-le-chasseur-ecarte-un-logement.md)) : masqué partout (review, web, alerte), pour tout le groupe de doublons (`duplicates.py`), annulable (`hunt review --dismissed`, touche `u`). Doit survivre à la purge.
- **Raisons** : liste fermée + « autre » en texte libre ; une raison qui recoupe un critère du filtre finit par suggérer ce critère.
- **Validation** : test de persistance de « écarté » livré avec son code ; collecte réelle via `hunt watch` sur « Autour d'Annecy » dès maintenant ; lecture des 5 annonces les plus sous-cotées une fois l'app terminée.
- Skills à appeler pour les tickets grilling : `grilling` + `domain-modeling`. Règles du projet : `CLAUDE.md` (couches, nommage verbe, docs dans le même commit).

## Decisions so far

<!-- une ligne par ticket résolu : gist + lien -->

- [Carte des loyers : le référentiel est-il utilisable ?](issues/01-carte-des-loyers.md) : oui, millésime 2025, charges comprises, non meublé, clé INSEE via geo.api.gouv.fr déjà appelé ; 4 communes couvertes
- [Modèle de « écarté »](issues/02-modele-ecarte.md) : on écarte un logement, reconnu par la règle Doublon et conservé hors purge ; global, sans expiration, « restauré le … » ; *Ouverte* passe au niveau du logement ; ADR-0009 remplace en partie 0007 et 0002
- [Liste des raisons d'écart](issues/03-raisons-ecart.md) : 8 raisons + autre, obligatoire ; 3 écarts même raison → suggestion de critère avec valeur prudente et impact, jamais appliquée seule ; photo figée des champs de décision
- [Affichage de la position au marché](issues/05-position-au-marche.md) : « −12 % vs réf. », « hors fourchette » seulement hors intervalle, « (repère faible) » écrit, « pas de repère » pour meublé / charges inconnues / sans surface ; alerte oui, web non ; « écart » réservé au geste
- [UX de `hunt review`](issues/04-ux-hunt-review.md) : variante C « liste + panneau », tri par position (« pas de repère » en fin), Rich sans Textual ; prototype sur `prototype/hunt-review` ; fuites de données repérées (colocation, source retirée, 0 €)
- [Démarrer la collecte réelle sur Annecy](issues/06-collecte-reelle-annecy.md) : `hunt watch` tourne depuis le 2026-09-25 sur « Autour d'Annecy » ; PAP et Orpi en échec, collecte partielle

Spec issue de la map : [spec.md](spec.md) (`ready-for-agent`).

## Not yet specified

- **Score au-delà du prix** : DPE, charges, chauffage pèsent dans la décision, mais une partie de ces champs n'est pas encore collectée (chantier crawler). À rouvrir quand ces champs existent.
- **Sort de la page web** : la supprimer ou la garder, à trancher après usage réel de `hunt review`.

## Out of scope

- Multi-utilisateur, comptes, hébergement : autre effort, pas une suite.
- Cycle de vie complet de l'annonce (contactée, relancée, visitée) : c'est un CRM.
- Réécriture dans un autre langage.
