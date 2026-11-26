# Échecs contre Claude

Une application pour jouer aux échecs contre Claude et analyser ses parties :
- **Jeu :** échiquier, choix de la couleur, retour en arrière, pendule.
- **Pendant la partie :** jauge d'évaluation et jauges tactiques et stratégiques.
- **Après la partie :** analyse Stockfish, rejeu commenté de tes meilleurs et pires coups.
- **Bilan :** détection de tes biais et évaluation de ton niveau.

Claude choisit ses coups seul, sans moteur. Stockfish sert uniquement aux jauges et à l'analyse.

L'application a besoin de deux services de Claude : un appel à Claude, pour qu'il joue contre toi et commente tes parties, et une base de données, pour enregistrer tes parties. Chaque coup de Claude et chaque explication comptent sur ton forfait Claude, comme un message dans le chat. Tes parties sont enregistrées dans ta propre base, visible de toi seul.

## Contenu de l'archive

| Fichier | Rôle |
|---|---|
| `index.html` | l'application (page d'entrée) |
| `stockfish-19-lite-single.js` et `.wasm` | moteur principal Stockfish 19 lite (jauge d'évaluation, analyse) |
| `stockfish-10.js` | Stockfish 10 (détail de l'évaluation pour les jauges tactiques et stratégiques, moteur de secours) |
| `chess.js` | règles du jeu (chess.js 0.10.3) |
| `polices.css` et les fichiers `.woff2` | polices Manrope, JetBrains Mono et pièces d'échecs |
| `openings.json` | noms des ouvertures (base lichess) |
| `LICENCE-*.txt` | textes des licences des composants embarqués |

L'application fonctionne avec ses seuls fichiers : plus rien n'est chargé par Internet.

## Hors de Claude

Sur un simple serveur web, la page s'affiche, mais Claude ne joue pas et rien n'est enregistré. Une version autonome demanderait une adaptation : une clé d'API Anthropic, facturée à part, et une sauvegarde dans le navigateur.

## Premiers pas

- **Onglet Jouer, « Ton profil » (facultatif) :** indique ton niveau Elo approximatif et ton pseudo chess.com ou lichess.
- **Onglet Mes parties :** importe tes parties en collant leur PGN complet. Ta couleur est reconnue grâce à ton pseudo.
- **Onglet Bilan :** « Analyser » lance l'analyse groupée. Ensuite, « Analyse approfondie par Claude » donne le diagnostic de tes biais et de ton niveau.

## Licences

Le texte des licences est fourni dans les fichiers `LICENCE-*.txt` de l'archive.
- **Stockfish 19 lite** (Stockfish.js, Chess.com, LLC) et **Stockfish 10** (Stockfish.js) : GPLv3. Sources : https://github.com/official-stockfish/Stockfish et https://github.com/nmrugg/stockfish.js
- **chess.js 0.10.3** : licence BSD. Un commentaire du fichier a été légèrement modifié (le préfixe d'une adresse web retiré), sans effet sur le code.
- **Polices** Manrope, JetBrains Mono et Noto Sans Symbols 2 : SIL OFL 1.1. Le fichier des pièces d'échecs ne contient que les six symboles utilisés.
- **Noms d'ouvertures :** https://github.com/lichess-org/chess-openings (CC0).
