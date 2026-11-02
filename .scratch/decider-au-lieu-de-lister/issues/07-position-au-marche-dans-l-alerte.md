# 07: Position au marché dans l'alerte

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Chaque logement de l'alerte (le bloc que `TerminalNotifier` imprime en mode `watch`/`search` ; l'application n'envoie aucun email) porte sa position au marché (ou « pas de repère (raison) ») avec les mêmes libellés que la revue, et la fin du bloc porte la mention de source ANIL. La position dépend du référentiel : l'application la compose avec la ligne de résumé du domaine, qui ne la connaît pas.

**Blocked by:** 05

**Status:** done (branche `feat/position-marche`)

- [ ] Test (`InMemoryNotifier`) : la ligne d'un logement comparable porte sa position ; celle d'un logement non comparable porte « pas de repère (raison) »
- [ ] Test : la mention de source est présente dans l'alerte
- [ ] Échappement HTML des libellés conservé (tests d'échappement des notifications verts)
- [ ] `docs/functional/notifications.md` à jour
- [ ] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
