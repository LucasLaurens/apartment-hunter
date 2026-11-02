# Audit de l'existant

Type: task
Status: resolved
Blocked by: 01

## Question

Que valent aujourd'hui la page web et `hunt review`, mesurés contre `PRODUCT.md`, `DESIGN.md` et ui-ux-craft ?

- **Web** : passes 0, 4a, 4b, 4c et 5 de `ui-ux-craft` (`measure.mjs` à 1280 / 1440 / 390, plus `make ui-check`), captures regardées, pas seulement comptées.
- **`hunt review`** : passe 4a adaptée au terminal (hiérarchie, une action dominante, retour sur chaque attente, erreurs qui nomment la correction).
- **Données** : une copie de la vraie base, plus un jeu semé avec Faker pour les états rares : charges inconnues, sans DPE, quatre doublons, titre très long, sans photo, date estimée (« vu le »).

Rendu : une liste de constats, chacun avec son `file:line`, la règle qu'il enfreint, et la gravité pour le travail de rejet rapide. Pas de correction : les constats nourrissent les tickets suivants.

## Answer

Audit du 2026-10-29 sur une copie de la vraie base (35 annonces, filtre « Autour d'Annecy ») plus un jeu Faker : charges inconnues, sans DPE, quatre doublons sur quatre sources, titre de 200 caractères, sans photo, date estimée, DPE G, chauffage collectif, champs manquants.

Outils utilisés :
- `measure.mjs` à 390, 1280 et 1440, et `make ui-check` (vert : contrastes, focus, modale, débordement).
- Captures regardées : liste, carte G, carte sans photo, états erreur, vide, sans filtre, crawl en cours, modale et erreur d'enregistrement.
- `hunt review` piloté dans un pseudo-terminal 120×32.

Gravité, jugée pour le rejet rapide :
- **Haute** : fausse lecture d'un chiffre, annonce perdue ou masquée, ou donnée détruite.
- **Moyenne** : ralentit le tri ou laisse un état sans réponse.
- **Basse** : finition.

Rien n'est corrigé ici. Les constats nourrissent les tickets 04 à 08 ; la colonne « Pour » indique lequel.

### Page web

| # | Gravité | Constat | Où | Règle | Pour |
|---|---|---|---|---|---|
| W1 | Haute | « 941€/mois CC » suivi de la puce « HC » : le total charges comprises et la mention « loyer annoncé hors charges » se lisent comme une contradiction sur le chiffre principal | `assets/app.js:606-607`, `domain/value_objects/price.py:25-28` | PRODUCT principe 1, fondamentaux § 1 (sens sans explication) | 06 |
| W2 | Haute | « Mis à jour à 7h22 » est l'heure du rendu dans le navigateur, pas celle du dernier crawl : la vraie base n'a rien récupéré depuis le 2026-09-25 et l'écran dit « à jour » | `assets/app.js:358` | PRODUCT principe 5, `overview.md` (alerté le premier) | États (non spécifié) |
| W3 | Haute | Crawl en cours = « Crawl en cours… » en gris et un bouton désactivé. Aucune source en cours, finie, vide ou en échec : une panne comme celle de PAP en septembre est invisible depuis le web | `assets/app.js:628-671` | PRODUCT principe 5 (« no-results-for-this-source ») | États (non spécifié) |
| W4 | Haute | Modifier un filtre efface en silence les critères absents de la modale : `max_surface_m2`, `max_rooms`, `charges_included`, `collective_heating`, `min_photos`, `exclude_agencies`, `max_age_days`, ainsi que `enabled`. Un filtre créé en CLI (`seed_filters.py` : `min_photos=2`, `charges_included=True`) perd ces critères au premier « Enregistrer » | `assets/app.js:857-878`, `web/filter_payload.py:42-67` | données détruites | Modale (non spécifié) |
| W5 | Haute | Une annonce réelle à « 0€/mois » (Gruffy, échec de lecture du prix) passe le filtre de budget et sort **première** au tri « Prix, moins cher » | donnée en base ; bornes dans `domain/services/sanitising.py`, matcher `listing_matcher.py:87-93` | CLAUDE.md § Security (assainir à la frontière) | ticket de collecte à ouvrir |
| W6 | Moyenne | Le badge « Nouveau » pulse sans fin sur chaque carte non ouverte (7 sur 15 dans la vraie base, 11 sur 25 dans le jeu) : le mouvement ne marque plus un état, il couvre la page | `assets/styles.css:382-383`, `assets/app.js:600` | DESIGN § Motion, Vercel « autoplay > 5 s » | 04, 06 |
| W7 | Moyenne | Neuf teintes de source sur la barre de filtres et sur chaque carte, placées en tête de carte : la première couleur vue est la source, pas le prix ni la nouveauté | `assets/styles.css:252-262`, `assets/app.js:602` | PRODUCT principe 2 (seule la nouveauté gagne la couleur) | 04 |
| W8 | Moyenne | Les compteurs des pastilles de source et le filtre par source portent sur la **page courante** seulement : « PAP 5 » veut dire 5 sur cette page, et « Aucun logement pour cette source » peut s'afficher après un changement de page alors que d'autres pages en ont | `assets/app.js:338-351` | fondamentaux § 1 (l'écran dit vrai) | 06 |
| W9 | Moyenne | Une pastille de source désélectionnée passe à `opacity: 0.5` et `saturate(0.25)`, sans autre marque : son texte tombe sous 4.5:1 (estimé à 2.3:1 environ), et l'état ne tient qu'à l'intensité | `assets/styles.css:268` | audit.md (contraste, couleur seule) | 04 |
| W10 | Moyenne | Une erreur d'enregistrement du filtre s'affiche en toast, en anglais technique (« radius_km must be between 1 and 150, got 400 »), avec l'icône de succès ✓, loin du champ Rayon qui n'est pas marqué invalide | `assets/app.js:890-893`, `assets/app.js:732` | fondamentaux § 2 (erreur sous son champ, qui nomme la correction), DESIGN § Forms | Modale |
| W11 | Moyenne | `startWatch` et `deleteFilter` ne lisent pas la réponse : la surveillance s'affiche active, ou « Filtre supprimé » s'affiche, même sur une erreur serveur | `assets/app.js:685-688`, `assets/app.js:914-926` | fondamentaux § 2 (dire ce qui s'est passé) | États |
| W12 | Moyenne | Prix sans séparateur de milliers ni espace (« 1282€/mois ») : sur une colonne de prix à quatre chiffres, l'œil compte les chiffres | `domain/value_objects/price.py:20-28` | Vercel (formats localisés), PRODUCT (numbers over adjectives) | 06 |
| W13 | Moyenne | Le survol de la carte (bordure et ombre) promet un clic, mais seul le titre (19 px de haut) ouvre l'annonce | `assets/styles.css:281`, `assets/app.js:572` ; `deadHover` mesuré | fondamentaux § 1 (survol seulement sur ce qui agit), Fitts | 05, 06 |
| W14 | Moyenne | La modale ne propose ni surface max, ni pièces max, ni charges, ni chauffage, ni photos min, ni agences, ni âge max, alors que `SearchFilter` les porte | `assets/index.html:87-199` | parité avec le domaine | Modale |
| W15 | Moyenne | Hauteurs de carte inégales (doublons, avertissements, titres sur deux lignes) dans une grille `align-items: start` : trous de 39 à 70 px entre les rangées (mesuré), donc une lecture en ligne qui saute | `assets/styles.css:207-209` | fondamentaux § 4 (un rythme d'espacement) | 06 |
| W16 | Moyenne | Écarter et position au marché, toutes deux décidées pour le web par la map, sont absentes | `assets/app.js:577-622` | map, Notes | 05, 06 |
| W17 | Basse | Deux boutons pleins au-dessus de la ligne de flottaison (« Rechercher » en en-tête, « Nouveau filtre » en barre latérale) | `assets/index.html:46`, `assets/index.html:61` | Von Restorff, une action dominante | 06 |
| W18 | Basse | Police de 10 px (pastilles de source, badge « Nouveau », libellés DPE/GES) sous le plancher de 11 px de DESIGN | `assets/styles.css:256`, `:270`, `:288`, `:346` | DESIGN § Typography | 04 |
| W19 | Basse | Pastilles de source hautes de 22 px, sous le minimum de 24 px | `assets/styles.css:264-265` | Vercel (cible ≥ 24 px) | 04 |
| W20 | Basse | Aucun `h1` ; nom « Apartment Hunter » en anglais dans une interface française ; `<title>` figé | `assets/index.html:8`, `:43` | audit.md (ordre des titres), PRODUCT (French UI), Vercel (`<title>`) | 06 |
| W21 | Basse | Ni le filtre, ni la page, ni le tri, ni la source ne sont dans l'URL : un rechargement revient au premier filtre, page 1 | `assets/app.js:274-281`, `:485-489` | Vercel (l'URL reflète l'état) | 06 |
| W22 | Basse | Em-dashes dans l'interface : 34 mesurés, dont les libellés de tri « Parution — plus récentes » et les infobulles | `assets/app.js:49-52`, `:511`, `:561` | fondamentaux § 11 | 06 |
| W23 | Basse | « 5ème étage » au lieu de « 5e étage » | `domain/value_objects/floor.py:29` | typographie française | 06 |
| W24 | Basse | En modification, les exemples des champs vides (« 400 », « 25 », « 1 ») se lisent comme des valeurs saisies | `assets/index.html:125-139` | Vercel (exemple de motif dans un placeholder, terminé par …) | Modale |
| W25 | Basse | Libellés « Notifications (min) » et « Rafraîchissement auto (min) » : jargon pour les deux cadences d'ADR-0005 | `assets/index.html:191-196` | glossaire | Modale |
| W26 | Basse | À 390 px, la première carte commence à mi-écran et l'en-tête des résultats coupe « · page 1 sur 3 » sur une ligne seule | `assets/styles.css:469-491`, `assets/app.js:352-356` | PRODUCT (chrome shrinks), vérifié sans casse | 06 |
| W27 | Basse | « Crawl » en libellé visible (« Crawl en cours… ») | `assets/app.js:631` | PRODUCT (French UI) | États |

Tenus, à ne pas casser :
- Aucun débordement horizontal à 390 px.
- Lettre DPE/GES toujours écrite ; la carte G porte son avertissement en clair.
- Marque « charges ? » visible ; date estimée préfixée « vu ».
- Squelettes à la géométrie des cartes ; états vide, erreur et sans filtre conçus, chacun avec son action.
- Lien d'évitement en premier arrêt de tabulation ; modale avec piège de focus, Échap et retour du focus.
- Contrastes AA mesurés (`make ui-check`).

### `hunt review` (terminal)

| # | Gravité | Constat | Où | Règle | Pour |
|---|---|---|---|---|---|
| R1 | Haute | La liste ne distingue pas une annonce jamais ouverte d'une déjà vue : le seul moyen de repérer les nouveautés est absent de l'écran de revue | `cli/review.py:90-96` | PRODUCT (repérer les 2 ou 3 nouveautés) | 08 |
| R2 | Haute | La liste affiche « 980€/mois » sans la marque des charges inconnues : le loyer seul se lit comme un total | `cli/review.py:92` | CLAUDE.md (`charges_unknown` : web, CLI et résumé portent la marque) | 08 |
| R3 | Moyenne | Le détail n'a ni GES, ni avertissement de location interdite F/G, ni position au marché | `cli/review.py:110-120` | CLAUDE.md (avertir sur F/G), map | 08 |
| R4 | Moyenne | Prix alignés à gauche et sans séparateur (« 1134€/mois CC » sous « 941€/mois CC ») : la colonne de prix ne se compare pas d'un coup d'œil | `cli/review.py:92` | PRODUCT (comparaison de chiffres) | 08 |
| R5 | Moyenne | La ligne sélectionnée est sur fond `grey23` codé en dur : sur un terminal clair, le texte par défaut sombre devient illisible. À vérifier dans un thème clair | `cli/review.py:95` | Rich hérite des couleurs (map, Notes) | 08 |
| R6 | Moyenne | Un écart est définitif depuis l'écran : ni annulation, ni rappel de la ligne écartée (« Écarté (trop cher). » ne nomme pas le logement) | `cli/review.py:187-194` | fondamentaux § 2 (dire ce qui s'est passé), Vercel (annuler un geste destructeur) | 08 |
| R7 | Basse | `o` ouvre le navigateur sans aucun message | `cli/review.py:184-186` | retour sur chaque action | 08 |
| R8 | Basse | Les flèches ne naviguent pas, seuls `j`/`k` | `cli/review.py:180-183` | Jakob | 08 |
| R9 | Basse | Hors terminal interactif, message en anglais qui ne dit pas quoi faire | `cli/review.py:163` | fondamentaux § 2, langue | 08 |
| R10 | Basse | Neuf raisons sur une ligne, imprimées sous l'aide sans redessiner l'écran | `cli/review.py:145-148` | Hick (liste fermée d'ADR-0009, à présenter, pas à réduire) | 08 |
| R11 | Basse | « €/m² 15.6 » avec un point décimal ; en-tête « 1 logements » au singulier | `cli/review.py:68`, `:112` | typographie française | 08 |
| R12 | Basse | Un logement publié sur quatre sources n'est pas marqué dans la liste, seulement dans le détail (« Source ») | `cli/review.py:90-96` | duplicates.py (une ligne par logement, mais dire combien) | 08 |

### Hors interface, vus pendant l'audit

| # | Gravité | Constat | Où |
|---|---|---|---|
| H1 | Haute, non vérifiée en direct | La table des communes est indexée sur le nom INSEE (« sevrier », « epagny metz-tessy », sans accent), et le matcher cherche `city.lower()` tel que le site l'écrit. Une annonce sans coordonnées venant de « Sévrier » ou « Épagny Metz-Tessy » ne trouve pas sa commune et retombe sur la comparaison exacte avec la ville du filtre : elle est **écartée en silence**. Reproduit avec le jeu semé : les 10 annonces semées dans ces deux communes, à moins de 10 km d'Annecy, sont toutes absentes du filtre à 20 km. Reste à mesurer la graphie réelle de chaque crawler | `domain/services/listing_matcher.py:65`, `:74` ; clés construites dans `infrastructure/geocoder.py:171` |
| H2 | Moyenne | Quatre annonces réelles titrées « Colocation à louer » passent `is_out_of_scope_tenancy` : les motifs exigent « colocation meublée / de / dans ». Peut-être voulu (règle prudente), à trancher | `domain/services/tenancy_scope.py:24-26` |

**Suite H1 (2026-10-29)** : confirmé en direct. Laforêt écrit « Saint Felix », « Saint Sylvestre », « Chambery » ; Century 21 « Alby Sur Cheran », « Viuz La Chiesaz » ; aucune annonce n'a de coordonnées. La cause tient aux accents **et** aux tirets. Corrigé sur `fix/commune-spelling` : les noms sont repliés des deux côtés, villes exclues comprises (`_fold_commune_name`). Sur la copie d'audit, on passe de 63 à 73 logements. Reste non couvert : une commune renommée ou fusionnée (« Vallieres » pour Vallières-sur-Fier). La clé de doublon (`build_home_key`) compare encore les noms sans repli ; la corriger demande de migrer `dismissals.home_city`.

**Suite H2 (2026-10-31)** : tranché, ce sont des chambres. Un titre qui commence par « Colocation » est exclu (`^\s*colocation\b`) ; un titre qui la cite plus loin (« T5 pour colocation », « colocation possible ») passe toujours. Corrigé sur `fix/colocation-a-louer`.

## Suite W4 et W5 (2026-10-30)

Les deux défauts de données sont corrigés sur `fix/filter-edit-keeps-criteria`, à partir de la pile de l'interface :

- **W4** : une modification applique le formulaire *sur le filtre enregistré* (`apply_payload`). Les critères que la modale n'affiche pas sont donc conservés : photos min, charges, âge max, agences exclues, surface max, activé, date de création.
  - Vérifié par l'API réelle et par un test, qui échoue sur l'ancien comportement.
  - Modifier un filtre inconnu renvoie 404 au lieu d'en créer un.
- **W5** : une annonce dont le loyer se lit à 0 € n'est plus enregistrée (`_keep_storable`), avec une ligne de log.
  - Le défaut d'origine sur EntreParticuliers (« € /mois » lu à 0 €) est corrigé à part, sur `feat/crawler-entreparticuliers`.
