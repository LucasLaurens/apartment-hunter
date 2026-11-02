# Ajouter le crawler Bien'ici

Type: task
Status: resolved
Blocked by:

## Question

Ajouter Bien'ici comme source : API JSON publique `/realEstateAds.json` (zone département `-7407`, `covers_radius`), tous les champs sur la liste, aucune page détail. Avant d'écrire : lire ses conditions d'utilisation sur l'accès automatisé ; si elles l'interdisent, la source est rejetée et ce ticket le note. Bien'ici agrège des flux d'agences (Laforêt entre autres) : vérifier que `duplicates.py` regroupe bien les doublons. Corriger la ligne « Bien'ici = connexion » de `docs/functional/sources.md`. Détails : la recherche, § Bien'ici.

Recherche : [sources-accessibles.md](../research/sources-accessibles.md), branche `research/sources-annecy`. Livre du code (voir Notes de la map).

## Answer

**Rejetée** (décision du 2026-10-30), comme le ticket le prévoyait si les conditions d'utilisation interdisent l'accès automatisé.

Les CGU de Bien'ici ([mentions légales et CGU](https://www.bienici.com/informations-legales)) interdisent l'extraction automatisée à des fins commerciales non autorisées. À la lettre, un usage personnel et non commercial n'est pas visé. Elles interdisent aussi toute reproduction du contenu sans autorisation, et cette clause-là ne fait pas la distinction. Dans le doute, la source n'est pas collectée.

Le `robots.txt`, l'absence de compte et l'absence de défi auraient permis la collecte. La ligne « Bien'ici = connexion » de `docs/functional/sources.md` est corrigée en « rejetée, CGU ».
