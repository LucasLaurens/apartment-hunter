# 06: Tri par position et par €/m²

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** La revue est triée par défaut de la position au marché la plus basse à la plus haute, les logements sans repère en fin. `s` fait tourner position → €/m² → parution. Le tri par position se calcule en Python sur tous les logements qui passent le filtre, **avant** la limite du nombre de résultats, pour classer tout le vivier et pas seulement les plus récents. Le tri par €/m² (total CC) est aussi exprimé en SQL et tenu par le test de parité SQL/Python existant. La page web garde la parution par défaut.

**Blocked by:** 05

**Status:** done (branche `feat/position-marche`)

- [ ] Deux nouvelles valeurs dans l'enum de tri : position au marché, €/m²
- [ ] Test : ordre par position, sans-repère en fin
- [ ] Test : avec plus de logements que la limite, le tri par position garde les mieux placés du vivier entier, pas ceux des plus récents
- [ ] Test de parité SQL/Python étendu au tri €/m² (annonces sans surface comprises)
- [ ] Touche `s` et tri en cours affiché en tête de revue
- [ ] Doc du tri à jour (règle de parité mentionnée)
- [ ] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
