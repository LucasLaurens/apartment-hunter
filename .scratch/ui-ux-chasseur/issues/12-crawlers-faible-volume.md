# Ajouter ou non les sources à faible volume

Type: grilling
Status: resolved
Blocked by:

## Question

ERA (1 annonce à Annecy), Capifrance (8 en 74), iad (5 en 74, remplissage hors département), Nestenn (2 ou 3 dans le rayon, DPE en image sur un chemin interdit) : valent-elles un crawler chacune, au regard de leur coût d'entretien ? Si oui, un lot ; corriger les lignes « SPA » d'ERA et Nestenn dans `docs/functional/sources.md`. Détails : la recherche.

Recherche : [sources-accessibles.md](../research/sources-accessibles.md), branche `research/sources-annecy`. Livre du code (voir Notes de la map).

## Answer

**Pas pour l'instant** (décision du 2026-10-30). ERA, Capifrance, iad et Nestenn ne comptent que 1 à 3 annonces chacune dans le rayon d'Annecy. Chaque crawler coûte de l'entretien (les changements des sites ont déjà demandé cinq corrections aux crawlers existants) pour presque rien. On les réexamine si leur stock grossit. Les lignes « SPA » d'ERA et de Nestenn dans `docs/functional/sources.md` sont corrigées : ce sont des pages rendues côté serveur, écartées pour leur volume.
