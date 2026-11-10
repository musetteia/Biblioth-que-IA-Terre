---
titre: "test-fichette-anonymisee"
resume: "fichette"
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
etiquettes: [fiche, synthese, word, docx, powershell]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, aucun-appel-reseau]
auteur: "Clément"
relu_par: "Clément"
validation_ia: "Validé avec l'aide de l'IA, par Clément, le 2026-11-10"
---

## Le problème résolu

Rédiger une fiche de synthèse d'une page dans un format imposé (en-tête, encart de 5 à 8 lignes, trois parties rédigées) prend du temps, surtout pour tenir sur une seule page. Cette skill guide l'IA pour rédiger le texte dans ce format, l'assembler dans un modèle Word et contrôler la pagination et la longueur de l'encart. Elle s'adresse à une personne qui produit régulièrement des fiches au même format.

## Entrées et sorties

- **Ce que vous donnez** : Le sujet et l'angle, la date, l'auteur, le dossier des sources et le dossier de sortie.
- **Ce que vous recevez** : Un fichier Word d'une page (A4 paysage, deux colonnes) construit depuis le modèle, avec le résultat des contrôles de mise en page.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Les scripts d'assemblage et de contrôle, le modèle Word et l'exemple cités dans le texte ne figurent pas dans le contenu déposé : à confirmer par l'auteur.
- Les scripts exigent Windows PowerShell 5.1 et Word installé pour le contrôle de pagination.
- Le rendu visuel n'est pas vérifié, seulement la pagination et la longueur de l'encart.
- Le format (en-tête, trois parties, encart) est propre à un cadre précis et suppose un modèle Word fourni par l'utilisateur.
- Les chiffres viennent uniquement des sources désignées : ceux qui ne sont pas sourcés doivent être relus par l'utilisateur.

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
