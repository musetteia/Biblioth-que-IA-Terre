# Valider un dépôt avec l'aide de l'IA

Vous êtes validateur : vous recevez les dépôts par courriel. Vous n'avez besoin ni du dossier du projet, ni de connaître Git pour l'étape de validation : il suffit du fichier joint au courriel et du skill **valider-depot**.

## 1. Installer le skill (une seule fois)
1. Téléchargez le fichier `valider-depot.zip` : https://github.com/musetteia/Biblioth-que-IA-Terre/raw/main/outils-validation/valider-depot.zip
2. Dans Claude, **Paramètres**, **Capacités** : activez **Exécution de code et création de fichiers**. Sur une offre d'équipe ou d'entreprise, c'est un propriétaire du compte qui l'active.
3. Dans Claude, **Customize** (Personnaliser), **Skills** : cliquez sur **+**, puis **Create skill**, puis **Upload a skill**, et choisissez `valider-depot.zip`. Les libellés peuvent varier selon la version.
4. Vérifiez que le skill apparaît dans la liste, et qu'il est activé. L'offre gratuite de Claude suffit.

Sur Claude Code : copiez le dossier `valider-depot` dans `~/.claude/skills/`.

## 2. Valider un dépôt (à chaque courriel)
1. Ouvrez le courriel « [Bibliothèque IA] Dépôt : … » et enregistrez le fichier joint `proposition-….json`.
2. Ouvrez une conversation Claude et glissez le fichier dedans.
3. Écrivez : **Valide ce dépôt avec le skill valider-depot.**
4. Claude présente ce qui a été retiré et ce qu'il complète, vous demande votre pseudo de validateur, puis vous remet **un seul fichier** : `valide-….json`. La fiche de validation s'affiche dans la conversation (elle est aussi rangée dans le fichier).
5. Relisez la fiche. Si quelque chose ne va pas, dites-le dans la conversation : il corrige et refait le fichier.
6. Si le résumé indique qu'un skill comportait d'autres fichiers (scripts, références), le formulaire n'a transmis que `SKILL.md` : demandez le reste à l'auteur, à l'adresse de contact indiquée dans le courriel.

## 3. Déposer le résultat (compte GitHub avec droit d'écriture)
1. Sur GitHub, ouvrez le dossier `validations` du dépôt de la bibliothèque (https://github.com/musetteia/Biblioth-que-IA-Terre/tree/main/validations), puis **Add file**, **Upload files**.
2. Glissez le fichier unique `valide-….json`.
3. En bas, choisissez **Create a new branch for this commit and start a pull request**, puis **Propose changes**, puis **Create pull request**.
4. Le robot fabrique le projet et l'ajoute à la demande de fusion (suivi dans l'onglet **Actions** : coche verte = conforme, croix rouge = motif affiché).
5. Rien n'est publié avant la fusion par un administrateur.

## Ce que le skill ne fait jamais
- Il ne modifie pas le contenu du contributeur (prompt, skill, code) : il le copie tel quel, aux éléments épurés près.
- Il n'écrase pas ce que le contributeur a renseigné.
- Il ne publie rien, n'envoie rien, n'accède à aucun réseau.
- Il refuse de produire le fichier si un nom de personne (prénom et nom), un marquage, une adresse, un téléphone ou une clé subsiste.

Si une clé ou un mot de passe figurait dans le dépôt, il a déjà circulé par courriel : prévenez l'auteur pour qu'il la révoque.
