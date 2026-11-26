---
name: creation-faux-bna
description: "Création de faux BNA PN DN : génère des BNAPN et BNADN fictifs, identiques en forme et en fonctionnement aux vrais formulaires Adobe, pour tester les outils de notation (import_bna, extraction_bna) sans aucune donnée réelle."
---

# Création de faux BNA PN DN — v1.1

## Objectif

Produire des **BNA de test** (BNAPN et BNADN) qui se comportent exactement comme de vrais BNA dans les outils `import_bna.html` et `extraction_bna.html`, sans jamais contenir de donnée réelle. Usage : tester, former, démontrer.

## Règles absolues

1. **Jamais de donnée réelle dans un faux.** Les faux sont fabriqués uniquement à partir des **maîtres fictifs** du dossier `maitres/`.
2. **Tout faux est marqué FICTIF** : titre du PN « BULLETIN DE NOTATION ANNUELLE — DOCUMENT FICTIF » en rouge ; bandeau rouge « BNADN — DOCUMENT FICTIF — TEST UNIQUEMENT » et nom du militaire sur le DN ; « (FICTIF) » à côté du nom sur le PN. Ne jamais retirer ce marquage.
3. **Faux numéros** : matricule, NI, identifiants SAP sont inventés (préfixes 91… et 8…), uniques par militaire.
4. **Usage de test uniquement** : ne jamais introduire un faux dans un circuit réel (Concerto, GE, signatures).
5. Si l'utilisateur fournit un **vrai BNA** (pour refaire un maître) : ne jamais afficher son contenu, ne jamais le copier dans une sortie, supprimer les copies de travail à la fin.

## Contenu du skill

| Fichier | Rôle |
|---|---|
| `maitres/BNAPN_maitre_FICTIF.pdf` | Maître PN vierge, identité MAITRE Fictif |
| `maitres/BNADN_maitre_FICTIF.pdf` | Maître DN vierge |
| `scripts/faux_bna.py` | Génération des lots, création d'un nouveau maître, contrôle anti-fuite |
| `scripts/rendu_bna.py` | Capture PNG d'un BNA tel qu'Adobe l'affiche (pdf.js) |

Dépendances : `pypdf`, `lxml`, `openpyxl` (pip, avec `--break-system-packages` si besoin) ; `qpdf` facultatif (compacte les PDF) ; pour le rendu : Python `playwright` avec Chromium et pdf.js (paquet npm `pdfjs-dist`, version 4.10.38), à installer une fois par l'utilisateur dans `~/.cache/rendu_bna` ou dans un autre dossier passé par `--dossier-pdfjs` (commande exacte affichée par `rendu_bna.py`). Aucun script ne télécharge quoi que ce soit ni ne contacte un service extérieur.
Toujours lancer les scripts avec `python3 -I`, en copiant d'abord le dossier du skill dans le répertoire de travail si le chemin du skill est en lecture seule.

## Déroulé

### 1. Recueillir le besoin (en un seul message)
- Nombre de militaires (100 au maximum par lot, gabarit des outils de notation).
- Répartition par grade (ex. : CPL 10, CCH 5, SGT 3) ; à défaut, tous CPL.
- Campagne (année, défaut : année en cours) et code d'unité pour le nom des fichiers (défaut `FIC_TST`).
- Classeur `modele_notation.xlsx` à pré-remplir (noms réels fictifs, prénoms, grades, genre, catégorie) : oui / non.

### 2. Générer le lot
```bash
python3 -I scripts/faux_bna.py lot --n 18 --grades CPL:10,CCH:5,SGT:3 --annee 2026 --unite FIC_TST \
        [--modele modele_notation.xlsx] [--debut 1] --sortie lot_fictif/
```
Produit :
- `NN_AAAA_BNAPN_GRADE_Nom_UNITE.pdf` et `NN_AAAA_BNADN_…` : une paire vierge par militaire, au format de nommage réel ;
- `identites.xlsx` : nom, prénom, grade, genre, catégorie, matricule fictif, noms des deux fichiers ;
- `notation_lot_fictif.xlsx` (si `--modele`) : le classeur de notation avec « Nom réel », « Prénom », « Grade », « Genre », « Catégorie » remplis. Les autres colonnes (pseudo, cotations, textes) restent à remplir, par exemple avec le skill notation-bna.
- `--debut` décale la numérotation pour enchaîner plusieurs lots sans doublon.

