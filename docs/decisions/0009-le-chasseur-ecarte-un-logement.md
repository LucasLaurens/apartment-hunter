# ADR-0009 — Le chasseur peut écarter un logement ; écart et ouverture se souviennent du logement

**Statut** : en vigueur — acceptée le 2026-09-25, implémentée le 2026-10-31. Remplace en partie
l'[ADR-0007](0007-perimetre-detection-seulement.md) (le champ « écarté ») et
l'[ADR-0002](0002-nouveau-signifie-pas-encore-ouverte.md) (l'unité de l'ouverture).

## Contexte

L'application doit aider à décider, pas seulement lister : montrer l'écart du loyer
au marché et retirer le bruit. Or l'ADR-0007 interdit tout champ « écarté » : une
annonce inintéressante est écartée « par le filtre ou par l'œil ». En pratique, l'œil
revoit chaque soir les mêmes refus, et le filtre ne sait pas dire « celui-là, non ».

Deux trous de mémoire aggravent ce bruit. L'ouverture est horodatée **par annonce**
(`listings.opened_at`), sur la ligne que la purge supprime :

- ouvrir une annonce ne marque pas ses doublons publiés sur d'autres sources ;
- une annonce purgée puis republiée, ou republiée sous une nouvelle URL, revient
  *Nouvelle*.

Un écart stocké de la même façon aurait les mêmes trous : le logement refusé
reviendrait par un autre site.

## Décision

**Le chasseur peut écarter un logement**, avec une raison, et le restaurer. Écarter est
un regard qui conclut « non », de même nature que l'ouverture : ce n'est pas un statut
de candidature. Tout le reste du périmètre de l'ADR-0007 reste en vigueur — ni dossier,
ni visite, ni relance, ni bail.

**Écart et ouverture se souviennent du logement, pas de l'annonce.** Une annonce est
écartée (ou ouverte) quand elle serait regroupée, au sens de *Doublon*, avec une annonce
écartée (ou ouverte). Les éléments qui fondent le regroupement (commune repliée, pièces,
surface arrondie, loyer, source) sont conservés hors de la ligne d'annonce, pour survivre à la
purge. Une seule définition du « même logement » : `domain/services/duplicates.py`.

## Conséquences

- L'annonce reste l'unité stockée ([ADR-0001](0001-annonce-est-l-unite-stockee.md)) ;
  s'y ajoute une mémoire des jugements portés sur des logements, que la purge ne touche
  pas.
- Une annonce sans pièces ni surface n'est jamais regroupée : elle n'est reconnue que par
  son URL, et une republication sous une nouvelle URL revient.
- Un changement de loyer casse la reconnaissance : le logement réapparaît. C'est voulu,
  une baisse de loyer est une information. Il porte alors la mention « écarté le … à
  N € (raison) », retrouvée par une comparaison sans le loyer qui sert à **afficher,
  jamais à masquer** : une erreur coûte une mention fausse, pas un logement manqué.
- Écarter est global (non lié au filtre) et sans expiration. Restaurer laisse la trace
  « restauré le … » et retire la raison des statistiques ; un nouvel écart remplace
  l'ancien.
- Un logement écarté est masqué partout : revue, page web, alerte.
- Dans l'ADR-0007, le verbe « écarter » pour la colocation et le bail mobilité désignait
  une exclusion automatique ; ce mot est désormais réservé au geste du chasseur.
