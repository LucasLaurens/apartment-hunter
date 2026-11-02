# Modale de filtre

Type: grilling
Status: resolved
Blocked by:

## Question

Qu'est-ce qui gêne vraiment dans la modale ? Constats de l'audit (ticket 03) :

- **W4**, haute : modifier un filtre effaçait en silence les critères que la modale n'affiche pas. Corrigé à part (`fix/filter-edit-keeps-criteria`), car une donnée perdue n'attend pas une décision d'interface.
- **W10** : une erreur d'enregistrement s'affiche en toast, en anglais technique, loin du champ concerné.
- **W14** : la modale ne propose pas la surface max, les pièces max, les charges, le chauffage, les photos min, les agences exclues ni l'âge max, que `SearchFilter` porte pourtant.
- **W24** : en modification, les exemples des champs vides se lisent comme des valeurs saisies.
- **W25** : les libellés « Notifications (min) » et « Rafraîchissement auto (min) » sont du jargon.

À trancher : quels critères exposer, et dans quel ordre ; la forme des erreurs ; les libellés des deux cadences (ADR-0005).

## Answer

Grilling du 2026-10-31. Les quatre recommandations sont retenues et implémentées sur `feat/modale-filtre`, à la suite de la pile.

- **W14** : une section repliée « Plus de critères » regroupe :
  - surface max et pièces max ;
  - charges et chauffage, en trois choix ;
  - photos min et ancienneté max (« parues depuis moins de N jours ») ;
  - agences exclues.
  
  Elle s'ouvre d'elle-même quand le filtre en utilise un.
- **Trouvé en route** : le serveur lisait `max_rooms` mais la page ne l'envoyait jamais, donc chaque modification le remettait à vide. C'était un reste de W4. Un test de parité échoue désormais quand le serveur lit un critère que `filterPayload()` n'envoie pas ; il a été vu échouer.
- **W10** : une borne refusée nomme son champ (`FilterBoundError`). Le serveur répond `422 {field, message}`, et la page affiche la phrase sous le champ, en français (« Le rayon va de 1 à 150 km. »). Elle marque le champ invalide et ouvre la section repliée si besoin. Le reste des erreurs apparaît sans coche de succès.
- **W24** : les exemples suivent la forme « ex. 1 200… ».
- **W25** : « Chercher sur les sites toutes les (min) » et « M'alerter au plus toutes les (min) », chacun avec une ligne d'aide, dans cet ordre.
- **Vérifié** :
  - parcours piloté en clair et en sombre : critères cachés relus à l'ouverture, rayon de 400 km refusé sous son champ, enregistrement puis réouverture qui garde pièces max, photos min et ancienneté ;
  - `ui-check` passe ;
  - 347 tests.
