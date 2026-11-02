# Quelles sources sont accessibles autour d'Annecy ?

Type: research
Status: resolved
Blocked by:

## Question

Quelles sources d'annonces de location, au-delà des 9 actives, peut-on crawler autour d'Annecy (74) dans les limites de la map (robots.txt respecté, pas de CAPTCHA, pas de compte) ?

À évaluer, avec pour chacune un verdict (retenue / rejetée + raison) et, si retenue, la route, le format (SSR, JSON, SPA), les champs disponibles (prix, charges, surface, pièces, étage, DPE, GES, date, meublé) et le volume observé :

- **Jinka** et **Bien'ici** : accessibles sans connexion ?
- Les SPA rejetées en août 2026, réévaluées maintenant que `PlaywrightCrawler` existe : ERA, Nexity, SquareHabitat, Stéphane Plaza, Nestenn, Guy Hoquet, Avendrealouer.
- Toute autre source pertinente pour la Haute-Savoie (agences locales, portails régionaux).

Sources déjà jugées, à ne pas refaire sauf fait nouveau : L'Adresse (`robots.txt: Disallow: /`), SuperImmo, immoregion.fr, Arthur Immo, immojeune, acheter-louer, vivastreet, fnaim, notaires.

## Answer

Recherche complète : [sources-accessibles.md](../research/sources-accessibles.md) sur la branche `research/sources-annecy` (non poussée). Instantané du 2026-10-28, `robots.txt` lu pour chaque site, 2 à 6 requêtes espacées par site, aucun compte, aucun CAPTCHA.

- **Retenues, fort volume** : **Bien'ici** (API JSON publique sans connexion, tous les champs sur la liste, 83 à Annecy, 309 en 74), **Square Habitat** (SSR Angular, `ng-state`, 16 autour d'Annecy), **EntreParticuliers** (SSR + JSON-LD, particuliers, complète PAP).
- **Retenues, faible volume** : ERA (1 à Annecy), Capifrance (8 en 74), iad (5 en 74, page remplie hors département), Nestenn (2 ou 3 dans le rayon).
- **Rejetées** : Jinka (application derrière connexion), Leboncoin (première page servie, puis challenge DataDome), Logic-Immo et Avendrealouer (DataDome), Ouest-France Immo (`robots.txt`), Stéphane Plaza, Guy Hoquet, Oralia, Cimm (pas de stock autour d'Annecy), Nexity (pas de location publiée).
- **À trancher par l'utilisateur** : le `robots.txt` d'EntreParticuliers autorise tous les robots mais nomme les robots d'IA (« ai-train=no ») ; le crawler du projet n'en est pas un. Les conditions d'utilisation de Bien'ici sur l'accès automatisé n'ont pas été lues.
- **Doc à corriger par les tickets de collecte** : `docs/functional/sources.md` rejette encore Bien'ici (connexion) et ERA, Square Habitat, Nestenn (SPA).
