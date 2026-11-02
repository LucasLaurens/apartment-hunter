# 05: Position au marché dans la revue

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Chaque logement de la revue porte sa position au marché : « −12 % vs réf. », avec « hors fourchette » hors de l'intervalle de prédiction et « (repère faible) » quand moins de 30 annonces sont observées dans la commune ou que le R² ajusté est < 0,5. Sinon « pas de repère (meublé | charges inconnues | sans surface | commune absente) », jamais de repli sur une zone plus large. Le panneau montre la référence utilisée (segment, commune, valeur, fourchette, millésime, logement type) ; le pied porte la mention de source ANIL.

Pour y arriver : le géocodage fournit le code INSEE de chaque commune du rayon (champ ajouté à l'appel geo.api.gouv.fr existant, communes déléguées rattachées à leur chef-lieu) ; un nouveau port « loyer de référence » est servi par un adaptateur de la Carte des loyers (téléchargement à la première utilisation, cache local par millésime, URL et millésime en constantes) ; un service pur du domaine calcule la position (ADR-0010).

**Blocked by:** 01

**Status:** done (branche `feat/position-marche`)

- [ ] Segment : 1-2 pièces → T1-T2, 3+ → T3+, inconnu → tous appartements
- [ ] Test : chaque cas — position simple, hors fourchette, repère faible, et les quatre « pas de repère » (vérifiés dans l'ordre meublé, charges inconnues, sans surface, commune absente)
- [ ] Test : une annonce d'une ancienne commune fusionnée (Seynod) reçoit la référence de la commune nouvelle
- [ ] Test : l'adaptateur lit un petit CSV d'exemple commité (cp1252, `;`, virgule décimale, code INSEE à zéro de tête) depuis un cache rempli, sans réseau
- [ ] Seuils (30 observations, R² 0,5) en constantes nommées ; mention de source en constante
- [ ] Écran vérifié à l'œil sur la collecte « Autour d'Annecy »
- [ ] `docs/technical/architecture.md` (port, adaptateur, cache), `docs/technical/crawlers.md` ou doc géocodage (code INSEE), Shared Rules de `CLAUDE.md` (position au marché), glossaire *Loyer de référence* et *Position au marché* en ✅, ADR-0010 « en vigueur »
- [ ] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
