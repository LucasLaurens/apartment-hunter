# Spec — Décider au lieu de lister

Status: ready-for-agent

Issue de la map [Décider au lieu de lister](map.md) (6 tickets résolus). Tickets d'implémentation : `.scratch/decider-au-lieu-de-lister/issues/` (01 à 08). Décisions de fond :
[ADR-0009](../../docs/decisions/0009-le-chasseur-ecarte-un-logement.md) (écarter un logement),
[ADR-0010](../../docs/decisions/0010-position-au-marche-contre-la-carte-des-loyers.md) (position au marché).
Vocabulaire : `docs/functional/glossaire.md` — *logement*, *annonce*, *doublon*, *écarté*, *raison d'écart*,
*suggestion de critère*, *ouverte*, *loyer de référence*, *position au marché*, *charges inconnues*.

## Problem Statement

Le chasseur reçoit chaque soir la liste des logements qui passent son filtre, mais la liste ne l'aide pas à
choisir. Elle ne dit pas si un loyer est bas pour la commune : trier par prix classe seulement ce qu'il accepte
déjà. Elle lui remontre aussi, soir après soir, les logements qu'il a déjà refusés, et le même logement revient
par un autre site ou sous une nouvelle URL. Même le badge *Nouvelle* se rallume quand une annonce déjà lue est
republiée. Enfin, ce que ses refus disent de ses goûts (« je refuse tous les rez-de-chaussée ») ne remonte
jamais jusqu'à son filtre.

## Solution

Une commande terminal, `hunt review`, pour passer les logements d'un filtre en revue. Une liste courte à gauche,
le détail du logement sélectionné à droite. Chaque logement porte sa **position au marché** (« −12 % vs réf. »),
calculée contre le loyer de référence public de sa commune (Carte des loyers, ANIL). La liste est triée de la
position la plus basse à la plus haute, les logements qu'on ne peut pas comparer en dernier.

D'une touche, le chasseur **écarte** un logement avec une raison. Le logement disparaît partout (revue, page
web, alerte) et ne revient ni par un doublon ni par une republication. Il peut le **restaurer**. Quand trois
écarts ont la même raison, l'application **suggère** le critère de filtre correspondant, avec une valeur
prudente et l'impact de la modification, sans jamais l'appliquer seule. *Ouverte* se souvient désormais du
logement : ouvrir une annonce ouvre ses doublons.

L'alerte (le bloc imprimé par le mode `watch` dans le terminal ; l'application n'envoie aucun email) porte aussi la position au marché. La page web est gelée : elle masque les logements écartés,
sans rien gagner d'autre.

## User Stories

### Revue

1. En tant que chasseur, je veux lancer `hunt review` sur un filtre enregistré, pour passer ses logements en revue depuis le terminal.
2. En tant que chasseur, je veux une liste courte à gauche (position au marché, total CC, commune, marque de mention), pour parcourir d'un coup d'œil.
3. En tant que chasseur, je veux le détail du logement sélectionné dans un panneau à droite (position, référence, total CC, €/m², taille, étage, DPE, annonceur, source, parution, mentions, lien), pour juger sans ouvrir le site.
4. En tant que chasseur, je veux naviguer avec `j` et `k`, pour aller vite sans souris.
5. En tant que chasseur, je veux ouvrir l'annonce dans mon navigateur avec `o`, pour voir les photos sur le site source.
6. En tant que chasseur, je veux quitter avec `q`.
7. En tant que chasseur, je veux voir en tête le nombre de logements à revoir et le tri en cours, pour savoir où j'en suis.
8. En tant que chasseur, je veux voir un logement par groupe de doublons, avec les autres sources qui le publient, pour ne pas lire trois fois le même logement.
9. En tant que chasseur, je veux que la revue applique le même filtre et les mêmes exclusions que la page web et l'alerte, pour qu'un logement ne soit jamais visible à un endroit et absent d'un autre.
10. En tant que chasseur, je veux voir la liste des touches en pied d'écran, pour ne pas avoir à les retenir.

### Position au marché