Femmes : un militaire sur cinq (prénom féminin, genre F). Noms : liste de patronymes courants, suffixés au-delà de 50.

### 3. Contrôler
- Contrôle anti-fuite, si un vrai BNA de référence est disponible :
  `python3 -I scripts/faux_bna.py controle --reference vrai_PN.pdf vrai_DN.pdf --fichiers lot_fictif/*.pdf` → doit afficher « AUCUNE fuite ».
- Contrôle visuel : `python3 -I scripts/rendu_bna.py lot_fictif/<fichier>.pdf capture.png`, puis regarder la capture (titre ou bandeau FICTIF, nom, NI, millésime). Si pdf.js n'est pas installé, le script s'arrête et indique la commande à lancer : la proposer à l'utilisateur, ne pas l'installer à sa place.

### 4. Livrer
Envoyer les PDF (zip conseillé) et `identites.xlsx`. Rappeler : faux pour test uniquement ; enregistrement possible dans Acrobat Pro et par les outils HTML ; Adobe Reader peut refuser d'enregistrer (signature « droits Reader » absente des faux).

## Refaire un maître (formulaire BNA modifié)

Seulement si l'utilisateur signale un changement du formulaire et fournit un vrai BNAPN et un vrai BNADN récents :
```bash
python3 -I scripts/faux_bna.py maitre --pn vrai_PN.pdf --dn vrai_DN.pdf --sortie maitres/
```
Le script :
- garde la structure (libellés, codes, arborescence) par **liste blanche** et efface tout le reste (identité, NIR, état civil, famille, unité, cotations, textes) ;
- supprime le paquet « form » (copie des valeurs) et la signature Reader ;
- réécrit le fichier en entier (les anciennes révisions disparaissent) ;
- ajoute le marquage FICTIF et l'identité MAITRE Fictif ;
- vérifie qu'aucune valeur réelle ne subsiste, y compris dans les flux décompressés ; en cas de fuite : **échec, maître inutilisable**.

Puis : contrôle visuel des deux maîtres avec `rendu_bna.py`, et livraison du skill mis à jour (nouveaux maîtres dans `maitres/`, version incrémentée).

## Ce que les faux permettent de tester

- `import_bna.html` : rattachement par nom réel, remplacement du pseudo, écriture et relecture, garde-fous, noms de fichiers conservés, charge (jusqu'à 500 militaires testés).
- `extraction_bna.html` : lecture, rapprochement PN/DN par matricule et année, analyse, export.
- Rendu : après import, `rendu_bna.py` montre les croix, la QSR, la CCPG, les textes et le notateur à leur place.

## Limites connues

- Les maîtres viennent du formulaire BNA en vigueur en 2018, réputé inchangé ; à refaire si le formulaire évolue.
- Rendu pdf.js : très proche d'Adobe, sans garantie absolue ; seul Adobe sur Intradef fait foi.
- Le BNADN n'occupe que le bas de la page (comme le vrai) ; le bandeau FICTIF et le nom y ont été ajoutés au-dessus du formulaire.

## Journal des versions
- **v1.1** (octobre 2026) : `rendu_bna.py` n'installe plus pdf.js lui-même ; l'utilisateur l'installe une fois, et aucun script ne contacte de service extérieur.
- **v1.0** (octobre 2026) : maîtres PN et DN fictifs ; génération de lots au nommage réel avec identités et classeur pré-rempli ; marquage FICTIF (titre PN, bandeau et nom DN, « (FICTIF) » à côté du nom) ; faux matricules, NI et identifiants SAP ; contrôle anti-fuite ; création d'un maître à partir de vrais BNA ; rendu visuel par pdf.js.
