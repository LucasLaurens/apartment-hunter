# ADR-0006 — Source, annonceur et enseigne sont trois notions séparées

**Statut** : acceptée, en vigueur — 2026-08-04

## Contexte

Le modèle a deux champs, `source` et `agency`, pour trois réalités :

- **où** l'annonce a été trouvée (`pap`, `seloger`, `orpi`…),
- **qui** la publie (« Laforêt Annecy », ou un particulier),
- **quel réseau** est derrière (Laforêt, Century 21…).

Elles ne coïncident pas : SeLoger peut diffuser une annonce d'une agence Orpi, qui
figure aussi sur le site d'Orpi. Le champ `agency` s'appelle « agence » alors que PAP
ne publie que des particuliers.

`excluded_advertisers` compare déjà par sous-chaîne, précisément parce que l'utilisateur
tape l'enseigne (« Laforêt ») quand le champ contient l'annonceur complet
(« Laforêt Annecy »). Le besoin des trois notions est donc déjà là, contourné.

## Décision

Fixer trois termes distincts, définis au glossaire :

| Terme | Sens | Exemple |
|-------|------|---------|
| **Source** | Le site scrapé | `seloger` |
| **Annonceur** | Qui publie | « Laforêt Annecy », ou « particulier » |
| **Enseigne** | Le réseau | Laforêt |

Ajouter le **type d'annonceur** (`particulier` / `agence`) : **affiché, non filtrant**.
Il change ce que coûte le logement (honoraires de location chez une agence, aucun chez
un particulier) mais ne doit masquer aucune annonce.

## Conséquences

- Le triplet (source, annonceur, enseigne) est ce qui rend le regroupement de doublons
  de l'[ADR-0001](0001-annonce-est-l-unite-stockee.md) crédible : trois sources, même
  annonceur, même loyer, même surface → même logement.
- `Listing.advertiser` remplace `Apartment.agency`, colonne SQL comprise : le
  renommage a touché crawlers, stockage, sérialisation et interface, et une migration
  de renommage garde les bases existantes lisibles.
- Le type d'annonceur se déduit de la source pour les cas fermés (PAP → particulier ;
  les cinq réseaux → agence) et doit être extrait pour les portails mixtes.
- `excluded_advertisers` continue de fonctionner par sous-chaîne sur l'annonceur ; le
  filtre garde son sens, seul le nom du champ visé change.
- Aucun filtre « particuliers uniquement » n'est ajouté. Si le besoin apparaît, ce sera
  une nouvelle décision.
