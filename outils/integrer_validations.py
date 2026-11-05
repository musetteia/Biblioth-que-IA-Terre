# -*- coding: utf-8 -*-
"""Robot de la bibliothèque : transforme chaque fichier validé déposé dans validations/ en projet complet.

Lancé automatiquement par GitHub (.github/workflows/validations.yml) quand un validateur dépose un
fichier « valide-xxx.json » dans validations/ sur une branche autre que main. On peut aussi le lancer
à la main : python outils/integrer_validations.py

Pour chaque fichier :
  1. il refuse tout fichier qui n'a pas été validé (bloc « validation » absent) ;
  2. il refuse tout fichier qui contient encore un marquage, un nom de personne, une adresse, un téléphone,
     une clé ou une adresse IP (même contrôle que le formulaire et le skill de validation) ;
  3. il fabrique le projet (projets/<id>/) et le vérifie comme tous les autres ;
  4. il range le fichier traité dans validations/traites/.
Si un seul fichier pose problème, rien n'est enregistré et le motif est affiché.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

from commun import PROJETS, RACINE, charger_vocabulaires, console_utf8
import importer

DOSSIER = RACINE / "validations"
TRAITES = DOSSIER / "traites"
sys.path.insert(0, str(RACINE / "outils-validation" / "valider-depot" / "scripts"))
import valider_depot  # noqa: E402  (même épuration que le skill et le formulaire)


def ecrire_resume(lignes):
    """Affiche le bilan, et l'écrit dans le résumé de l'exécution GitHub quand il existe."""
    texte = "\n".join(lignes)
    print(texte)
    chemin = os.environ.get("GITHUB_STEP_SUMMARY")
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(texte + "\n")


def _pieces_controlees(d, lot, erreurs_pj):
    """Pièces jointes d'un fichier validé : nouvelle analyse complète, indépendante de celle du validateur."""
    if erreurs_pj:
        raise importer.ErreurProposition("Pièces jointes : " + " ".join(erreurs_pj))
    attendues = (d["validation"].get("pieces_jointes") or [])
    if not lot:
        if attendues:
            raise importer.ErreurProposition("Pièces jointes annoncées par la validation mais absentes du fichier.")
        return None
    if lot["refus"]:
        raise importer.ErreurProposition("Pièces jointes refusées :\n" + "\n".join("  - " + x for x in lot["refus"]))
    if sorted(x.get("sha256") for x in attendues) != sorted(f["sha256_origine"] for f in lot["fichiers"]):
        raise importer.ErreurProposition("Les pièces jointes ne correspondent pas à celles qu'a validées le validateur (empreintes différentes).")
    for f in lot["fichiers"]:
        if f["sha256"] != f["sha256_origine"]:
            raise importer.ErreurProposition("« %s » : des métadonnées de personne n'ont pas été anonymisées." % f["nom"])
        if f["nom"] != f["nom_origine"]:
            raise importer.ErreurProposition("« %s » : nom de fichier non conforme." % f["nom_origine"])
    return [(f["nom"], f["octets"]) for f in lot["fichiers"]]


def integrer(fichier, vocab, existants):
    d = importer.lire_proposition(str(fichier), vocab)
    if not isinstance(d.get("validation"), dict):
        raise importer.ErreurProposition("Ce fichier n'a pas été validé (bloc « validation » absent) : "
                                         "il doit d'abord passer par le skill valider-depot.")
    lot, erreurs_pj = valider_depot.analyser_pj(d)     # retire « pieces_jointes » de d : le base64 ne passe pas par l'épuration de texte
    pieces = _pieces_controlees(d, lot, erreurs_pj)
    _, reste, _ = valider_depot.epurer_proposition(d)
    if sum(reste.values()):
        detail = ", ".join("%d × %s" % (n, valider_depot.LIBELLES[c]) for c, n in reste.items() if n)
        raise importer.ErreurProposition("Le fichier contient encore des éléments interdits : %s." % detail)
    ident = importer.identifiant(d, existants)
    tmp = Path(tempfile.mkdtemp(prefix="validation-"))
    try:
        dossier = tmp / ident
        dossier.mkdir()
        importer.ecrire_projet(dossier, d, vocab, ident, pieces)
        rapport = importer.verifier(dossier, ident, existants, vocab)
        if rapport.erreurs:
            raise importer.ErreurProposition("Vérification du projet :\n" + "\n".join("  - " + e for e in rapport.erreurs))
        PROJETS.mkdir(exist_ok=True)
        shutil.copytree(str(dossier), str(PROJETS / ident))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return ident, d


def ranger(fichier):
    TRAITES.mkdir(parents=True, exist_ok=True)
    cible = TRAITES / fichier.name
    n = 2
    while cible.exists():
        cible = TRAITES / ("%s-%d%s" % (fichier.stem, n, fichier.suffix))
        n += 1
    shutil.move(str(fichier), str(cible))


def main():
    console_utf8()
    fichiers = sorted(DOSSIER.glob("*.json")) if DOSSIER.is_dir() else []
    if not fichiers:
        print("Aucun fichier à intégrer dans validations/.")
        return 0
    vocab = charger_vocabulaires()
    existants = {p.name for p in PROJETS.iterdir() if p.is_dir()} if PROJETS.exists() else set()
    reussis, echecs = [], []
    for f in fichiers:
        try:
            ident, d = integrer(f, vocab, existants)
        except importer.ErreurProposition as e:
            echecs.append((f.name, str(e)))
            continue
        existants.add(ident)
        reussis.append((f, ident, d))

    if echecs:
        # Rien n'est enregistré : on retire les projets fabriqués pendant ce passage.
        for _, ident, _ in reussis:
            shutil.rmtree(str(PROJETS / ident), ignore_errors=True)
        lignes = ["## Intégration refusée", ""]
        for nom, motif in echecs:
            lignes += ["**%s**" % nom, "", motif, ""]
        lignes.append("Corrigez le fichier (en le repassant par le skill valider-depot), puis déposez-le de nouveau.")
        ecrire_resume(lignes)
        return 1

    lignes = ["## Projets ajoutés à la demande de fusion", ""]
    for f, ident, d in reussis:
        ranger(f)
        lignes.append("- « %s » → `projets/%s` (%s)" % (importer.une_ligne(d["titre"]), ident,
                                                     importer.une_ligne(d["validation"].get("par"))))
    lignes += ["", "Un administrateur relit puis fusionne : la fusion publie le site."]
    ecrire_resume(lignes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
