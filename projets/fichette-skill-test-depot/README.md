---
titre: "Fichette-skill-test-depot"
resume: "Pour valider la nouvelle chaîne de dépôt."
type: skill
usage: synthese
ia_compatibles: [claude]
langue: fr
niveau: debutant
statut: relu
version: 0.1
donnees: exemples-fictifs
filiation: original
version_plus_recente: aucune
licence: "[à définir]"
etiquettes: [fichette, fiche]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, aucun-appel-reseau]
auteur: "Clément"
relu_par: "Clément"
validation_ia: "Validé avec l'aide de l'IA, par Clément, le 2026-11-06"
---

## Le problème résolu

Rediger une fiche de synthese d'une page a partir de plusieurs documents prend du temps, et la mise en page se degrade vite. Le skill structure le texte en trois parties avec un encart a retenir, assemble un .docx au format fixe et controle qu'il tient sur une page. Il s'adresse a toute personne qui produit regulierement des fiches de synthese.

## Entrées et sorties

- **Ce que vous donnez** : Un dossier de documents sources, le sujet et l'angle, la date, l'auteur et l'organisation.
- **Ce que vous recevez** : Une fiche Word d'une page (A4 paysage, 2 colonnes) avec en-tete, encart de 5 a 8 lignes et trois parties redigees, plus un compte rendu des controles.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Le skill a besoin de ses fichiers annexes (modele, exemple, scripts), absents du depot.
- Le controle de pagination exige Word installe sous Windows.
- Le rendu visuel n'est pas verifie par les scripts, seulement la pagination et la longueur de l'encart.
- Les chiffres de la fiche viennent des seules sources fournies et restent a relire par l'utilisateur.
- La limite d'une page oblige a des arbitrages sur les sujets tres denses.

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