11. En tant que chasseur, je veux voir la position au marché de chaque logement (« −12 % vs réf. »), pour savoir si son loyer est bas pour la commune.
12. En tant que chasseur, je veux que la liste soit triée par défaut de la position la plus basse à la plus haute, pour voir d'abord les logements qui valent un appel.
13. En tant que chasseur, je veux que les logements sans repère soient en fin de liste, pour qu'ils ne se mélangent pas aux logements comparés.
14. En tant que chasseur, je veux changer de tri avec `s` (position, €/m², parution), pour regarder la liste sous un autre angle.
15. En tant que chasseur, je veux une marque « hors fourchette » quand le prix au m² sort de l'intervalle de prédiction, pour savoir quand « sous le marché » est vraiment vrai.
16. En tant que chasseur, je veux lire « (repère faible) » quand le producteur lui-même appelle à la prudence (moins de 30 annonces observées dans la commune, ou modèle peu ajusté), pour ne pas surinterpréter.
17. En tant que chasseur, je veux « pas de repère (meublé) » pour une annonce meublée, parce que la référence ne couvre que le non meublé.
18. En tant que chasseur, je veux « pas de repère (charges inconnues) » quand les charges sont inconnues, pour qu'un loyer nu ne passe pas pour une affaire.
19. En tant que chasseur, je veux « pas de repère (sans surface) » pour une annonce sans surface.
20. En tant que chasseur, je veux « pas de repère (commune absente) » quand la commune n'a pas de référence, plutôt qu'un chiffre emprunté à une zone plus large.
21. En tant que chasseur, je veux voir dans le panneau la référence utilisée (segment, commune, valeur, fourchette, millésime, logement type), pour savoir à quoi je compare.
22. En tant que chasseur, je veux que la référence dépende du nombre de pièces (T1-T2, T3+, tous appartements si inconnu), pour comparer un studio à des studios.
23. En tant que chasseur, je veux la mention de la source de la référence en pied d'écran et d'alerte, comme l'exige la licence.
24. En tant que chasseur, je veux que le millésime utilisé soit affiché, parce que deux millésimes ne se comparent pas.
25. En tant que chasseur, je veux que la référence soit téléchargée une fois puis réutilisée, pour que la revue reste rapide et marche sans réseau ensuite.
26. En tant que chasseur, je veux que les anciennes communes fusionnées (Seynod, Cran-Gevrier…) soient rattachées à leur commune nouvelle, pour qu'une annonce « Seynod » ait la référence d'Annecy.
27. En tant que chasseur, je veux trier aussi par €/m² (total CC), pour classer les logements même sans référence.
28. En tant que chasseur, je veux voir la position au marché dans la ligne de chaque logement de l'alerte, pour décider à la réception si j'ouvre ou non.

### Écarter et restaurer

