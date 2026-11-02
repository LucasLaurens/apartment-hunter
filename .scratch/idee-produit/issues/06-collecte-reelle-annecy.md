# Démarrer la collecte réelle sur Annecy

Type: task
Status: resolved
Blocked by:

## Question

Lancer `hunt watch` sur un filtre réaliste pour que la base contienne de vraies annonces au moment de la lecture finale des 5 plus sous-cotées.

- Filtre : « Autour d'Annecy » existe déjà en base (`48569da5`, rayon 15 km, ≤ 1 250 €, ≥ 40 m², hors RDC et 1er, DPE A-D, intervalle 15 min).
- Lancer `hunt watch --filter "Autour d'Annecy"` et le laisser tourner.

## Answer

Lancé le 2026-09-25 à 15:14, onglet Terminal « hunt watch Annecy » : `uv run hunt watch --filter "Autour d'Annecy"`. Premier crawl OK (foncia 32 annonces sur 4 communes, century21 6 à Annecy).

Faits pour la suite :

- Le process s'arrête si l'app, le terminal ou la machine s'arrêtent : le relancer avec la même commande. La mise en veille met seulement la collecte en pause.
- La purge supprime toujours les annonces disparues : la base contient les annonces en ligne, pas un historique.
- Deux sources perdues dès le premier crawl, hors du périmètre de cette map : PAP (`No geo ID found for 'Annecy', skipping`, régression depuis le 2026-08-03) et Orpi (404 sur `location-immobiliere-epagny-metz-tessy`, slug d'une commune nouvelle). La collecte est donc partielle tant qu'elles ne sont pas corrigées.
