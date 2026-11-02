# Map — UI/UX du chasseur

Label: wayfinder:map

## Destination

Une spec prête à implémenter (`ready-for-agent`) qui améliore l'UI/UX de la page web, dégelée, et de `hunt review`, chaque amélioration jugée contre la raison d'être de `PRODUCT.md` : repérer les deux ou trois vraies nouveautés, rejeter le reste en moins d'une seconde, trouver l'annonce ici avant les portails. Avec une collecte qui couvre le maximum de sources accessibles.

## Notes

Cadre verrouillé au chartage (2026-10-28), à respecter par chaque session :

- **Étalon** : la raison d'être de `PRODUCT.md` (Users, Product Purpose, Design Principles) ; la vitesse d'`overview.md` (« être alerté le premier ») comme contrainte ; les *raisons d'écart* (ADR-0009) comme signal de ce qui doit sauter aux yeux.
- **Surfaces** : la page web est **dégelée** (la note « page web gelée » de [Décider au lieu de lister](../idee-produit/map.md) tombe) et redevient une surface de décision ; `hunt review` reste la surface terminal. Le web peut **écarter**, par le même cas d'usage `DismissHome` et la même liste fermée de raisons.
- **Acquis** : les 7 tickets `ready-for-agent` de [Décider au lieu de lister](../decider-au-lieu-de-lister/issues/) ne sont pas redécidés ; cette map décide comment ils s'affichent. Seule exception rouverte : « position au marché : web non », qui ne tenait qu'au gel. Le web l'affiche, même formulation que la revue (« −12 % vs réf. », « pas de repère »).
- **Lisibilité** : `PRODUCT.md` prime sur la règle « inconnu pressé sur téléphone » de ui-ux-craft. Critère : compris en un coup d'œil de 15 s. Mesures à 1280 / 1440, plus 390 pour vérifier que rien ne casse.
- **Thème** : choix de l'utilisateur dans des paramètres web, Clair / Sombre / Système. Amende le principe 3 de `PRODUCT.md` (« One theme ») et `DESIGN.md` § Theme ; `check_single_light_theme` (`scripts/verify_ui.py`) devra changer. ADR-0011 à écrire par le ticket qui le résout. Le terminal n'est pas concerné (Rich hérite des couleurs du terminal).
- **Design system** : `DESIGN.md` existe, donc ui-ux-pro-max sans `--design-system` ; recherche par motif, subordonnée aux lois locales.
- **Collecte, exécutée dans la map** : par exception au « planifier sans faire », les tickets de collecte livrent du code, chacun sur sa branche `fix/crawler-<source>` (ou `feat/crawler-<source>`), avec `docs/technical/crawlers.md`, `docs/functional/sources.md` et le README dans le même commit, `make full` vert.
- **Limites de collecte, non négociables** : `robots.txt` respecté (L'Adresse reste exclue), aucun CAPTCHA résolu, aucun compte créé ni identifiant saisi. Jinka et Bien'ici sont voulus **seulement** s'ils sont accessibles sans connexion. Une source bloquée sans contournement acceptable est retirée, pas laissée en échec.
- **Skills à appeler** : `grilling` + `domain-modeling` pour les tickets grilling ; `ui-ux-craft` pour tout ticket d'interface ; `prototype` pour les tickets prototype ; `research` pour la recherche. Règles du projet : `CLAUDE.md`.

## Decisions so far

<!-- une ligne par ticket résolu : gist + lien -->

- [Réparer PAP, Orpi et le DPE de ParuVendu](issues/01-reparer-pap-orpi-paruvendu.md) : rien n'était cassé comme annoncé ; échecs mis en cache (PAP, codes postaux) corrigés, Orpi filtré au département, ParuVendu lu sur la carte ; pages détail PAP (403) et ParuVendu (captcha) bloquées, acceptées
- [Quelles sources sont accessibles autour d'Annecy ?](issues/02-sources-accessibles.md) : Bien'ici, Square Habitat, EntreParticuliers retenues ; ERA, Capifrance, iad, Nestenn à faible volume ; Jinka et Leboncoin rejetés
- [Audit de l'existant](issues/03-audit-de-l-existant.md) : web, 27 constats dont 5 hauts (« CC » puis « HC » sur le prix, « Mis à jour » qui ment sur la fraîcheur, crawl sans état par source, modification de filtre qui efface des critères, annonce à 0 € en tête du tri) ; `hunt review`, 12 dont 2 hauts (pas de marque nouveau ni charges inconnues dans la liste) ; hors interface, des communes accentuées probablement perdues au matching
- [Budget de couleur](issues/04-budget-de-couleur.md) : texte neutre confirmé et budget resserré ; position au marché et écart sans teinte ; plus de teinte par source (état des pastilles par la forme) ; Nouveau sans fond teinté ni pulsation ; orangé réservé à « charges ? » et F/G ; primaire/secondaire/tertiaire = hiérarchie d'actions sur une teinte ; budget encodé dans `test_colour_budget.py` (implémenté) ; annonces expirées sorties en [ticket 13](issues/13-annonces-expirees.md)
- [Annonces expirées](issues/13-annonces-expirees.md) : `last_seen_at` + dernière réponse de chaque source par filtre ; expirée masquée, source injoignable marquée puis masquée à 7 j, avis en tête de liste ; temps compté en crawls du filtre, pas à l'horloge ; aucune requête en plus
- [Paramètres web et thème](issues/07-parametres-et-theme.md) : page Paramètres (variante C du prototype), Clair / Sombre / Système en `localStorage`, Système par défaut ; une seule liste de couleurs en `light-dark()` ; ADR-0011
- [Hiérarchie de la carte web](issues/06-hierarchie-de-la-carte-web.md) : ligne de décision (variante A) ; total et commune, puis taille · étage · DPE · GES, puis argent et annonceur ; titre réduit à un lien étendu sur la carte ; plus de couleur de source ni de pulsation ; 9 / 12 cartes visibles à 1280 / 1440
- [Geste d'écart web](issues/05-geste-d-ecart-web.md) : bouton « Écarter » et clavier `j`/`k`/`x` comme `hunt review`, une barre de raisons fixe, « Annuler » 6 s, page « Écartés » pour restaurer ; restaurer laisse une trace (`restored_at`)
- [Constats hunt review](issues/08-constats-hunt-review.md) : les douze retenus et implémentés ; ● nouveauté, montants « 1 210 € CC » formés dans le domaine, panneau dans l'ordre de la carte web, `reverse` pour la sélection, `u` annule, `hunt review --dismissed` restaure
- [Carte des filtres](issues/14-carte-des-filtres.md) : bascule Liste / Carte, une pastille par commune qui ouvre ses logements, carte de zone dans la modale (rayon en direct, clic pour exclure) ; MapLibre épinglé avec SRI, chargé à la demande
- [Crawler Bien'ici](issues/09-crawler-bienici.md) : rejeté, les CGU interdisent la reproduction du contenu sans autorisation ; dans le doute, pas de collecte
- [Sources à faible volume](issues/12-crawlers-faible-volume.md) : ERA, Capifrance, iad, Nestenn pas pour l'instant (1 à 3 annonces chacune dans le rayon)
- [États de la page](issues/15-etats-de-la-page.md) : « Dernière recherche : il y a … » calculée par le serveur, une étiquette d'avancement par source pendant une recherche, réponses du serveur vérifiées, « Recherche » au lieu de « Crawl »
- [Tri, pagination et URL](issues/17-tri-pagination-url.md) : compteurs de source sur tout le filtre et source choisie côté serveur, état dans l'URL (nouveau filtre = étape d'historique), onglet et `h1` au nom du filtre, plus de tiret cadratin dans la page (test), en-tête empilé à 390 px ; tri par position au marché reporté à l'ADR-0010
- [Modale de filtre](issues/16-modale-de-filtre.md) : « Plus de critères » replié (s'ouvre s'il sert), erreurs de borne sous leur champ en français, exemples « ex. … », libellés des deux rythmes ; `max_rooms` n'était jamais envoyé, un test de parité le garde

## Not yet specified


- **Paramètres au-delà du thème** : rien d'identifié ; la page Paramètres existe et n'attend qu'un réglage de plus.

## Out of scope

- Tableau de `hunt search` et assistant `hunt filter add` : surfaces terminal hors revue.
- Bloc d'alerte de `hunt watch` au-delà de la position au marché (déjà décidée).
- Tout accès à une source qui exige un compte, un identifiant ou un CAPTCHA.
- Multi-utilisateur, comptes, hébergement.
