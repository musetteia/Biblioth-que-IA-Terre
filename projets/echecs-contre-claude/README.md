---
titre: "Échecs contre Claude"
resume: "Application pour jouer aux échecs contre Claude, avec jauges d'évaluation pendant la partie, analyse Stockfish après la partie et bilan de tes biais."
type: application
usage: analyse-documents-donnees
ia_compatibles: [claude]
capacites: [sample, db]
langue: fr
niveau: debutant
statut: relu
version: 0.1
donnees: exemples-fictifs
filiation: original
version_plus_recente: aucune
licence: "[à définir]"
etiquettes: [echecs, jeu, analyse, stockfish]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, seul-appel-claude]
auteur: "Adrian"
relu_par: "Adrian"
validation_ia: "Validé avec l'aide de l'IA, par Adrian, le 2026-11-26"
---

## Le problème résolu

Jouer aux échecs contre Claude, suivre l'évaluation de la partie en direct, puis comprendre ses erreurs : analyse par Stockfish après la partie, rejeu commenté des meilleurs et pires coups, détection des biais récurrents et estimation du niveau. Pour toute personne qui veut progresser aux échecs avec son propre compte Claude.

## Entrées et sorties

- **Ce que vous donnez** : Un clic pour lancer une partie, ou des parties collées au format PGN.
- **Ce que vous recevez** : Une partie jouée contre Claude, ses jauges, l'analyse après-partie et un bilan de tes biais et de ton niveau.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Fonctionne uniquement installée dans Claude : hors de Claude, Claude ne joue pas et rien n'est enregistré.
- Chaque coup de Claude et chaque explication comptent sur le forfait Claude de l'utilisateur.
- Les parties sont enregistrées dans la base personnelle de l'utilisateur, visible de lui seul.
- Les jauges et l'analyse viennent de moteurs Stockfish ; le diagnostic des biais et du niveau est produit par Claude et reste indicatif.
- L'archive pèse environ 1,8 Mo (moteurs, polices et noms d'ouvertures embarqués).

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