29. En tant que chasseur, je veux écarter le logement sélectionné avec `x`, pour ne plus le voir.
30. En tant que chasseur, je veux choisir la raison d'une touche (`1` trop cher, `2` trop petit, `3` étage, `4` DPE, `5` commune, `6` annonceur, `7` meublé, `8` aspect), pour que l'écart ne me coûte qu'une frappe de plus.
31. En tant que chasseur, je veux `0` pour « autre » avec un texte libre, qui peut rester vide, pour les raisons que la liste n'a pas.
32. En tant que chasseur, je veux que la raison soit obligatoire, pour que mes écarts puissent nourrir les suggestions.
33. En tant que chasseur, je veux qu'un logement écarté disparaisse de la revue, de la page web et de l'alerte, pour ne plus jamais le croiser.
34. En tant que chasseur, je veux qu'un doublon publié plus tard sur un autre site soit écarté aussi, parce que c'est le même logement.
35. En tant que chasseur, je veux qu'une annonce purgée puis republiée reste écartée, pour que la purge n'efface pas mes décisions.
36. En tant que chasseur, je veux qu'une republication sous une nouvelle URL par une autre source reste écartée, parce que le logement n'a pas changé. (Par la même source, elle revient : elle ne se distingue pas du lot identique d'une résidence.)
37. En tant que chasseur, je veux que deux lots identiques publiés par la même source ne soient pas confondus, pour ne pas perdre un vrai logement en en écartant un autre.
38. En tant que chasseur, je veux que l'écart vaille pour tous mes filtres, parce que c'est mon jugement sur un logement, pas sur un filtre.
39. En tant que chasseur, je veux que l'écart n'expire jamais, pour que le bruit ne revienne pas tout seul.
40. En tant que chasseur, je veux basculer avec `d` sur la liste des logements écartés, avec leur raison, pour revenir sur une décision.
41. En tant que chasseur, je veux restaurer un logement écarté avec `u`, pour corriger une erreur.
42. En tant que chasseur, je veux qu'un logement restauré porte « restauré le … », pour savoir que je l'ai déjà jugé une fois.
43. En tant que chasseur, je veux que la raison d'un écart restauré ne compte plus, parce que c'était une erreur.
44. En tant que chasseur, je veux qu'un nouvel écart d'un logement restauré remplace l'ancien, raison comprise, et efface « restauré le … ».
45. En tant que chasseur, je veux qu'un logement écarté dont le loyer change réapparaisse, parce qu'une baisse de loyer est une information nouvelle.
46. En tant que chasseur, je veux que ce logement réapparu porte « écarté le … à N € (raison) », pour savoir ce que j'en pensais et à quel prix.
47. En tant que chasseur, je veux qu'une annonce sans pièces ni surface soit au moins reconnue par son URL, pour qu'elle ne revienne pas au prochain crawl.

### Ouverte

48. En tant que chasseur, je veux qu'ouvrir une annonce marque tout son logement comme *ouvert*, doublons compris, pour que le badge *Nouvelle* ne se rallume pas sur un autre site.
49. En tant que chasseur, je veux qu'une annonce purgée puis republiée reste *ouverte*, pour que la purge n'efface pas ma lecture.
50. En tant que chasseur, je veux lire « ouverte le … » dans la revue, pour savoir que je suis déjà passé dessus.
51. En tant que chasseur, je veux que le clic depuis la page web marque aussi le logement comme *ouvert*, pour que web et terminal disent la même chose.

### Suggestions de critère

52. En tant que chasseur, je veux qu'au 3e écart pour la même raison, l'application me propose le critère de filtre correspondant, pour que mes refus améliorent mon filtre.
53. En tant que chasseur, je veux que les écarts ne se comptent ensemble que s'ils ont la même valeur quand la raison en a une (même commune, même annonceur, même étage), pour qu'une suggestion vise une seule cible.
54. En tant que chasseur, je veux pour « trop cher » un `max_price` à la dizaine sous le plus petit total CC écarté, pour couper juste ce que j'ai refusé.
55. En tant que chasseur, je veux pour « trop petit » un `min_surface_m2` au m² entier au-dessus de la plus grande surface écartée.
56. En tant que chasseur, je veux pour « étage » l'exclusion du rez-de-chaussée ou du premier étage selon les écarts, sans compter les étages inconnus.
57. En tant que chasseur, je veux pour « DPE » le retrait de la lettre écartée et des lettres plus mauvaises.
58. En tant que chasseur, je veux pour « commune » l'exclusion de la commune, et pour « annonceur » l'exclusion de l'annonceur.
59. En tant que chasseur, je veux pour « meublé » le critère inverse de celui des logements écartés.
60. En tant que chasseur, je veux voir combien de logements non écartés la modification masquerait aussi, pour ne pas perdre en silence un logement que je n'ai pas vu.
61. En tant que chasseur, je veux confirmer ou refuser d'une touche (`o`/`N`), et que rien ne soit appliqué sans mon accord.
62. En tant que chasseur, je veux qu'une suggestion acceptée modifie le filtre enregistré, comme le ferait l'édition du filtre.
63. En tant que chasseur, je veux qu'une suggestion refusée ne revienne qu'après 3 nouveaux écarts pour la même raison, pour ne pas être harcelé.
64. En tant que chasseur, je veux que la suggestion vise chaque filtre qui laisse encore passer ces logements.
65. En tant que chasseur, je veux que « aspect » et « autre » ne déclenchent jamais de suggestion, parce qu'aucun critère ne leur correspond.

### Maintenance

66. En tant que mainteneur, je veux une photo figée des champs de décision de chaque logement écarté (total CC, surface, étage, DPE, annonceur, meublé), pour calculer une suggestion même après la purge.
67. En tant que mainteneur, je veux lire les textes « autre » par une simple requête, pour promouvoir à la main une raison qui revient.
68. En tant que mainteneur, je veux que les URL du millésime soient des constantes nommées, pour passer au millésime suivant en changeant une ligne chaque décembre.

## Implementation Decisions

### Domaine

- **Reconnaissance d'un logement** : une seule définition du « même logement », la clé de regroupement de *Doublon* (commune normalisée, pièces, surface arrondie au m², loyer HC), avec la règle « une fois par source ». Une annonce est écartée (ou ouverte) quand elle serait regroupée avec une annonce écartée (ou ouverte) : même clé, et une source différente, ou exactement la même URL. La clé est exposée par le service des doublons pour être partagée, jamais recopiée. Annonce sans pièces ni surface : reconnue par son identifiant (hash d'URL) seulement.
- **Reconnaissance lâche** : même clé sans le loyer (commune, pièces, surface). Sert uniquement à retrouver un écart pour afficher « écarté le … à N € (raison) » sur un logement réapparu après un changement de loyer ; ne masque jamais.
- **Jugement porté sur un logement** : une valeur immuable qui porte la photo figée de l'annonce jugée (clé de regroupement, source, identifiant, total CC, surface, étage, DPE, annonceur, meublé), le moment, et pour un écart la raison et son texte libre. Deux sortes de jugements : l'*ouverture* et l'*écart*. Une restauration efface l'écart mais conserve la date de restauration, qui produit la mention « restauré le … ».
- **Raison d'écart** : enum fermée : trop cher, trop petit, étage, DPE, commune, annonceur, meublé, aspect, autre. Seul « autre » porte un texte libre, éventuellement vide. Le libellé et la touche vivent dans la présentation.
- **Position au marché** : un service pur prend une annonce et un loyer de référence optionnel. Il rend soit une position (pourcentage, hors fourchette ou non, repère faible ou non), soit une absence de repère avec sa raison (meublé, charges inconnues, sans surface, commune absente). La base est le total CC au m², cohérent avec l'ADR-0003. L'ordre de vérification est meublé, charges inconnues, sans surface, puis commune absente.
- **Loyer de référence** : une valeur immuable qui porte le €/m², les bornes basse et haute de l'intervalle, le nombre d'annonces observées dans la commune, le R² ajusté, le segment, le millésime et le libellé de commune. « Repère faible » quand il y a moins de 30 annonces observées ou un R² < 0,5 : ces deux seuils sont des constantes nommées.
- **Segment** : 1-2 pièces → T1-T2, 3+ → T3+, pièces inconnues → tous appartements.
- **Suggestion de critère** : un service pur, qui prend les écarts actifs, les refus, le filtre et les logements non écartés. Il rend zéro ou une suggestion par couple (raison, valeur) : le critère, la nouvelle valeur et l'impact (le nombre de logements non écartés qu'elle masquerait). Le seuil (3) est une constante. Les valeurs suivent les règles des user stories 54 à 59. Le refus est conservé (critère, valeur, date), et le compteur ne reprend qu'à partir des écarts postérieurs au refus.
- **Tri** : on ajoute à l'enum de tri une valeur « position au marché » (qui devient le tri par défaut de la revue) et une valeur « €/m² ». Le tri par parution reste le défaut de la page web.

