# ADR-0004 — « Passoire thermique » est une notion du domaine ; avertir, ne jamais masquer

**Statut** : acceptée, en vigueur — 2026-08-04

## Contexte

Le DPE n'est aujourd'hui qu'une valeur filtrable : `accepted_dpe_ratings`, un ensemble
de lettres. Le code ignore que F et G portent une conséquence légale — la loi Climat
et Résilience interdit progressivement leur mise en location (logements d'habitation,
France métropolitaine, nouveaux baux) :

| Classe | Interdite à la location depuis / à partir du |
|--------|---------------------------------------------|
| G | 1ᵉʳ janvier 2025 |
| F | 1ᵉʳ janvier 2028 |
| E | 1ᵉʳ janvier 2034 |

Un G reste publié et loué en pratique. Le masquer d'office reviendrait à décider à la
place du chasseur, sur la foi d'une étiquette parfois erronée ou périmée.

Cas voisin : beaucoup d'annonces n'ont pas de DPE du tout. L'explication la plus
fréquente est bénigne — le diagnostic n'a pas encore été fait par l'agence.

## Décision

**Passoire thermique** entre dans le vocabulaire du domaine, pas seulement dans le
glossaire : un logement classé F ou G en est une.

Une annonce F ou G est **affichée avec un avertissement daté** : « passoire thermique
— location interdite depuis le 01/01/2025 » (G), « — interdite à partir du
01/01/2028 » (F). Jamais masquée d'office.

Une annonce **sans DPE** reste affichée, passe les filtres DPE, et porte la mention
« DPE non communiqué ». L'absence n'est pas un signal négatif ; elle ne doit pas non
plus être confondue avec un bon classement.

Le calendrier réglementaire vit en un seul endroit du domaine, à côté de `DpeRating`.

## Conséquences

- Le domaine porte des dates légales. Elles changent par la loi, pas par le code :
  elles doivent être nommées, datées, et testées (un G est interdit aujourd'hui, un F
  ne l'est pas encore).
- L'avertissement dépend de la date courante. Une fonction pure prenant la date en
  paramètre, jamais `datetime.now()` enfoui.
- Le filtre DPE existant est conservé tel quel : cocher les lettres acceptées reste la
  façon d'exclure. L'avertissement s'ajoute, il ne filtre pas.
- Le GES n'emporte aucune interdiction : ne pas lui appliquer le même traitement.
- L'avertissement est du texte lisible, pas une couleur seule — cohérent avec la règle
  d'accessibilité qui impose lettre **et** couleur pour DPE et GES.
