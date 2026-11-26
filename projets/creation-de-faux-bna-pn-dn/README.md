---
titre: "Création de faux BNA PN DN"
resume: "Skill Claude qui génère des BNAPN et BNADN fictifs, identiques en forme et en fonctionnement aux vrais formulaires Adobe, pour tester les outils de notation sans donnée réelle. Marqués FICTIF."
type: projet
usage: code-scripts
ia_compatibles: [claude]
langue: fr
niveau: intermediaire
statut: relu
version: 0.1
donnees: exemples-fictifs
filiation: original
version_plus_recente: aucune
licence: "[à définir]"
etiquettes: [bna, notation, donnees-fictives, pdf]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, aucun-appel-reseau]
auteur: "JF"
relu_par: "JF"
validation_ia: "Validé avec l'aide de l'IA, par JF, le 2026-10-30"
---

## Le problème résolu

Tester import_bna.html et extraction_bna.html exige des BNA qui se comportent comme de vrais formulaires Adobe, mais une vraie notation ne doit jamais servir de jeu d'essai. Ce skill fabrique des BNAPN et BNADN fictifs, marqués FICTIF, sans aucune donnée réelle, pour tester, former et démontrer devant un public. Il s'adresse aux concepteurs d'outils de notation et aux formateurs.

## Entrées et sorties

- **Ce que vous donnez** : Nombre de militaires (100 maximum par lot), répartition par grade, campagne, code d'unité fictif pour le nom des fichiers, et éventuellement le classeur modele_notation.xlsx à pré-remplir.
- **Ce que vous recevez** : Une paire BNAPN/BNADN vierge par militaire, au format de nommage réel, marquée FICTIF ; un fichier identites.xlsx (nom, prénom, grade, genre, catégorie, matricule fictif, noms de fichiers) ; le classeur de notation pré-rempli si demandé.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Documents maîtres issus du formulaire BNA en vigueur en 2018 ; à refaire si le formulaire évolue.
- Rendu pdf.js proche d'Adobe sans garantie ; seul Adobe sur Intradef fait foi.
- Adobe Reader peut refuser d'enregistrer les faux (signature droits Reader absente).
- Dépendances : pypdf, lxml, openpyxl ; qpdf facultatif.
- Contrôle visuel (rendu_bna.py, facultatif) : l'utilisateur installe une fois pdf.js (paquet npm pdfjs-dist, version 4.10.38) et Playwright avec Chromium ; aucun script ne télécharge rien ni ne contacte de service extérieur.
- Faux pour test uniquement : ne jamais les introduire dans un circuit réel.
- Le skill complet (SKILL.md, scripts/, maitres/) est fourni dans le zip joint au projet ; le champ contenu ne reprend que le SKILL.md.

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
