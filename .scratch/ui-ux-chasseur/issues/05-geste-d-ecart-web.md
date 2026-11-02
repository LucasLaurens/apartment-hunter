# Geste d'écart sur le web

Type: prototype
Status: resolved
Blocked by: 03

## Question

Comment écarte-t-on un logement depuis la page web, en moins d'une seconde quand la raison est évidente ?

- Déclencheur : bouton sur la carte, raccourci clavier, les deux ?
- Choix de la raison : liste fermée de l'ADR-0009 (8 raisons + « autre » avec texte libre), obligatoire ; sans modale par réflexe.
- Retour : la carte disparaît comment, et l'annulation immédiate (toast « Annuler ») ?
- Restauration : où voit-on les logements écartés côté web (pendant de `hunt review --dismissed`) ?

Même cas d'usage `DismissHome`, même règle de masquage par groupe de doublons. Prototype jetable à réagir, lié depuis ce ticket.

## Answer

**Variante B, avec un bouton sur chaque carte**, choisie sur prototype le 2026-10-29. Les trois variantes (raisons dans la carte, clavier et barre de raisons, menu et carte réduite) restent sur la branche `prototype/geste-ecart` (`858c5aa`).

- **Déclencheur** : les deux. Un bouton « × Écarter », d'aspect tertiaire, sur chaque carte, placé au-dessus du lien étendu pour qu'écarter n'ouvre jamais l'annonce. Au clavier, `j`/`k` passent d'une carte à l'autre et `x` ouvre la barre, comme dans `hunt review`.
- **Choix de la raison** : une barre unique, fixée en bas de page, sans modale. Elle reprend la liste fermée avec les touches de `hunt review` (1–8, 0). Le choix « autre » ajoute un champ libre étiqueté. `Échap` annule. Les raisons viennent du serveur (`/api/dismissal-reasons`), servies depuis la même liste que le terminal (`presentation/dismissal_reasons.py`).
- **Retour** : la page se recharge depuis le serveur, ce qui fait partir les doublons avec le logement. Le message « Écarté : … (raison) » propose « Annuler » pendant 6 s.
- **Annuler et restaurer** : c'est un seul geste, `RestoreHome`. Il pose `restored_at` : l'écart reste comme trace « déjà jugé une fois », mais ne masque plus et ne compte plus (ADR-0009).
- **Restauration** : la page « Écartés » de la barre latérale liste les écarts en vigueur, chacun avec « Restaurer ».
- **Routes** :
  - `POST /api/listings/{id}/dismiss` : 422 sur une raison inconnue ou sur un texte joint à une autre raison qu'« autre », 404 sur une annonce purgée ;
  - `GET /api/dismissals` ;
  - `DELETE /api/dismissals/{id}`.
- **Trouvé en route** :
  - Une recharge de la liste encore en cours effaçait une page latérale ouverte entre-temps. La vue est maintenant revérifiée quand la réponse arrive.
  - La réécriture de la carte (ticket 06) avait supprimé les styles de la modale, du toast, des formulaires et de la pagination. Ils sont restaurés (`f5e676a`), et un garde échoue désormais sur toute classe du markup sans règle.
- **Reste à faire** : la mention « écarté le … à N € » quand le loyer change (ADR-0009).
