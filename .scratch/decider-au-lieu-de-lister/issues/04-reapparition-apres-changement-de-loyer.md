# 04: Réapparition après un changement de loyer

Spec : [Décider au lieu de lister](../../idee-produit/spec.md)

**What to build:** Un logement écarté dont le loyer change n'est plus reconnu : il réapparaît dans la revue, sur le web et dans l'alerte — une baisse de loyer est une information. Il porte la mention « écarté le … à N € (raison) », retrouvée par une comparaison sans le loyer (commune, pièces, surface) qui sert uniquement à afficher, jamais à masquer.

**Blocked by:** 01

**Status:** done

- [x] Test : un logement écarté republié avec un autre loyer réapparaît avec la mention, date, ancien total CC et raison compris
- [x] Test : la comparaison sans le loyer ne masque jamais rien
- [x] Test : un logement sans pièces ni surface ne reçoit jamais cette mention
- [x] Glossaire *Écarté* (loyer modifié) passé en ✅
- [x] `make full` vert (ruff, format, mypy strict, pytest) ; noms de fonctions verbe-premier ; tests AAA, fakes concrets, Faker
