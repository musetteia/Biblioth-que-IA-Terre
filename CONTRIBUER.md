# Contribuer

Tout le monde peut proposer un projet, sans compte et sans installer quoi que ce soit. Chaque proposition est relue avant d'apparaître sur le site.

## Proposer un projet

1. Ouvrez la page [Proposer un projet](proposer.html).
2. Remplissez les champs obligatoires : titre, pseudo, résumé et IA testées.
3. Ajoutez le contenu : glissez votre fichier dans le cadre prévu (prompt ou instructions en `.md` ou `.txt`, script en `.py`, skill en `.zip` ou `SKILL.md`), ou copiez-collez son texte. Pour un skill en `.zip`, seul `SKILL.md` est envoyé : si votre skill contient d'autres fichiers, dites-le dans le résumé et laissez une adresse de contact.
4. Cochez les quatre engagements : aucune donnée réelle, exemples fictifs, aucun nom ni adresse, aucun appel réseau.
5. Cliquez sur *Vérifier et préparer ma proposition*, puis sur *Envoyer ma proposition*.

C'est tout : vous n'avez plus rien à faire. Les noms, adresses électroniques, numéros de téléphone, clés et mentions de protection sont retirés automatiquement avant l'envoi. Les parties facultatives (problème résolu, étapes, exemples) seront complétées par la personne qui relit. Votre saisie est gardée dans votre navigateur jusqu'à l'envoi : vous pouvez fermer la page et revenir.

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
