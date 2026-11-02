# Carte des filtres et des logements

Type: prototype
Status: resolved
Blocked by:

## Question

Où vit la carte sur la page web, et que montre-t-elle d'un coup d'œil ? Trois variantes à prototyper :
- une bascule « Liste / Carte » dans la zone principale ;
- une carte latérale permanente à côté de la liste ;
- une carte dans la modale du filtre, pour régler le rayon et les communes exclues.

Elle montre la commune de base, le cercle du rayon, les communes exclues, et une pastille par commune avec son nombre de logements. Un clic sur une pastille filtre la liste sur cette commune.

## Décidé (grilling du ticket 08, 2026-10-29)

- **Fond** : MapLibre avec les tuiles vectorielles d'OpenFreeMap, gratuites, sans clé ni quota, données OpenStreetMap. Style clair ou sombre selon le thème (ADR-0011). L'attribution OSM est affichée.
- **Positions** : une pastille par commune, au centre de la commune déjà géocodé par le projet. Aucune source ne publie les coordonnées d'une annonce (0 annonce sur 4 en base le 2026-10-29). On ne géocode pas d'adresse par annonce, faute d'adresses publiées et pour ne pas multiplier les requêtes Nominatim. La question reste ouverte si une source publie un jour des coordonnées.
- **Chargement** : la bibliothèque n'est chargée qu'à l'ouverture de la carte, pas à chaque visite. Une ligne sous la carte dit qu'elle interroge OpenFreeMap.

## Garde-fous de sécurité (exigés, valables pour toute l'application)

- **Script tiers** : depuis un CDN autorisé (jsdelivr ou unpkg), en version exacte, avec `integrity` (SRI) et `crossorigin="anonymous"`. Jamais de « latest », jamais de version flottante. Un test vérifie que toute balise `<script src>` ou `<link>` externe porte un `integrity`.
- **Données scrapées sur la carte** : commune, nombre et titre ne passent jamais par `setHTML` ni par `innerHTML` d'un popup. Ils passent par `textContent` ou `escHtml`, comme sur les cartes. Aucune valeur scrapée ne va dans une URL de tuile ni dans du JS inline.
- **Origines** : les URL de tuiles et de style sont des constantes nommées (un seul fournisseur). Aucune clé d'API dans le dépôt.
- **Coordonnées** : elles viennent de notre propre API (géocodage déjà en cache), jamais d'un champ scrapé.
- **Hors ligne** : si la carte ne peut pas se charger, la page la remplace par un état dédié (« carte indisponible »). La liste reste utilisable.

Docs à mettre à jour avec : `DESIGN.md` (composant Carte), `docs/technical/architecture.md`, `docs/technical/security.md` (dépendance tierce, SRI), le README.

## Answer

**Variantes A et C**, choisies sur prototype le 2026-10-30. Les trois variantes restent sur la branche `prototype/carte` (`3892e84`). Implémenté sur `feat/carte`.

- **Page (A)** : une bascule « Liste / Carte » dans la barre des résultats. La carte montre le rayon du filtre et une pastille par commune avec son nombre de logements.
- **Clic sur une pastille** : il ouvre le détail de la commune, demande faite au choix. On y voit la liste de ses logements, chacun avec son lien et sa marque « Nouveau ». Le clic ne filtre pas la liste : le filtrage par commune se fait dans la modale.
- **Modale du filtre (C)** : une carte compacte. Le cercle suit le rayon pendant la saisie, et un clic sur une commune l'ajoute aux « Villes exclues » ou l'en retire.
- **Serveur** :
  - `MapFilterHomes` place chaque logement par `ListingMatcher.find_position`, la même règle que la vérification du rayon.
  - `GET /api/filters/{id}/map` renvoie les logements par commune.
  - `GET /api/area` renvoie les communes du rayon pour le formulaire, enregistré ou non. Ses bornes sont refusées en 422 avant tout géocodage.
  - Un logement que la carte ne sait pas placer est compté et signalé sous la carte, pas perdu.
- **Couleurs** : encre neutre pour le rayon et les pastilles, puisqu'une pastille est un compte et pas un état (budget du ticket 04). Une commune exclue se reconnaît à sa forme : creuse et barrée. Le popup suit le thème.
- **Garde-fous de sécurité, vérifiés par test et provoqués exprès** :
  - MapLibre épinglé (4.7.1) avec SRI et `crossorigin` ;
  - aucun `setHTML` ;
  - aucune balise externe sans `integrity`.
  
  Rien d'externe n'est chargé avant l'ouverture d'une carte (mesuré : 0 requête).
- **Limite connue** : sur cette pile de branches, les noms de commune sont comparés en minuscules seulement. « Sevrier » exclu depuis la carte ne masque donc pas une annonce écrite « Sévrier ». Le pliage des accents de `main` (`ac5aefe`) corrige ce point à la fusion.
