# Modèle de « écarté »

Type: grilling
Status: resolved
Blocked by:

## Question

Comment l'état « écarté » est-il modélisé pour survivre à la purge et couvrir les doublons ?

- Clé : l'annonce (`listing_id`, hash d'URL) ou le groupe de doublons ? Que se passe-t-il quand un nouveau doublon d'un logement écarté arrive d'un autre site ?
- Stockage : table dédiée, non touchée par `delete_many` (`sqlite_repository.py`).
- Restauration : `hunt review --dismissed` + touche `u` ; qu'est-ce qui est conservé (raison, date) ?
- Une annonce republiée sous une nouvelle URL est-elle reconnue comme déjà écartée ?
- Terme et définition à ajouter à `docs/functional/glossaire.md`.

## Answer

Décision consignée dans [ADR-0009](../../../docs/decisions/0009-le-chasseur-ecarte-un-logement.md), qui remplace en partie l'ADR-0007 (le champ « écarté » était interdit) et l'ADR-0002 (unité de l'ouverture). Termes *Écarté* et *Ouverte* mis à jour dans `docs/functional/glossaire.md`.

| Sujet | Décision |
|---|---|
| Unité | On écarte un **logement**, reconnu par la règle *Doublon* (commune, pièces, surface arrondie, loyer, source différente). Les éléments sont conservés hors de la ligne d'annonce pour survivre à la purge. Sans pièces ni surface : reconnu par l'URL seulement |
| Portée | Globale, jamais liée à un filtre |
| Durée | Pas d'expiration |
| Restauration | Trace « restauré le … » ; la raison sort des statistiques ; un nouvel écart remplace l'ancien |
| « Déjà vu » | = *Ouverte* (touche `o`) ; « vu le … » reste la première détection |
| *Ouverte* | Passe au niveau du logement, même mécanisme, survit à la purge |
| Loyer modifié | Le logement réapparaît avec « écarté le … à N € (raison) » ; retrouvé par une comparaison sans le loyer, qui affiche et ne masque jamais |
| Visibilité | Masqué partout : revue, web, alerte |
