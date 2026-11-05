# Contribuer

Tout le monde peut proposer un projet, sans compte et sans installer quoi que ce soit. Chaque proposition est relue avant d'apparaître sur le site.

## Proposer un projet

1. Ouvrez la page [Proposer un projet](proposer.html).
2. Remplissez les champs obligatoires : titre, pseudo, résumé et IA testées.
3. Ajoutez le contenu : glissez votre fichier dans le premier cadre (prompt ou instructions en `.md` ou `.txt`, script en `.py`, skill en `.zip` ou `SKILL.md`), ou copiez-collez son texte. Pour un skill en `.zip`, seul `SKILL.md` est envoyé : si votre skill contient d'autres fichiers, dites-le dans le résumé.
4. Si votre projet a des documents liés (modèle, fiche, tableau), glissez-les dans le second cadre, « Pièces jointes » : Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`) ou PDF, 10 fichiers et 15 Mo au maximum. Les anciens formats (`.doc`, `.xls`, `.ppt`), les fichiers à macros, protégés par mot de passe ou contenant des objets incorporés sont refusés. Si un document ne contient que du texte, préférez le coller dans le champ du contenu (ou en `.md`) : c'est plus léger.
5. Cochez les quatre engagements : aucune donnée réelle, exemples fictifs, aucun nom ni adresse, aucun appel réseau.
6. Cliquez sur *Vérifier et préparer ma proposition*, puis sur *Envoyer ma proposition*.
7. Confirmez votre adresse : saisissez votre adresse professionnelle (`@intradef.gouv.fr` ou `@academie.def.gouv.fr`), un code à 6 chiffres vous est envoyé, saisissez-le. Le dépôt n'est envoyé qu'après cette confirmation. Votre adresse n'est jamais publiée.

C'est tout : vous n'avez plus rien à faire. Les métadonnées de personnes de vos pièces jointes (auteur, dernier enregistrement) sont remplacées par « [personne] » ; le contenu de vos documents n'est jamais modifié. Les noms, adresses électroniques, numéros de téléphone, clés et mentions de protection sont retirés automatiquement avant l'envoi. Les parties facultatives (problème résolu, étapes, exemples) seront complétées par la personne qui relit. Votre saisie est gardée dans votre navigateur jusqu'à l'envoi : vous pouvez fermer la page et revenir.

## Ce qui se passe ensuite

1. La proposition arrive par courriel chez les validateurs.
2. Un validateur la fait vérifier et compléter par Claude avec le skill `valider-depot`, puis dépose le fichier validé dans le dossier `validations/` du dépôt GitHub.
3. Un robot fabrique la fiche et la vérifie.
4. Un administrateur relit et publie. Rien n'apparaît sur le site avant cette étape.

## Pour le responsable : ajouter à la main une proposition reçue autrement

Si une proposition arrive par un autre chemin (fichier téléchargé depuis le formulaire), sous Windows, glissez le fichier `proposition-xxx.json` sur `ajouter.bat`. Sinon, dans un terminal :

`python outils/importer.py proposition-xxx.json`

L'outil crée le projet complet (fiche, fonctionnement, installation, exemples), le vérifie, puis propose de le publier. Si la vérification échoue, rien n'est ajouté et les problèmes sont listés : corrigez-les avec le contributeur.

Le projet arrive avec le statut « proposé ». Il n'est relevé que par un relecteur qui n'en est pas l'auteur (voir *Faire relire un projet*).

## Faire relire un projet

Demandez à un camarade de l'essayer avec les exemples. S'il valide, il inscrit son nom dans le champ `relu_par` de la fiche et passe le statut à « relu ».

## Adapter un projet existant

`python outils/nouveau.py ma-version --depuis synthese-conference`

La copie garde le lien vers l'original. Modifiez ce que vous voulez et re-attestez les contrôles. Cette méthode demande de modifier des fichiers à la main : elle s'adresse à ceux qui connaissent Git.

## Améliorer un projet publié

Modifiez les fichiers du projet, relancez `python outils/valider.py`, augmentez le numéro de version (1.0 vers 1.1 pour un ajustement, vers 2.0 pour un changement de fonctionnement) et décrivez le changement dans le message de commit.
