# Paramètres web et thème Clair / Sombre / Système

Type: prototype
Status: resolved
Blocked by: 04

## Question

Où vivent les paramètres sur la page web, et comment le thème s'y choisit ?

- Emplacement : panneau, page, entrée dans l'en-tête ? Une page qui naît avec un seul réglage.
- Stockage du choix : préférence locale au navigateur ou en base (mono-utilisateur, local) ? Valeur par défaut : Clair ou Système ?
- Tokens sombres en OKLCH dans `DESIGN.md` : même teinte 155, même budget de couleur (selon le ticket 04), contraste AA, DPE/GES lisibles sur fond sombre.
- Garde-fous : `check_single_light_theme` remplacé par une vérification AA dans chaque thème ; pas de flash du mauvais thème au chargement.

À la résolution : ADR-0011 (le thème devient un choix de l'utilisateur, amende le principe 3 de `PRODUCT.md`), `PRODUCT.md` et `DESIGN.md` mis à jour.

## Answer

**Variante C, une page Paramètres**, choisie sur prototype le 2026-10-29. Les trois variantes (engrenage dans l'en-tête, réglage permanent dans la barre latérale, page Paramètres) restent sur la branche `prototype/parametres-theme` (`f3b354f`).

- **Emplacement** : une entrée « Paramètres » en pied de barre latérale ouvre une page dans la zone principale. On y trouve trois cartes radio avec aperçu (Système montre les deux moitiés) et un bouton « Retour aux résultats ». Pendant la lecture de cette page, un rafraîchissement de veille ou de crawl ne la remplace plus par la liste. La page naît avec le seul thème.
- **Stockage et défaut** : `localStorage` (`ah-theme`), Système par défaut. Le thème dépend de l'appareil, pas du chasseur. Recommandation retenue avec la variante, sans réponse séparée sur ces deux points.
- **Tokens** : chaque couleur s'écrit `light-dark(clair, sombre)`, sans second bloc ni `prefers-color-scheme`. Même teinte 155. En sombre, les pastilles DPE restent claires avec une lettre foncée.
- **Garde-fous** :
  - `test_theme_tokens.py` échoue sur une couleur sans valeur sombre, sur un second bloc de tokens, et sur une clé de stockage qui diverge entre le script du `<head>` et l'audit. Ces trois cas ont été cassés exprès : la suite est passée au rouge.
  - `make ui-check` mesure l'AA dans chaque thème après rechargement, et vérifie que le thème enregistré est appliqué au chargement.
- **Documents** : [ADR-0011](../../../docs/decisions/0011-le-theme-est-un-choix-du-chasseur.md), `PRODUCT.md` (principe 3 et scène physique), `DESIGN.md` (§ Theme, colonne Dark), `conventions.md`, README.
- **Non vérifié** : Safari et Firefox. `light-dark()` exige Safari 17.5 et Firefox 120.
