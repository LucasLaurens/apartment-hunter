# ADR-0003 — Le budget se raisonne en charges comprises, les charges inconnues sont signalées

**Statut** : acceptée, en vigueur — 2026-08-04

## Contexte

Les sources publient tantôt un loyer hors charges, tantôt charges comprises, et
n'indiquent pas toujours laquelle. `Price.total` vaut `amount + charges`, avec
`charges` optionnel : quand la source ne publie pas de provision, le total **est** le
loyer nu.

Conséquence : une annonce à 800 € HC sans charges publiées passe un filtre « max
850 € » alors qu'elle coûtera environ 900 € par mois. Le filtre ment, sans le dire.

Compléter par une provision estimée (au m², ou forfaitaire) rendrait les comparaisons
homogènes — au prix d'un chiffre inventé affiché comme un chiffre relevé.

## Décision

Le budget est **le coût mensuel total** : le filtre prix compare `Price.total`. C'est
déjà le comportement.

Quand la source ne publie pas de provision, l'annonce **reste affichée et reste
filtrable**, mais porte la mention « charges non communiquées ». Le total affiché ne
doit pas ressembler à un total certain.

**Aucune estimation de charges.** Un montant que personne n'a publié n'entre pas dans
le modèle.

## Conséquences

- `Price.has_charges` existe déjà et distingue les deux cas : rien à ajouter au domaine.
- La restitution doit changer : carte web, tableau CLI et alerte doivent tous marquer
  l'incertitude. Un seul des trois qui l'oublie et le piège revient.
- Un filtre prix serré laissera passer des annonces qui le dépassent réellement. C'est
  assumé : mieux vaut une annonce à écarter d'un coup d'œil qu'une bonne annonce
  masquée par une estimation fausse.
- Les honoraires de location (paiement unique à la signature) restent hors du filtre
  prix, qui est mensuel.
