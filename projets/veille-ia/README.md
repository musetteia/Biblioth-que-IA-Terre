---
titre: "Veille IA"
resume: "Un Skill qui permet de générer une veille IA à partir de newsletters d'une boite mail GMAIL perso et de l'open source."
type: skill
usage: recherche-veille
ia_compatibles: [claude]
langue: fr
niveau: avance
statut: relu
version: 0.1
donnees: exemples-fictifs
filiation: original
version_plus_recente: aucune
licence: "[à définir]"
etiquettes: [veille, newsletters, gmail, synthese, grand-ecran]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, aucun-appel-reseau]
auteur: "Simon"
relu_par: "Simon"
validation_ia: "Validé avec l'aide de l'IA, par Simon, le 2026-10-29"
---

## Le problème résolu

Les newsletters sur l'IA s'accumulent dans la boîte mail et personne n'a le temps de toutes les lire. Ce skill les lit chaque jour, complète par des recherches web sourcées et en tire une synthèse courte classée en 7 axes, avec un niveau d'importance pour chaque information. Il s'adresse à quelqu'un qui anime une veille IA pour un public non spécialiste, en conversation sur téléphone ou sur un grand écran.

## Entrées et sorties

- **Ce que vous donnez** : Une boîte Gmail connectée à Claude, avec un libellé « Veille IA » qui regroupe les newsletters, et éventuellement une période.
- **Ce que vous recevez** : Une synthèse en grilles de lecture (7 axes, niveau de signal, bruit écarté, lecture croisée) et, sur demande, une édition de 6 diapositives pour grand écran.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Il faut connecter Gmail et avoir la recherche web ; l'édition grand écran demande aussi l'outil de publication de pages.
- La partie grand écran a besoin d'un gabarit, d'un glossaire et d'un script (dossiers assets/ et scripts/) qui ne sont pas fournis dans ce dépôt.
- Les adresses des expéditeurs ont été remplacées par nom@example.org : chaque utilisateur doit remettre les siennes.
- Le skill lit une vraie boîte mail et y ajoute un libellé : il traite donc des données réelles.
- Le texte reste propre à l'auteur (Cercle IA, liens vers des pages privées) et doit être adapté avant usage.

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
