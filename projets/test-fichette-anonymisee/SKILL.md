---
name: fichette
description: Construit une fiche EDG-T d'une page (format "fichette") pour son utilisateur, à partir du canevas Modele-fichette et du style de la fiche LPM v3. À utiliser quand il demande de créer, rédiger, refaire ou mettre en forme une fiche, une fichette, une fiche de synthèse ou de préparation de séance EDG-T, ou de "faire comme la fiche LPM".
---

# Skill fichette

Produit un `.docx` d'une page (A4 paysage, 2 colonnes, Arial 11) à partir du canevas `assets/modele-fichette.docx`. Le style de référence est `assets/exemple-fiche-LPM-v3.docx` (version retouchée par l'utilisateur, son texte source est dans `assets/exemple-fiche-LPM-v3.content.txt`). **Lis ces deux éléments avant de rédiger** : l'exemple montre le niveau de densité, de narratif et de précision attendu.

## Déroulé

1. **Fraîcheur du canevas.** Si `Modele-fichette.docx` existe dans `<dossier-du-modele>\`, compare son hash (`Get-FileHash`) à `assets/modele-fichette.docx`. S'ils diffèrent, dis-le à l'utilisateur et propose de remplacer la copie de la skill (relis alors les commentaires Word, qui portent les consignes).
2. **Cadrage.** Si ce n'est pas déjà clair, demande : sujet et angle, date, auteur (par défaut `GRADE NOM`), dossier des sources, dossier de sortie. Les données viennent **uniquement des dossiers désignés par l'utilisateur** : ne cherche pas ailleurs sauf demande explicite. Signale tout chiffre que tu ne peux pas sourcer.
3. **Rédaction** dans un fichier de contenu (UTF-8) au format de l'exemple (`AUTEUR|`, `DATE|`, `OBJET|`, `ENCART|`, `H|` titre de partie, `P|` paragraphe avec `**gras**`). Fichier de travail dans le scratchpad, pas dans les dossiers de l'utilisateur.
4. **Assemblage** : 
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\build_fiche.ps1" -Content <contenu.txt> -Output <dossier>\AAAAMMJJ_NP_Fiche-<Sujet>.docx
   ```
   Le script construit la fiche depuis le modèle (en retirant les commentaires du modèle) puis lance `scripts/check_fiche.ps1`. Il refuse d'écraser un fichier existant : pour une nouvelle version, utilise `_v2`, `_v3`.
5. **Corriger** selon les lignes `ATTENTION` du contrôle (débordement de page, encart hors de 5 à 8 lignes, tiret long, résidu du modèle, trop de gras), puis relancer sous un nouveau nom ou après avoir supprimé le brouillon que tu as toi-même créé.
6. **Passe Opus facultative** (style et enchaînements) : voir `references/passe-opus.md`. À proposer, pas à imposer.
7. **Compte rendu** : chemin du fichier, résultat des contrôles, points de rédaction à valider (chiffres sensibles, reformulations de ton fait). Le rendu visuel n'est pas vérifié par les scripts (seulement pagination et longueur d'encart) : dis-le.

## Règles du canevas (issues des commentaires du modèle)

- **En-tête** : `EDG-T/Groupe 2`, grade et nom de l'auteur, date, mot `FICHE`, `OBJET :`. Ne pas toucher à la structure.
- **Encart** (`ENCART`) : « si vous ne deviez retenir que ça ». Il doit faire **5 à 8 lignes** une fois mis en page et permettre de comprendre l'idée maîtresse et les éléments les plus saillants seul (chiffres acceptés). Écrit en dernier, une fois le corps stabilisé.
- **Trois parties** (`H|`) : (1) contexte général ; (2) enjeux, éléments plus concrets ou actualité, solutions décrites légèrement (3 maximum en général) ; (3) conclusions, perspectives, ou solution à privilégier parmi celles de la partie 2. Sous-parties possibles, jamais systématiques.
- **Chaque partie est un narratif** : une suite logique d'arguments reliés par des connecteurs, pas une énumération. Chaque paragraphe pose son idée principale d'emblée, la partie 3 prolonge explicitement la 1 et la 2.
- **Gras** sur les éléments saillants uniquement : idées maîtresses et chiffres clés (quelques passages par paragraphe, ni zéro ni une dizaine).
- Schémas possibles s'ils sont très simples (non gérés par le script : à insérer à la main si besoin).

## Style de l'utilisateur

- Français, direct, sans tirets longs (virgules ou points).
- Précision factuelle avant l'effet de style : l'utilisateur corrige les formulations approximatives (par exemple « la Défense », périmètre exact d'un chiffre, intitulé d'un scénario). Ses retouches sur l'exemple font foi sur le fond.
- Tout ce que dit la fiche vient des sources fournies ; une reformulation qui ajoute une interprétation doit être signalée.
- Titre de partie sous la forme « Sujet : thèse » (ex. « Perspectives post-2027 : une trajectoire votée mais pas acquise »).

## Pièges techniques (Windows PowerShell 5.1)

- Les scripts `.ps1` sont **ASCII uniquement** : 5.1 lit les fichiers sans BOM en ANSI. Ne pas y mettre d'accents ni de tirets typographiques (utiliser `[char]0x2014`).
- PowerShell ne distingue pas `$f` de `$F` : ne pas réutiliser un nom de variable avec une casse différente.
- `$env:TEMP` peut être en nom court (8.3) : normaliser avec `(Get-Item $path).FullName` avant de découper des chemins.
- Le contrôle de pagination exige Word installé (COM) ; il ouvre le fichier en lecture seule et quitte Word à la fin.
