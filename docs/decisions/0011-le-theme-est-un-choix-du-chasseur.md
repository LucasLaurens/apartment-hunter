# ADR-0011 — Le thème est un choix du chasseur : Clair, Sombre ou Système

**Statut** : acceptée, implémentée — 2026-10-29. Amende le principe 3 de `PRODUCT.md`
(« One theme, chosen on purpose »).

## Contexte

`PRODUCT.md` imposait un thème unique, clair, pour une raison réelle : la page sert de
jour, quinze secondes à la fois, à comparer des chiffres. `DESIGN.md` refusait un
second thème pour une raison tout aussi réelle : ce serait une seconde copie de chaque
décision de couleur, qui dériverait.

Le chasseur consulte aussi la page le soir, et sur un appareil réglé en sombre. Un
écran clair à 23 h n'est pas « choisi exprès », il est subi.

## Décision

**Le thème se choisit dans une page Paramètres : Clair, Sombre ou Système (par
défaut), enregistré dans le navigateur ; chaque couleur s'écrit une seule fois, avec
ses deux valeurs côte à côte (`light-dark()`).**

## Conséquences

- L'objection de la double copie tombe sans être contournée : un token porte sa
  valeur claire et sa valeur sombre dans la même déclaration, et `color-scheme` sur
  `:root` choisit. « Système » est `color-scheme: light dark` ; il n'existe aucune
  branche `prefers-color-scheme`. `tests/presentation/test_theme_tokens.py` échoue sur
  une couleur écrite sans sa valeur sombre, et sur un second bloc de tokens.
- Le choix vit dans `localStorage` (`ah-theme`), pas en base : le thème dépend de
  l'appareil et de son éclairage, pas du chasseur. Un téléphone en sombre et un
  portable en clair coexistent.
- Un script dans le `<head>` d'`index.html` applique le choix avant le premier rendu :
  pas de flash du mauvais thème.
- Le budget de couleur (ticket 04) vaut pour les deux thèmes. Le sombre garde la teinte
  155 et l'échelle DPE lisible comme sur l'étiquette : pastille claire, lettre foncée.
- `make ui-check` mesure le contraste AA dans chaque thème, en rechargeant la page avec
  le choix enregistré ; `check_single_light_theme` disparaît.
- Navigateurs : `light-dark()` exige Chrome 123, Safari 17.5, Firefox 120.
- Le terminal (`hunt review`) n'est pas concerné : Rich hérite des couleurs du terminal.
- La page Paramètres naît avec le seul thème. Elle n'appelle pas d'autres réglages :
  elle leur fait de la place le jour où l'un existe.
