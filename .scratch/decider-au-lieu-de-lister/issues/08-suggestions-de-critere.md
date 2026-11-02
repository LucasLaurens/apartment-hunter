# 08: Suggestions de critère

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Au 3e écart actif pour la même raison — et la même valeur quand la raison en a une (même commune, même annonceur, même étage) — la revue pose, juste après l'écart, une question `[o/N]` qui propose la modification de filtre la plus prudente et dit combien de logements non écartés elle masquerait aussi. Valeurs : trop cher → `max_price` à la dizaine sous le plus petit total CC écarté ; trop petit → `min_surface_m2` au m² entier au-dessus de la plus grande surface écartée ; étage → exclusion du rez-de-chaussée ou du 1er (étage inconnu non compté) ; DPE → retrait de la lettre écartée et des plus mauvaises ; commune / annonceur → exclusion ; meublé → critère inverse. « Aspect » et « autre » n'en déclenchent jamais.

Accepter enregistre le filtre modifié par le chemin d'édition des filtres existant (mêmes bornes, même validation) ; jamais appliqué sans confirmation. Refuser conserve le refus (critère, valeur, date) : la question ne revient qu'après 3 nouveaux écarts même raison. Proposée pour chaque filtre qui laisse encore passer ces logements.

**Blocked by:** 01, 02

**Status:** done (branche `feat/suggestions-critere`) ; ADR-0009 en vigueur depuis la livraison de 02 à 04 (2026-10-31)

- [ ] Seuil (3) en constante nommée ; service pur du domaine pour le calcul
- [ ] Test par raison : valeur suggérée et impact
- [ ] Test : un écart restauré ne compte pas
- [ ] Test : après un refus, pas de nouvelle question avant 3 nouveaux écarts même raison
- [ ] Test : accepter modifie le filtre enregistré et respecte ses bornes (`SearchFilter` refuse une valeur hors bornes)
- [ ] Test SQLite : les refus survivent à la purge
- [ ] Question vérifiée à l'œil dans la revue
- [ ] Shared Rules de `CLAUDE.md` (suggestions), glossaire *Suggestion de critère* en ✅, ADR-0009 « en vigueur » une fois les tickets 01 à 04 et 08 livrés
- [ ] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
