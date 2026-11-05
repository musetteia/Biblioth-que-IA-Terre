# Règles de publication

Ces règles s'appliquent à tout projet de la bibliothèque. Elles protègent les utilisateurs et la communauté. Le script de vérification en contrôle une partie ; le reste repose sur vous et sur le relecteur.

## Règle d'or

**Cette bibliothèque est hors du réseau sécurisé de la Défense. N'y publiez rien de protégé ni de non public.** Par défaut, tous les exemples sont fictifs ou anonymisés au point d'être sans lien avec une situation réelle. Une seule exception encadrée existe : les faits de sources ouvertes (voir plus bas).

## Ce qui est interdit dans un projet

- Tout document ou texte portant une mention de protection, quelle qu'elle soit.
- Les noms de personnes réelles, de lieux ou d'unités réels, de matériels ou d'opérations réels (sauf dans l'exception « sources ouvertes » ci-dessous, et dans ses limites).
- Les adresses électroniques, numéros de téléphone, adresses IP, mots de passe, clés ou jetons.
- Les scripts qui accèdent au réseau, lancent des commandes système ou exécutent du texte comme du code.
- Les fichiers qui ne sont pas du texte simple (formats autorisés : md, txt, py, json, csv, yaml). Taille maximale par fichier : 200 Ko.
- Exception : les **pièces jointes** d'un projet, rangées dans `pieces-jointes/`, peuvent être des documents Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`) ou PDF, 10 au plus et 15 Mo en tout. Elles sont contrôlées à la réception, par le validateur puis par le robot : sont refusés les macros, objets incorporés ou ActiveX, liens vers d'autres fichiers, JavaScript ou lancement de programme dans un PDF, fichiers chiffrés, anciens formats (`.doc`, `.xls`, `.ppt`), mentions de protection, clés et mots de passe. Les métadonnées de personnes sont anonymisées ; les noms ou numéros présents dans le texte d'un document sont signalés au validateur, qui décide.

## Les quatre contrôles à attester

Avant publication, l'auteur vérifie lui-même chacun de ces points, puis les inscrit dans le champ `controles` de la fiche. Sans les quatre, le projet n'est pas accepté.

1. **aucune-donnee-reelle** : le projet ne contient aucune information réelle.
2. **exemples-fictifs** : tous les exemples sont inventés.
3. **aucun-nom-adresse** : aucun nom réel, aucune adresse, aucun numéro.
4. **aucun-appel-reseau** : le projet n'envoie ni ne télécharge rien par lui-même.

## Ce que doit contenir une fiche

- Un titre, un résumé, et les champs de classement (type, usage, IA compatibles, langue, niveau).
- Trois sections : *Le problème résolu*, *Entrées et sorties*, *Limites connues*.
- Un fichier `fonctionnement.md` (facultatif pour une première proposition, à ajouter ensuite) : au moins deux étapes, qui fait quoi (vous ou l'IA), avec un exemple fictif par étape. Sans lui, l'onglet « Fonctionnement » n'apparaît pas.
- Un fichier `installation.md` : la marche à suivre, commune puis par IA.
- Un exemple d'entrée et de sortie attendue (recommandé, facultatif pour une première proposition) : fictif, ou, dans l'exception « sources ouvertes », tiré de sources publiques citées.

## Exception : faits réels de sources ouvertes

Certains projets (une veille, par exemple) n'ont de sens qu'avec des faits réels. Ils peuvent déclarer `donnees: sources-ouvertes` à la place de `exemples-fictifs`, aux conditions suivantes.

- **Seulement des informations publiques.** Chaque fait réel vient d'une source ouverte, datée, avec son lien. Aucune information protégée, aucune information non publique, aucune mention de protection.
- **Les exemples sont présentés comme des exemples** : datés, non mis à jour, et jamais repris comme une situation à jour.
- **Pas de particulier ni d'adresse.** Les titulaires de fonctions publiques, et les personnes visées par un acte officiel public (une liste de sanctions, par exemple), peuvent être nommés comme dans la source citée. Aucun nom de particulier, aucune adresse, aucun numéro.
- **Trois contrôles à attester** à la place des quatre : `aucune-donnee-protegee`, `sources-citees`, `aucun-nom-adresse`. Les contrôles `aucune-donnee-reelle` et `exemples-fictifs` ne s'appliquent pas, car ils seraient faux.
- **Le relecteur vérifie chaque fait réel contre sa source** avant de passer le projet à « relu ».
- Les autres contrôles du script (mentions de protection, adresses électroniques, numéros, mots de passe, scripts) restent actifs.
- Le formulaire « Proposer un projet » reste réservé aux exemples fictifs.

## Statuts

- Tout nouveau projet est **proposé**.
- Seul un relecteur, autre que l'auteur, passe un projet à **relu** puis **recommandé**, et inscrit son nom dans `relu_par`.
- L'auteur ne relève jamais lui-même le statut de son projet.

## Adaptations

Adapter un projet crée un nouveau projet. Il garde le lien vers son original (champ `filiation`), repart en statut « proposé » et doit être de nouveau attesté : les contrôles ne sont jamais hérités.

## Limites de la vérification automatique

Le script de vérification est un premier filtre. Il repère des motifs courants (adresses, numéros, mots de marquage, imports réseau). Il ne comprend pas le sens d'un texte : il ne garantit pas qu'un projet est sans risque. La relecture humaine reste obligatoire.

## Licence

La licence applicable aux projets n'est pas encore décidée. Tant qu'elle ne l'est pas, ne publiez que ce que vous avez le droit de partager.
