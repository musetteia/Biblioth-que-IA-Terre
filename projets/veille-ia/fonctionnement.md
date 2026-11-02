# Fonctionnement

## Préparer la boîte mail
- qui: vous
- entrée: Vos abonnements à des newsletters sur l'IA
- sortie: Un libellé « Veille IA » qui regroupe ces newsletters dans Gmail

Créez le libellé et un filtre qui l'applique automatiquement, puis remplacez dans le skill les adresses nom@example.org par celles de vos expéditeurs.

## Lancer la veille
- qui: vous
- entrée: Une demande du type « fusion IA du jour »
- sortie: La période à couvrir (24 h par défaut, 72 h le lundi)

## Collecter et vérifier
- qui: ia
- entrée: Les mails de la période et quelques recherches web
- sortie: Une liste de faits datés, chacun avec sa source

L'IA lit les newsletters, consulte les annonces officielles des éditeurs et écarte les rumeurs et l'autopromotion.

## Classer et rédiger
- qui: ia
- entrée: Les faits retenus
- sortie: La synthèse en 7 axes avec niveau de signal, bruit écarté et lecture croisée

## Relire avant diffusion
- qui: vous
- entrée: La synthèse ou l'édition grand écran
- sortie: Une veille vérifiée, prête à partager

Vérifiez les chiffres mis en avant et leurs sources avant toute diffusion.
