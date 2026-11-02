# ADR-0002 — « Nouvelle » signifie « pas encore ouverte par le chasseur »

**Statut** : acceptée, en vigueur — 2026-08-04 ; partiellement remplacée par
l'[ADR-0009](0009-le-chasseur-ecarte-un-logement.md) le 2026-09-25 (l'ouverture se
souvient du logement, plus de l'annonce ; le sens de « Nouvelle » ne change pas)

## Contexte

Le mot « nouveau » recouvre trois choses différentes dans le code :

| Notion | Mesure |
|--------|--------|
| `CrawlOutcome.new_count` | L'URL n'était pas en base avant ce crawl |
| `find_new_since(filter_id)` | Pas encore alertée pour ce filtre |
| `published_at` récent | Fraîcheur côté source |

Aucune ne correspond à ce que le badge de l'interface doit dire. Scénario de
référence : une annonce parue samedi sur PAP, découverte par le crawl lundi 9 h. Le
badge doit être allumé lundi 14 h, éteint mardi 9 h — donc il dépend du regard du
chasseur, pas du crawl ni de la source.

Marquer « vue » au simple défilement de la liste est trop agressif : l'usage est de
survoler quinze secondes entre deux tâches, une carte croisée du coin de l'œil n'est
pas une annonce examinée.

## Décision

**Nouvelle** = le chasseur n'a pas encore ouvert l'annonce vers sa source.

Le badge s'éteint au **clic vers la source**, pas à l'affichage de la carte.

Cet état est enregistré côté application (horodatage d'ouverture par annonce). C'est
la seule écriture déclenchée par le chasseur — voir
[ADR-0007](0007-perimetre-detection-seulement.md), qui interdit tout autre suivi.

Les trois notions existantes gardent leur sens mais changent de nom au fil des
touchers : **découverte**, **non alertée**, **récente**.

## Conséquences

- Une colonne d'ouverture apparaît : `listings.opened_at`, exposée au domaine par le
  booléen `Listing.opened` (la date répond à « quand », le domaine ne demande que
  « déjà ? »). Non liée au filtre — une annonce ouverte l'est pour de bon, quel que
  soit le filtre qui l'a fait remonter, et seule la première ouverture est horodatée.
- L'application n'est plus strictement en lecture seule, mais le chasseur n'a aucun
  geste de gestion à faire : ouvrir l'annonce est déjà ce qu'il ferait.
- Le badge devient stable dans le temps : rouvrir l'app le lendemain ne rallume rien.
- Une annonce jamais ouverte reste « nouvelle » indéfiniment. Acceptable : la purge la
  supprimera quand la source la retirera.
- L'alerte (`mark_notified`) reste distincte du badge. Recevoir une alerte n'éteint pas
  le badge.
