# Ajouter le crawler EntreParticuliers

Type: task
Status: resolved
Blocked by:

## Question

Décidé le 2026-10-30 : **oui**. `Content-Signal: search=yes` couvre l'usage (recherche personnelle, aucun entraînement d'IA).

Décision d'abord (HITL) : son `robots.txt` autorise tous les robots mais nomme ClaudeBot, GPTBot et consorts avec « ai-train=no » ; le crawler du projet n'est pas un robot d'IA, mais l'utilisateur tranche en connaissance de cause. Si oui : page département `/annonces-immobilieres/location/appartement/haute-savoie-74?page=N`, détail pour DPE, GES, `datePosted`. Détails : la recherche, § EntreParticuliers.

Recherche : [sources-accessibles.md](../research/sources-accessibles.md), branche `research/sources-annecy`. Livre du code (voir Notes de la map).

## Answer

Implémenté sur `feat/crawler-entreparticuliers` (`b679213`), partie de `main`, non poussée.

- **Collecte** : page département, nom du département lu sur geo.api.gouv.fr. Les demandes de locataires sont écartées.
- **Page détail** : DPE, GES, `datePosted`, étage (dans la description) et puce « Meublé ».
- **Premier passage réel (2026-10-30)** : 168 annonces dans le 74.
  - Prix et date du site : 168 sur 168.
  - DPE et GES : 144.
  - Meublé : 102. Étage : 51.
- **Trouvé en route** : `parse_price_from_euro_node` écartait « 980 € /mois » comme un prix au m² et lisait 0 €. Corrigé dans la boîte à outils partagée, avec un test. Figaro, ParuVendu et Century21 utilisent la même fonction.
- **Limites** :
  - La source mêle particuliers et quelques professionnels (badge « Professionnel » sur la page détail, non lu) : elle est classée « mixte ».
  - Une carte ne dit pas si le loyer inclut les charges, d'où la marque « charges ? ».