### Application

- **Cas d'usage de revue** : il prend un filtre, un tri et une vue (à revoir ou écartés). Il rend des entrées de revue, chacune portant un groupe de doublons, sa position au marché (ou son absence de repère) et ses mentions (ouverte le, restauré le, écarté le … à N €). Il réutilise le matcher et le regroupement des doublons, comme `GetTopListings`.
- **Le masquage des écartés est partagé** : `GetTopListings` (page web) et `NotifyNewListings` (alerte) masquent les logements écartés par la même règle. Il n'existe qu'un seul endroit qui dit « ce logement est écarté ».
- **Tri par position** : il se fait en Python, sur l'ensemble des annonces qui correspondent au filtre, **avant** la limite du nombre de résultats, parce que la position dépend du référentiel et ne se calcule pas en SQL. Le tri par €/m², lui, est exprimable en SQL : il suit la règle de parité existante (le SQL et le tri Python doivent rester identiques).
- **Commandes** : écarter (avec raison et texte libre), restaurer, ouvrir. Chacune vise un logement à partir de l'une de ses annonces. « Ouvrir » remplace le cas d'usage actuel d'ouverture par annonce et sert aussi à la page web (même route HTTP, nouveau comportement).
- **Suggestion** : après chaque écart, le cas d'usage d'écart rend la suggestion éventuelle. L'accepter enregistre le filtre modifié par le chemin d'édition des filtres existant, ce qui garantit les mêmes bornes et la même validation. La refuser enregistre le refus.
- **Alerte** : la ligne de chaque logement porte la position au marché ou « pas de repère », et la fin du bloc d'alerte porte la mention de source. La position dépend du référentiel, donc elle ne peut pas venir de la ligne de résumé du domaine (`build_summary_line`) seule : c'est l'application qui la compose avec la position calculée.

