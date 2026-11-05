# Dossier des dépôts validés

Déposez ici **un seul fichier par dépôt** : `valide-xxx.json`, produit par le skill `valider-depot`.

1. Sur GitHub, ouvrez **d'abord** ce dossier `validations`, puis **Add file**, **Upload files** (depuis la page d'accueil du dépôt, le fichier irait à la racine et le robot l'ignorerait).
2. Glissez le fichier `valide-xxx.json`, jamais un .zip : les pièces jointes éventuelles (Word, Excel, PowerPoint, PDF) sont déjà à l'intérieur.
3. En bas, choisissez **Create a new branch for this commit and start a pull request**, puis **Propose changes**, puis **Create pull request**.
4. Le robot (suivi dans l'onglet **Actions**) fabrique le projet et l'ajoute à la demande de fusion. Une coche verte signale que tout est conforme ; une croix rouge affiche le motif dans l'onglet Actions.
5. Quand la coche verte apparaît, cliquez sur **Merge pull request** puis **Confirm merge** : la fusion publie le site. Le robot a refait tous les contrôles, y compris sur les pièces jointes.

Ne déposez jamais directement sur `main`, et jamais un fichier `proposition-xxx.json` non validé : le robot le refuserait.
Les fichiers traités sont rangés dans `traites/`.
