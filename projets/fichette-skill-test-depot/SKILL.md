---
name: fichette-test-depot
description: Version anonymisée et dépersonnalisée de la skill fichette, destinée à être déposée ou testée ailleurs. Construit une fiche d'une page (format "fichette") à partir d'un canevas neutre et d'un exemple fictif. À utiliser quand on demande de créer, rédiger, refaire ou mettre en forme une fiche, une fichette ou une fiche de synthèse d'une page avec cette version de test.
---

# Skill fichette-test-depot

Produit un `.docx` d'une page (A4 paysage, 2 colonnes, Arial 11) à partir du canevas `assets/modele-fichette-test.docx`. Le style de référence est `assets/exemple-fiche.docx` (texte source dans `assets/exemple-fiche.content.txt`). **Tout y est fictif** (organisation, chiffres, noms) : l'exemple ne sert qu'à montrer le niveau de densité, de narratif et de précision attendu. **Lis ces deux éléments avant de rédiger.**

Cette skill ne contient aucune donnée personnelle, aucun nom, aucun chemin propre à un utilisateur et aucun commentaire ni métadonnée d'origine.

## Déroulé

1. **Cadrage.** Si ce n'est pas déjà clair, demande : sujet et angle, date, auteur (par défaut `GRADE NOM`, à remplacer), organisation à indiquer en en-tête, dossier des sources, dossier de sortie. Les données viennent **uniquement des dossiers désignés par l'utilisateur** : ne cherche pas ailleurs sauf demande explicite. Signale tout chiffre que tu ne peux pas sourcer.
2. **Rédaction** dans un fichier de contenu (UTF-8) au format de l'exemple (`AUTEUR|`, `DATE|`, `OBJET|`, `ENCART|`, `H|` titre de partie, `P|` paragraphe avec `**gras**`). Fichier de travail dans le scratchpad, pas dans les dossiers de l'utilisateur.
3. **Assemblage** :
   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\build_fiche.ps1" -Content <contenu.txt> -Output <dossier>\AAAAMMJJ_Fiche-<Sujet>.docx
   ```
   Le script construit la fiche depuis le modèle puis lance `scripts/check_fiche.ps1`. Il refuse d'écraser un fichier existant : pour une nouvelle version, utilise `_v2`, `_v3`.
4. **Corriger** selon les lignes `ATTENTION` du contrôle (débordement de page, encart hors de 5 à 8 lignes, tiret long, résidu du modèle, trop de gras), puis relancer sous un nouveau nom ou après avoir supprimé le brouillon créé par toi-même.
5. **Passe de relecture facultative** (style et enchaînements) : voir `references/passe-relecture.md`. À proposer, pas à imposer.
6. **Compte rendu** : chemin du fichier, résultat des contrôles, points de rédaction à valider (chiffres sensibles, reformulations de ton fait). Le rendu visuel n'est pas vérifié par les scripts (seulement pagination et longueur d'encart) : le dire.

## Règles du canevas

- **En-tête** : organisation (`ORGANISME/Groupe X` dans le modèle, à adapter dans le .docx si besoin), grade et nom de l'auteur, date, mot `FICHE`, `OBJET :`. Ne pas toucher à la structure.
- **Encart** (`ENCART`) : « si vous ne deviez retenir que ça ». Il doit faire **5 à 8 lignes** une fois mis en page et permettre de comprendre l'idée maîtresse et les éléments les plus saillants seul (chiffres acceptés). Écrit en dernier, une fois le corps stabilisé.
- **Trois parties** (`H|`) : (1) contexte général ; (2) enjeux, éléments plus concrets ou actualité, solutions décrites légèrement (3 maximum en général) ; (3) conclusions, perspectives, ou solution à privilégier parmi celles de la partie 2. Sous-parties possibles, jamais systématiques.
- **Chaque partie est un narratif** : une suite logique d'arguments reliés par des connecteurs, pas une énumération. Chaque paragraphe pose son idée principale d'emblée, la partie 3 prolonge explicitement la 1 et la 2.
- **Gras** sur les éléments saillants uniquement : idées maîtresses et chiffres clés (quelques passages par paragraphe, ni zéro ni une dizaine).
- Schémas possibles s'ils sont très simples (non gérés par le script : à insérer à la main si besoin).

## Style attendu

- Français, direct, sans tirets longs (virgules ou points).
- Précision factuelle avant l'effet de style : périmètre exact d'un chiffre, intitulé exact d'un scénario, pas de formulation approximative.
- Tout ce que dit la fiche vient des sources fournies ; une reformulation qui ajoute une interprétation doit être signalée.
- Titre de partie sous la forme « Sujet : thèse » (ex. « Perspectives post-2029 : une trajectoire votée mais pas acquise »).

## Pièges techniques (Windows PowerShell 5.1)

- Les scripts `.ps1` sont **ASCII uniquement** : 5.1 lit les fichiers sans BOM en ANSI. Ne pas y mettre d'accents ni de tirets typographiques (utiliser `[char]0x2014`).
- PowerShell ne distingue pas `$f` de `$F` : ne pas réutiliser un nom de variable avec une casse différente.
- `$env:TEMP` peut être en nom court (8.3) : normaliser avec `(Get-Item $path).FullName` avant de découper des chemins.
- Le contrôle de pagination exige Word installé (COM) ; il ouvre le fichier en lecture seule et quitte Word à la fin.
- Le script d'assemblage retrouve l'auteur et la date dans le modèle par leur début de texte (`GRADE`, `Le `) : si le modèle est modifié, conserver ces deux débuts.
