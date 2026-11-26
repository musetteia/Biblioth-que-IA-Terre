# -*- coding: utf-8 -*-
"""Crée un projet à partir d'un modèle, ou duplique un projet existant pour l'adapter.

Usage :
    python outils/nouveau.py mon-projet --type prompt
    python outils/nouveau.py mon-projet --depuis synthese-conference

Types de modèle : prompt, skill, projet, script.
Une adaptation garde un lien vers son original (champ filiation) et doit être
de nouveau attestée : la liste « controles » est vidée.
"""
import re
import shutil
import sys

from commun import MODELES, PROJETS, ErreurFiche, console_utf8, lire_projet, remplacer_champ

TYPES = ("prompt", "skill", "projet", "script", "application")


def main(argv):
    console_utf8()
    args = argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return 2
    nouvel_id, type_modele, source = args[0], None, None
    i = 1
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            type_modele = args[i + 1]
            i += 2
        elif args[i] == "--depuis" and i + 1 < len(args):
            source = args[i + 1]
            i += 2
        else:
            print("Argument inconnu : %s" % args[i])
            return 2

    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", nouvel_id):
        print("Le nom « %s » doit être en minuscules, chiffres et tirets (ex. mon-projet)." % nouvel_id)
        return 2
    cible = PROJETS / nouvel_id
    if cible.exists():
        print("Le dossier projets/%s existe déjà." % nouvel_id)
        return 2
    if bool(type_modele) == bool(source):
        print("Indiquez soit --type (%s), soit --depuis <projet>." % ", ".join(TYPES))
        return 2

    if source:
        origine = PROJETS / source
        if not (origine / "README.md").exists():
            print("Le projet « %s » n'existe pas." % source)
            return 2
        shutil.copytree(str(origine), str(cible), ignore=shutil.ignore_patterns("__pycache__", ".*"))
        readme = cible / "README.md"
        texte = readme.read_text(encoding="utf-8")
        try:
            titre = lire_projet(cible)["meta"].get("titre", nouvel_id)
        except ErreurFiche:
            titre = nouvel_id
        if "(adaptation" not in titre:
            titre = "%s (adaptation)" % titre
        texte = remplacer_champ(texte, "titre", titre)
        texte = remplacer_champ(texte, "filiation", "adaptation:%s" % source)
        texte = remplacer_champ(texte, "statut", "propose")
        texte = remplacer_champ(texte, "version", "0.1")
        texte = remplacer_champ(texte, "version_plus_recente", "aucune")
        texte = remplacer_champ(texte, "auteur", '"[contributeur]"')
        texte = remplacer_champ(texte, "relu_par", '"[relecteur]"')
        texte = remplacer_champ(texte, "controles", "[]")
        readme.write_text(texte, encoding="utf-8")
        print("Projet « %s » créé comme adaptation de « %s »." % (nouvel_id, source))
    else:
        if type_modele not in TYPES:
            print("Type inconnu « %s » (attendu : %s)." % (type_modele, ", ".join(TYPES)))
            return 2
        modele = MODELES / type_modele
        if not modele.exists():
            print("Le modèle « %s » est introuvable." % type_modele)
            return 2
        shutil.copytree(str(modele), str(cible), ignore=shutil.ignore_patterns("__pycache__", ".*"))
        print("Projet « %s » créé à partir du modèle « %s »." % (nouvel_id, type_modele))

    print("""
Étapes suivantes :
  1. Ouvrez projets/%s/README.md et remplacez les textes du modèle.
  2. Vérifiez chaque point des contrôles, puis ajoutez-les à la ligne « controles ».
  3. python outils/valider.py %s
  4. python outils/build.py   puis ouvrez site/index.html
""" % (nouvel_id, nouvel_id))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
