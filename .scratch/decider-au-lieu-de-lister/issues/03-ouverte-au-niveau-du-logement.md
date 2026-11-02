# 03: Ouverte au niveau du logement

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Ouvrir une annonce — `o` dans la revue ou clic depuis la page web — marque tout son logement *ouvert*, doublons compris. L'ouverture survit à la purge et à une republication : le badge *Nouvelle* ne se rallume plus sur un autre site ni après un retour de l'annonce. La revue affiche « ouverte le … ». Les ouvertures existantes (colonne d'horodatage sur les annonces) sont migrées en jugements d'ouverture, qui deviennent la seule source de vérité ; le sens de *Nouvelle* (ADR-0002) ne change pas.

**Blocked by:** 01

**Status:** done

- [x] Test : ouvrir une annonce rend son doublon d'une autre source *ouvert* (badge *Nouvelle* éteint)
- [x] Test : une annonce ouverte, purgée puis republiée reste *ouverte*
- [x] Test SQLite : la migration transforme chaque horodatage d'ouverture existant en jugement d'ouverture, une seule fois
- [x] La route web d'ouverture passe par le même cas d'usage que la revue
- [x] « ouverte le … » visible dans la revue
- [x] `docs/technical/data-model.md` (migration), glossaire *Ouverte* et *Nouvelle* à jour, mention 🚧 retirée
- [x] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
