# Fonctionnement

## Recueil du besoin
- qui: vous
- entrée: Nombre de militaires, grades, campagne, code d'unité, classeur oui/non
- sortie: Paramètres du lot

L'utilisateur donne ses besoins en un seul message. À défaut : tous CPL, année en cours, unité FIC_TST.

```exemple
18 militaires : CPL 10, CCH 5, SGT 3, campagne 2026, unité FIC_TST.
```

## Génération du lot
- qui: ia
- entrée: Paramètres du lot et maîtres fictifs
- sortie: PDF PN/DN par militaire, identites.xlsx, classeur pré-rempli

Claude lance faux_bna.py. Noms courants, une femme sur cinq, faux matricules et NI uniques.

```exemple
01_2026_BNAPN_CPL_Bernard_FIC_TST.pdf et 01_2026_BNADN_CPL_Bernard_FIC_TST.pdf.
```

## Contrôle anti-fuite
- qui: ia
- entrée: Lot généré et, si disponible, un vrai BNA de référence
- sortie: Verdict de contrôle

Claude compare les faux au vrai BNA. Le résultat attendu est « AUCUNE fuite ».

```exemple
36 fichiers contrôlés : AUCUNE fuite.
```

## Contrôle visuel
- qui: ia
- entrée: Un PDF du lot
- sortie: Capture PNG du BNA

Claude affiche le BNA comme Adobe (pdf.js) et vérifie le marquage FICTIF, le nom, le NI et le millésime.

```exemple
Capture montrant le titre rouge DOCUMENT FICTIF et « Bernard (FICTIF) ».
```

## Livraison et test
- qui: vous
- entrée: Zip des PDF et identites.xlsx
- sortie: BNA de test chargés dans les outils de notation

L'utilisateur charge les faux dans import_bna.html ou extraction_bna.html pour tester.

```exemple
Import de 18 notations fictives puis relecture dans extraction_bna.html.
```