### Ports et infrastructure

- **Nouveau port « loyer de référence »** : on lui demande la référence pour un code INSEE et un segment, il rend une référence ou rien. L'adaptateur lit les CSV de la Carte des loyers : trois fichiers appartements (tous, T1-T2, T3+), le fichier maisons n'étant pas utilisé. Il les télécharge à la première utilisation vers un cache local nommé par millésime, puis les relit sans réseau. Lecture en cp1252, séparateur `;`, virgule décimale, code INSEE lu en chaîne. URL et millésime sont des constantes. Colonnes utilisées : `INSEE_C`, `loypredm2`, `lwr.IPm2`, `upr.IPm2`, `nbobs_com`, `R2_adj`.
- **Code INSEE** : le géocodage fournit, en plus des coordonnées, le code INSEE de chaque commune du rayon. Il suffit d'ajouter `code` aux champs demandés dans l'appel geo.api.gouv.fr déjà fait par département : zéro requête en plus, même cache de 24 h. Les communes déléguées ou associées sont rattachées à leur chef-lieu par un appel par département à l'endpoint des communes associées et déléguées. Nominatim n'est pas utilisé pour cela. Un code postal seul ne suffit jamais à trouver un code INSEE.
- **Persistance des jugements** : une table dédiée, hors de la table des annonces, que la purge (`delete_many`) ne touche pas. Elle porte la photo figée, la sorte de jugement, la raison, le texte libre, les dates d'écart, d'ouverture et de restauration. Une seconde table conserve les refus de suggestion. L'accès passe par le port du dépôt d'annonces (qui porte déjà les filtres et l'ouverture), avec des méthodes pour enregistrer un écart, restaurer, enregistrer une ouverture, lister les jugements, enregistrer et lister les refus. La colonne `opened_at` existante est migrée en jugements d'ouverture, puis cesse d'être la source de vérité.
- **Page web** : aucune fonctionnalité nouvelle. Elle masque les écartés et ouvre au niveau du logement, par les mêmes cas d'usage.

### Présentation (terminal)

- **Commande `hunt review`**, avec l'option `--filter <nom>` et l'option `--dismissed` pour ouvrir directement la vue des écartés. Rendu avec Rich (déjà installé), lecture des touches en mode brut via la bibliothèque standard. Pas de Textual.
- **Disposition retenue par le prototype** (variante C, branche `prototype/hunt-review`) : une grille à deux colonnes de largeurs 2 et 3. À gauche, la liste : curseur, position, total, commune tronquée, marque « • » quand il y a une mention. À droite, un panneau titré « commune · taille » avec, dans l'ordre : Position, Référence, Total, €/m², Taille, Étage, DPE, Annonceur, Source, Paru / vu, Mentions, Lien. En pied : les touches, puis la mention de source.
- **Touches** : `j` et `k` pour naviguer, `o` pour ouvrir, `x` pour écarter (puis `1`-`8` ou `0`), `d` pour basculer entre à revoir et écartés, `u` pour restaurer (dans la vue des écartés), `s` pour changer de tri, `q` pour quitter. La question de suggestion se pose en `[o/N]` juste après l'écart qui atteint le seuil. Une touche invalide au choix de la raison annule l'écart.
- **Libellés** : « −12 % vs réf. », « hors fourchette », « (repère faible) », « pas de repère (raison) », « ouverte le … », « restauré le … », « écarté le … à N € (raison) ». Jamais « prix du marché », jamais « écart » pour parler de la position.

## Testing Decisions

- **Ce qu'est un bon test** : il vérifie un comportement visible de l'extérieur (ce que la revue montre, masque ou suggère), jamais la structure interne. Pas de mocks : des fakes concrets en mémoire, une structure `# Arrange / # Act / # Assert`, des données générées avec Faker.
- **Point de test principal : les cas d'usage**, avec `InMemoryListingRepository` (étendu aux jugements et aux refus), `InMemoryGeocoding` (étendu au code INSEE) et un nouveau `InMemoryRentReference`. Scénarios à couvrir :
  - écarter, purger, republier (même URL, nouvelle URL, autre source) : le logement reste masqué ;
  - deux lots identiques d'une même source : en écarter un ne masque pas l'autre ;
  - loyer modifié : le logement réapparaît avec la mention d'écart ;
  - restaurer, puis réécarter ;
  - ouvrir une annonce ouvre son doublon, et l'ouverture survit à la purge ;
  - chaque cas « pas de repère », « hors fourchette », « repère faible » ;
  - ordre par position, avec les logements sans repère en fin, et la limite de résultats appliquée après le tri ;
  - suggestion au 3e écart : valeur, impact, refus, puis retour après 3 nouveaux écarts ; aucune suggestion pour « aspect » ou « autre » ;
  - masquage des écartés dans `GetTopListings` et dans l'alerte ;
  - position au marché dans l'alerte (`InMemoryNotifier`).

  Précédents à suivre : les tests des cas d'usage `GetTopListings`, `PurgeStaleListings` et `NotifyNewListings`.
- **Adaptateur SQLite** : les jugements survivent à `delete_many`, et la migration de `opened_at` produit des jugements d'ouverture. Précédents : les tests SQLite de l'ouverture et de la parité de tri. Le tri €/m² entre dans le test de parité SQL/Python.
- **Adaptateur Carte des loyers** : il lit un petit fichier d'exemple commité (cp1252, virgule décimale, un code INSEE à zéro de tête), avec un cache déjà rempli, sans aucun appel réseau.
- **Géocodage** : le code INSEE et le rattachement des communes déléguées se testent sans réseau, en amorçant les données comme le font les tests existants de `geo_postal` (un code amorcé est rendu sans appel).
- **Nommage** : les nouvelles fonctions passent le test existant qui impose un verbe en tête des noms.
- **Pas de test automatique pour l'écran terminal** : on le vérifie en le faisant tourner sur la vraie base, et en regardant le rendu.

## Out of Scope

- Suivi de candidature (contact, visite, relance, dossier, bail) : l'ADR-0007 reste en vigueur sur ce point.
- Multi-utilisateur, comptes, hébergement ; tout champ « utilisateur ».
- Nouvelles fonctionnalités sur la page web, en dehors du masquage des écartés et de l'ouverture au niveau du logement.
- Score au-delà du prix (DPE, charges, chauffage), et correction de la référence par la surface (les coefficients ne sont pas publiés).
- Référence pour les maisons : le modèle ne distingue pas maison et appartement, et une maison est comparée aux appartements (limite connue).
- Promotion automatique des textes « autre » ; écran de statistiques des raisons.
- Tendance entre millésimes de la Carte des loyers.
- Réparation des crawlers PAP et Orpi, et des fuites de données (colocation « Colocation à louer », annonces d'une source retirée jamais purgées, loyer à 0 €) : tâches séparées.
- Réécriture dans un autre langage.

## Further Notes

- **Documentation dans le même changement**, selon `CLAUDE.md` :
  - `README.md` : la commande `hunt review` ;
  - `docs/technical/data-model.md` : la table des jugements, la table des refus et la migration d'`opened_at` ;
  - `docs/technical/architecture.md` : le nouveau port et l'adaptateur Carte des loyers ;
  - `docs/technical/conventions.md` si de nouveaux verbes entrent dans le test de nommage ;
  - glossaire : les entrées 🚧 (*Écarté*, *Raison d'écart*, *Suggestion de critère*, *Loyer de référence*, *Position au marché*, *Ouverte*) passent en ✅ ;
  - ADR-0009 et ADR-0010 : leur statut passe à « en vigueur » ;
  - ajouter une ligne dans les « Shared Rules » de `CLAUDE.md`, qui disent où vit chaque règle partagée : reconnaissance du logement, position au marché, suggestions.
- **Validation finale** : une fois l'app terminée, lire les 5 logements les plus bas en position sur la collecte réelle « Autour d'Annecy » (lancée le 2026-09-25). Tant que les fuites de données ne sont pas corrigées, elles prennent la tête du tri : à corriger avant cette lecture.
- **Un tiers des logements actuels n'a pas de surface**, et l'étage est inconnu partout. La position et la raison « étage » seront souvent absentes tant que les crawlers ne collectent pas mieux ces champs.
- **Prototype** : branche `prototype/hunt-review`. À relire pour la disposition, jamais à fusionner : il a été écrit sans tests et reste jetable.
