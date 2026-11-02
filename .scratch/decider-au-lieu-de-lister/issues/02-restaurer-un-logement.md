# 02: Restaurer un logement écarté

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Le chasseur bascule avec `d` (ou lance `hunt review --dismissed`) sur la vue des logements écartés, chacun avec sa raison, et restaure le sélectionné avec `u`. Le logement revient dans la revue, sur le web et dans l'alerte, marqué « restauré le … ». Écarté à nouveau, le nouvel écart remplace l'ancien (raison comprise) et la mention « restauré le … » disparaît.

**Blocked by:** 01

**Status:** done

- [x] Test : restaurer un logement le rend visible partout et produit la mention « restauré le … »
- [x] Test : réécarter un logement restauré remplace la raison et efface la mention
- [x] Test : un écart restauré n'est plus compté comme écart actif (préalable aux suggestions)
- [x] `d` bascule entre « à revoir » et « écartés » ; `u` n'agit que dans la vue des écartés ; `--dismissed` ouvre directement cette vue
- [x] Écran vérifié à l'œil sur la vraie base
- [x] README et glossaire *Écarté* (restauration) à jour
- [x] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
