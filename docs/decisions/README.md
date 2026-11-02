# Décisions d'architecture (ADR)

Une décision par fichier, numérotée, jamais réécrite : si une décision change, on en
ajoute une nouvelle qui remplace l'ancienne et on marque l'ancienne « Remplacée ».

Le vocabulaire employé ici est défini dans le [glossaire](../functional/glossaire.md).

| # | Décision | Statut |
|---|----------|--------|
| [0001](0001-annonce-est-l-unite-stockee.md) | L'annonce est l'unité stockée ; les doublons sont regroupés à l'affichage | Acceptée, en vigueur |
| [0002](0002-nouveau-signifie-pas-encore-ouverte.md) | « Nouvelle » signifie « pas encore ouverte par le chasseur » | Acceptée, partiellement remplacée par 0009 |
| [0003](0003-budget-en-charges-comprises.md) | Le budget se raisonne en charges comprises ; les charges inconnues sont signalées, jamais estimées | Acceptée, en vigueur |
| [0004](0004-passoire-thermique-notion-du-domaine.md) | « Passoire thermique » est une notion du domaine ; avertir, ne jamais masquer | Acceptée, en vigueur |
| [0005](0005-deux-cadences-crawl-et-alerte.md) | Deux cadences distinctes : crawl et alerte | Acceptée, déjà en vigueur |
| [0006](0006-source-annonceur-enseigne.md) | Source, annonceur et enseigne sont trois notions séparées | Acceptée, en vigueur |
| [0007](0007-perimetre-detection-seulement.md) | L'application détecte et affiche ; elle ne suit pas une candidature | Acceptée, partiellement remplacée par 0009 |
| [0008](0008-cadence-de-crawl-fenetre-partagee.md) | La cadence de crawl est une fenêtre partagée, pas un délai en série | Acceptée, en vigueur |
| [0009](0009-le-chasseur-ecarte-un-logement.md) | Le chasseur peut écarter un logement ; écart et ouverture se souviennent du logement | En vigueur |
| [0010](0010-position-au-marche-contre-la-carte-des-loyers.md) | La position au marché se mesure contre la Carte des loyers, jamais contre nos annonces | En vigueur |
| [0011](0011-le-theme-est-un-choix-du-chasseur.md) | Le thème est un choix du chasseur : Clair, Sombre ou Système, une seule liste de couleurs | Acceptée, implémentée |

## Format

Contexte (le problème observé) → Décision (une phrase à l'impératif) → Conséquences
(ce que ça coûte, ce que ça interdit). Pas de section « alternatives » pour le plaisir :
seules les options réellement pesées sont citées.
