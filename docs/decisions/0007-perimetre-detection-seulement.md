# ADR-0007 — L'application détecte et affiche ; elle ne suit pas une candidature

**Statut** : acceptée, en vigueur — 2026-08-04 ; partiellement remplacée par
l'[ADR-0009](0009-le-chasseur-ecarte-un-logement.md) le 2026-09-25 (le chasseur peut
écarter un logement ; le suivi de candidature reste exclu)

## Contexte

Chercher un logement est un tunnel : repérer, contacter, visiter, envoyer un dossier,
signer un bail. Un outil de chasse invite naturellement à modéliser ce tunnel
(statuts, relances, pièces du dossier, garant, Visale).

L'application n'en connaît rien : elle crawle, filtre, affiche, alerte, purge. Le
produit revendique la vitesse de rejet comme acte principal — repérer les deux ou
trois annonces neuves parmi vingt-cinq et écarter le reste en moins d'une seconde.

## Décision

Le périmètre s'arrête à la **détection** et à l'**affichage**. Le suivi de candidature
se fait ailleurs (mail, notes), pas ici.

N'entrent ni au modèle, ni à l'interface, ni au vocabulaire : dossier de location,
garant, Visale, caution, visite, relance, bail, préavis, état des lieux, statut de
candidature.

**Seule exception** : l'horodatage d'ouverture d'une annonce, introduit par
l'[ADR-0002](0002-nouveau-signifie-pas-encore-ouverte.md) pour éteindre le badge
« Nouvelle ». Ce n'est pas un statut de candidature — c'est la mémoire d'un regard,
et il n'y a aucun geste de gestion à faire pour l'alimenter.

Deux catégories de biens sont écartées avant affichage, parce qu'elles faussent la
comparaison des loyers :

- **colocation / chambre chez l'habitant** — ce n'est pas un logement entier ;
- **bail mobilité / location saisonnière** — 1 à 10 mois, hors sujet.

Les **maisons** restent recevables, malgré le nom `Listing`.

## Conséquences

- Pas de table de statuts, pas de champ « écarté », pas de favoris. Une annonce
  inintéressante est écartée par le filtre ou par l'œil, pas par un clic.
- Une annonce qui ne correspond plus est supprimée (hors critères ou retirée) plutôt
  que conservée dans un état intermédiaire. Cohérent avec le comportement actuel de la
  purge.
- L'exclusion colocation / bail mobilité demande une détection (mots-clés, type de
  bien annoncé). Elle doit être conservatrice : en cas de doute, afficher.
- Si le besoin de suivi apparaît un jour, ce sera une décision qui remplace celle-ci,
  pas un ajout discret de champ.
