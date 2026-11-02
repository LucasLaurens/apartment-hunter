# États de la page web

Type: grilling
Status: resolved
Blocked by:

## Question

Que dit la page dans chacun de ses états, pour que l'écran ne mente jamais sur sa fraîcheur ? Constats de l'audit (ticket 03) :

- **W2** : « Mis à jour à 7h22 » affiche l'heure du navigateur, pas celle du dernier crawl.
- **W3** : un crawl en cours n'indique pas l'état par source (en cours, finie, vide, en échec). Le ticket 13 a ajouté les sources injoignables, mais pas l'état du crawl en direct.
- **W11** : la surveillance et la suppression de filtre ne lisent pas la réponse du serveur.
- **W27** : « Crawl en cours… » est un mot anglais à l'écran.

À trancher : quelle heure afficher (dernier crawl réussi par filtre ? par source ?), où vit l'état par source pendant un crawl, et quels mots.

## Answer

Grilling du 2026-10-30. Les quatre recommandations sont retenues et implémentées sur `feat/etats-page`, à la suite de la pile.

- **W2** : « Dernière recherche : il y a 12 min », calculée par le serveur à partir de la réponse la plus récente d'une source pour ce filtre (`ListingPage.last_searched_at`). Avant toute recherche : « Pas encore de recherche ».
- **W3** : `CrawlAllSources` signale l'avancement de chaque source (en cours, trouvées, aucune, échec ; un dépassement de délai compte comme un échec) par un rapporteur. La CLI et la veille passent `ignore_progress`. La recherche lancée depuis le web le garde, et `/api/search/status` le renvoie. La page affiche une étiquette neutre par source sous la barre de résultats, qui disparaît en fin de recherche.
- **W11** : lancer ou arrêter la surveillance, et supprimer un filtre, lisent maintenant la réponse du serveur. Une erreur s'affiche avec l'icône d'alerte, et l'écran ne change pas. Les autres messages d'erreur ont perdu la coche de succès (W10, en partie).
- **W27** : « Recherche en cours… ».
- **Vérifié** : 4 nouveaux tests (avancement par source, statut par filtre, heure de dernière recherche). Rendu contrôlé en clair et en sombre, avec un statut de recherche et un échec de surveillance simulés dans le navigateur, puis une heure réelle en base.
