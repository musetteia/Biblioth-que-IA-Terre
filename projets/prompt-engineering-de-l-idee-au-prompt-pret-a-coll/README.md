---
titre: "Prompt engineering : de l'idée au prompt prêt à coller"
resume: "Transforme une simple idée (projet, agent, tâche) en prompt complet : recherche web, questions à choix multiple une par une, garde-fous validés, audit final."
type: skill
usage: redaction
ia_compatibles: [claude]
langue: fr
niveau: debutant
statut: relu
version: 0.1
donnees: exemples-fictifs
filiation: original
version_plus_recente: aucune
licence: "[à définir]"
etiquettes: [prompt, prompt-engineering, garde-fous, questionnaire, audit]
controles: [aucune-donnee-reelle, exemples-fictifs, aucun-nom-adresse, aucun-appel-reseau]
auteur: "Adrian"
relu_par: "Adrian"
validation_ia: "Validé avec l'aide de l'IA, par Adrian, le 2026-11-21"
---

## Le problème résolu

Écrire un bon prompt demande de connaître le métier, de lister ce qui manque et de prévoir les erreurs de l'IA. Un prompt rédigé d'un jet oublie souvent le public, le format de sortie, les cas limites et les garde-fous.
Ce skill conduit la démarche à votre place : il cherche les règles du domaine sur le web, repère les lacunes de votre idée, vous interroge, puis assemble et contrôle le prompt.

## Entrées et sorties

- **Ce que vous donnez** : Une idée en quelques lignes (le projet, l'agent ou la tâche visés), ou un prompt existant à améliorer. Vous pouvez imposer un mode : court, standard ou complet.
- **Ce que vous recevez** : Un prompt complet en XML structuré, dans un bloc de code modifiable, avec ses hypothèses, les valeurs à renseigner, les sources datées avec indice de fiabilité (A à D) et les points non vérifiés.

Un exemple se trouve dans le dossier `exemples/`.

## Limites connues

- Il s'appuie sur la recherche web : sans accès au web, il le signale et pose plus de questions plutôt que d'inventer du contenu métier.
- Le nombre de questions est plafonné selon le mode (3, 6 ou 8) : les lacunes restantes deviennent des hypothèses affichées, à relire.
- Il ne remplace pas la relecture par un professionnel pour les sujets réglementés (fiscal, juridique, santé).
- Il exécute un test à blanc du prompt, pas un test réel sur l'IA cible.
- Le skill ne contient aucun script : les recherches web sont faites par les outils de l'IA qui l'exécute, pas par du code du skill.

## Pour adapter ce projet

Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible.
