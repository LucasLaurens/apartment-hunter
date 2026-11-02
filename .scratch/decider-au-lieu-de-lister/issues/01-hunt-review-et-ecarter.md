# 01: hunt review et écarter un logement

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Le chasseur lance `hunt review --filter "<nom>"` et passe en revue les logements de son filtre dans la disposition retenue par le prototype (variante C) : liste courte à gauche, panneau de détail à droite, touches en pied d'écran. Tri par parution pour l'instant. `j`/`k` naviguent, `o` ouvre le lien dans le navigateur (comportement d'ouverture actuel), `q` quitte. `x` écarte le logement sélectionné après le choix obligatoire d'une raison (`1`-`8`, ou `0` + texte libre éventuellement vide ; une touche invalide annule).

Le logement écarté disparaît de la revue, de la page web et de l'alerte, et ne revient ni par un doublon d'une autre source, ni après une purge, ni sous une nouvelle URL. L'écart est global (tous filtres) et sans expiration. Commencer par exposer la clé de regroupement de *Doublon* pour la partager (préfactoring sans changement de comportement).

**Blocked by:** None (can start immediately)

**Status:** done (branche `feat/hunt-review-ecarter`)

- [x] La clé « même logement » a un seul propriétaire, partagé par le regroupement des doublons et la reconnaissance des écarts ; `group_duplicates` garde son comportement (tests existants verts)
- [x] Un écart est un jugement conservé hors de la table des annonces, avec la photo figée (clé de regroupement, source, identifiant, total CC, surface, étage, DPE, annonceur, meublé), la raison, le texte libre et la date ; la purge ne le touche pas
- [x] Raison d'écart = enum fermée (trop cher, trop petit, étage, DPE, commune, annonceur, meublé, aspect, autre) ; seul « autre » porte un texte
- [x] Test : écarter, purger, republier (même URL, nouvelle URL, autre source) → le logement reste masqué dans la revue
- [x] Test : deux lots identiques d'une même source → en écarter un ne masque pas l'autre
- [x] Test : une annonce sans pièces ni surface écartée n'est masquée que sous la même URL
- [x] Test : `GetTopListings` (web) et l'alerte masquent les logements écartés, par la même règle que la revue
- [x] Test SQLite : les écarts survivent à `delete_many`
- [x] `hunt review` tourne sur la vraie base, écran vérifié à l'œil (liste, panneau, touches, choix de raison)
- [x] README (commande `hunt review`), `docs/technical/data-model.md` (table des jugements), `docs/technical/architecture.md`, ligne « reconnaissance du logement » dans les Shared Rules de `CLAUDE.md`, glossaire *Écarté* et *Raison d'écart* à jour (✅ pour ce qui est livré)
- [x] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker

## Notes de livraison

- Limite assumée, conforme à la règle *Doublon* : une republication par **la même** source sous une nouvelle URL n'est pas reconnue (elle ne se distingue pas du lot identique d'une résidence). Le glossaire le dit ; la spec (story 36) le promettait à tort.
- Vérifié : 10 tests de cas d'usage et 4 tests SQLite, chacun vu rouge par une mutation volontaire (règle de source ignorée, règle de clé supprimée, purge qui efface les écarts), puis vert. Écran rendu sur une copie de la vraie base ; un écart y retire bien le logement.
