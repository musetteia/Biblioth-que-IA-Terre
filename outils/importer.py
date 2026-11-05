# -*- coding: utf-8 -*-
"""Transforme une proposition de projet (fichier .json du formulaire du site) en projet complet.

Usage :
    python outils/importer.py proposition-xxx.json              # crée le projet et le vérifie
    python outils/importer.py proposition-xxx.json --publier    # crée, vérifie, puis envoie sur GitHub
    python outils/importer.py proposition-xxx.json --demander   # crée, vérifie, puis demande avant d'envoyer

Le projet n'est ajouté que s'il passe la vérification. Sinon, rien n'est créé et les
problèmes sont listés : corrigez-les avec le contributeur (ou dans le fichier .json).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from commun import DOSSIER_PJ, PROJETS, RACINE, ErreurFiche, charger_vocabulaires, console_utf8, lire_projet
from rendu import slug
import valider

FORMAT = "bibliotheque-ia-terre/proposition"
FICHIER_PRINCIPAL = {"prompt": "prompt.md", "projet": "instructions.md", "skill": "SKILL.md"}
CONTROLES = ("aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "aucun-appel-reseau")


# -- petits outils de texte -------------------------------------------------
def une_ligne(texte):
    return re.sub(r"\s+", " ", str(texte or "")).strip()


def entre_guillemets(texte):
    return '"%s"' % une_ligne(texte).replace('"', "'")


def bloc(texte):
    return str(texte or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def sans_barrieres(texte):
    """Les barrières de code (trois accents graves) casseraient les exemples du schéma."""
    return bloc(texte).replace("```", "'''")


def liste_lignes(texte):
    """Une ligne = un élément. Retire les puces éventuelles."""
    elements = []
    for ligne in bloc(texte).split("\n"):
        ligne = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", ligne).strip()
        if ligne:
            elements.append(ligne)
    return elements


class ErreurProposition(Exception):
    pass


# -- lecture et contrôle du fichier de proposition --------------------------
def lire_proposition(chemin, vocab):
    try:
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise ErreurProposition("Impossible de lire le fichier : %s" % e)
    if not isinstance(donnees, dict) or donnees.get("format") != FORMAT:
        raise ErreurProposition("Ce fichier n'est pas une proposition créée par le formulaire du site.")
    donnees.pop("reception", None)   # bloc ajouté par la boîte de dépôt : jamais publié
    validation = donnees.get("validation")
    if validation is not None and (not isinstance(validation, dict) or not une_ligne(validation.get("par"))):
        raise ErreurProposition("Le bloc « validation » est incomplet : il doit indiquer le pseudo du validateur (par).")

    problemes = []
    for cle in ("titre", "resume", "type", "usage", "niveau", "langue", "auteur", "probleme", "donne", "recoit", "contenu"):
        if not une_ligne(donnees.get(cle)):
            problemes.append("Le champ « %s » est vide." % cle)
    if donnees.get("type") not in vocab["type"]:
        problemes.append("Type inconnu : %s." % donnees.get("type"))
    if donnees.get("usage") not in vocab["usage"]:
        problemes.append("Usage inconnu : %s." % donnees.get("usage"))
    if donnees.get("niveau") not in vocab["niveau"]:
        problemes.append("Niveau inconnu : %s." % donnees.get("niveau"))
    if donnees.get("langue") not in vocab["langue"]:
        problemes.append("Langue inconnue : %s." % donnees.get("langue"))
    ia = donnees.get("ia_compatibles")
    if not isinstance(ia, list) or not ia or any(x not in vocab["ia"] for x in ia):
        problemes.append("Choisissez au moins une IA (valeurs autorisées : %s)." % ", ".join(vocab["ia"]))
    # Les étapes de fonctionnement sont facultatives. Si elles sont fournies, il en faut au moins deux, complètes.
    etapes = donnees.get("etapes")
    if etapes is None:
        etapes = donnees["etapes"] = []
    if not isinstance(etapes, list):
        problemes.append("Le champ « etapes » doit être une liste.")
    elif etapes and len(etapes) < 2:
        problemes.append("Une seule étape de fonctionnement est fournie : il en faut au moins deux (ou aucune).")
    else:
        for i, e in enumerate(etapes, start=1):
            if not isinstance(e, dict) or not une_ligne(e.get("titre")) or not une_ligne(e.get("entree")) or not une_ligne(e.get("sortie")):
                problemes.append("Étape %d : le titre, l'entrée et la sortie sont obligatoires." % i)
            elif e.get("qui") not in ("vous", "ia"):
                problemes.append("Étape %d : « qui » doit valoir vous ou ia." % i)
    if problemes:
        raise ErreurProposition("\n".join("  - " + p for p in problemes))
    return donnees


def identifiant(donnees, existants):
    base = slug(donnees.get("id") or donnees["titre"])[:50].strip("-") or "projet"
    if base == "section":
        base = "projet"
    candidat, n = base, 2
    while candidat in existants:
        candidat = "%s-%d" % (base, n)
        n += 1
    return candidat


# -- génération des fichiers ------------------------------------------------
def fiche(d, vocab):
    valide = d.get("validation") if isinstance(d.get("validation"), dict) and une_ligne((d.get("validation") or {}).get("par")) else None
    controles = [c for c in CONTROLES if c in (d.get("controles") or [])]
    etiquettes = []
    for e in liste_lignes(str(d.get("etiquettes") or "").replace(",", "\n")):
        s = slug(e)
        if s and s != "section" and s not in etiquettes:
            etiquettes.append(s)
    etiquettes = etiquettes[:5]
    entetes = [
        "titre: " + entre_guillemets(d["titre"]),
        "resume: " + entre_guillemets(d["resume"]),
        "type: " + d["type"],
        "usage: " + d["usage"],
        "ia_compatibles: [%s]" % ", ".join(d["ia_compatibles"]),
        "langue: " + d["langue"],
        "niveau: " + d["niveau"],
        "statut: " + ("relu" if valide else "propose"),
        "version: 0.1",
        "donnees: exemples-fictifs",
        "filiation: original",
        "version_plus_recente: aucune",
        'licence: "[à définir]"',
        "etiquettes: [%s]" % ", ".join(etiquettes),
        "controles: [%s]" % ", ".join(controles),
        "auteur: " + entre_guillemets(d["auteur"]),
        "relu_par: " + (entre_guillemets(valide["par"]) if valide else '"[pas encore relu]"'),
    ]
    if valide:
        date = une_ligne(valide.get("date"))[:10]
        entetes.append("validation_ia: " + entre_guillemets(
            "Validé avec l'aide de l'IA, par %s%s" % (une_ligne(valide["par"]), (", le " + date) if date else "")))
    limites = liste_lignes(d.get("limites")) or ["Aucune limite n'a été indiquée par l'auteur : testez avec prudence."]
    adapter = bloc(d.get("adapter")) or "Adaptez les exemples et les consignes à votre cas, sans y mettre de donnée sensible."
    corps = [
        "## Le problème résolu", "", bloc(d["probleme"]), "",
        "## Entrées et sorties", "",
        "- **Ce que vous donnez** : " + une_ligne(d["donne"]),
        "- **Ce que vous recevez** : " + une_ligne(d["recoit"]), "",
    ]
    if bloc(d.get("exemple_entree")) or bloc(d.get("exemple_sortie")):
        corps += ["Un exemple se trouve dans le dossier `exemples/`.", ""]
    corps += ["## Limites connues", ""] + ["- " + x for x in limites] + ["", "## Pour adapter ce projet", "", adapter, ""]
    return "---\n" + "\n".join(entetes) + "\n---\n\n" + "\n".join(corps)


def fonctionnement(d):
    sorties = ["# Fonctionnement", ""]
    for e in d["etapes"]:
        sorties += [
            "## " + une_ligne(e["titre"]),
            "- qui: " + e["qui"],
            "- entrée: " + une_ligne(e["entree"]),
            "- sortie: " + une_ligne(e["sortie"]),
            "",
        ]
        if bloc(e.get("texte")):
            sorties += [bloc(e["texte"]), ""]
        if bloc(e.get("exemple")):
            sorties += ["```exemple", sans_barrieres(e["exemple"]), "```", ""]
    return "\n".join(sorties)


def installation(d, vocab, nom_principal, exemple_entree, exemple_sortie):
    t = d["type"]
    commun = []
    if t == "prompt":
        commun = ["Ouvrez une nouvelle conversation dans votre outil d'IA.",
                  "Copiez tout le contenu de `%s` et envoyez-le comme premier message." % nom_principal,
                  "Dans un second message, collez votre texte, sans donnée sensible."]
    elif t == "projet":
        commun = ["Créez un espace de travail dédié dans votre outil d'IA (un « projet » ou l'équivalent).",
                  "Copiez le contenu de `%s` dans les consignes de cet espace." % nom_principal,
                  "Ajoutez les documents du dossier `connaissance/`, s'il y en a, comme documents de référence."]
    elif t == "skill":
        commun = ["Récupérez le dossier du projet ; le fichier essentiel est `SKILL.md`.",
                  "Si votre outil sait charger un skill, installez-le. Sinon, copiez le contenu de `SKILL.md` au début d'une conversation."]
    else:
        commun = ["Vérifiez que Python 3 est installé : tapez `python --version` dans un terminal (sous Linux ou macOS, parfois `python3`).",
                  "Copiez le fichier `%s` dans le dossier de votre choix." % nom_principal,
                  "Lancez-le depuis un terminal ; l'aide est en tête du fichier. Utilisez d'abord des données fictives."]
    if exemple_entree:
        commun.append("Pour tester : utilisez `exemples/entree-fictive.md`" + (" et comparez avec `exemples/sortie-attendue.md`." if exemple_sortie else "."))
    commun.append("Relisez et vérifiez toujours ce que l'IA produit avant de l'utiliser.")
    lignes = ["## Étapes communes", ""] + ["%d. %s" % (i, x) for i, x in enumerate(commun, start=1)]
    lignes += ["", "Les noms des menus changent selon les versions des outils : en cas de doute, consultez l'aide de votre outil.", ""]
    if not d["ia_compatibles"] or d["ia_compatibles"] == ["toutes"]:
        return "\n".join(lignes)
    for ia in d["ia_compatibles"]:
        if ia != "toutes":
            lignes += ["## " + vocab["ia"][ia], "", "Suivez les étapes communes dans %s." % vocab["ia"][ia], ""]
    return "\n".join(lignes)


def contenu_principal(d, ident):
    t = d["type"]
    texte = bloc(d["contenu"]) + "\n"
    if t == "skill" and not texte.startswith("---"):
        nom = ident
        texte = "---\nname: %s\ndescription: %s\n---\n\n%s" % (nom, entre_guillemets(d["resume"]), texte)
    return texte


def ecrire_projet(dossier, d, vocab, ident, pieces=None):
    t = d["type"]
    nom_principal = FICHIER_PRINCIPAL.get(t) or ident.replace("-", "_") + ".py"
    (dossier / nom_principal).write_text(contenu_principal(d, ident), encoding="utf-8", newline="\n")
    ex_in, ex_out = bloc(d.get("exemple_entree")), bloc(d.get("exemple_sortie"))
    if ex_in or ex_out:
        (dossier / "exemples").mkdir()
    if ex_in:
        (dossier / "exemples" / "entree-fictive.md").write_text(ex_in + "\n", encoding="utf-8", newline="\n")
    if ex_out:
        (dossier / "exemples" / "sortie-attendue.md").write_text(ex_out + "\n", encoding="utf-8", newline="\n")
    (dossier / "README.md").write_text(fiche(d, vocab), encoding="utf-8", newline="\n")
    if d.get("etapes"):
        (dossier / "fonctionnement.md").write_text(fonctionnement(d), encoding="utf-8", newline="\n")
    (dossier / "installation.md").write_text(installation(d, vocab, nom_principal, bool(ex_in), bool(ex_out)), encoding="utf-8", newline="\n")
    if pieces:
        (dossier / DOSSIER_PJ).mkdir()
        for nom, octets in pieces:
            (dossier / DOSSIER_PJ / nom).write_bytes(octets)


# -- vérification avant ajout -------------------------------------------------
def verifier(dossier, ident, existants, vocab):
    try:
        projet = lire_projet(dossier)
    except ErreurFiche as e:
        r = valider.Rapport(ident)
        r.erreur("README.md : %s" % e)
        return r
    return valider.valider_projet(projet, set(existants) | {ident}, vocab)


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8")


def publier(ident, titre):
    for etape in (("add", "projets/" + ident), ("commit", "-m", "Ajout : " + titre), ("push",)):
        r = git(*etape)
        if r.returncode != 0:
            print("\nL'envoi sur GitHub a échoué à l'étape « git %s » :\n%s" % (etape[0], (r.stderr or r.stdout).strip()))
            return False
    return True


def main(argv):
    console_utf8()
    args = [a for a in argv[1:] if not a.startswith("--")]
    options = [a for a in argv[1:] if a.startswith("--")]
    if len(args) != 1 or any(o not in ("--publier", "--demander") for o in options):
        print(__doc__)
        return 2
    vocab = charger_vocabulaires()
    try:
        donnees = lire_proposition(args[0], vocab)
    except ErreurProposition as e:
        print("Proposition refusée :\n%s" % e)
        return 1
    if donnees.get("pieces_jointes"):
        print("Proposition refusée :\nelle contient des pièces jointes. Elles ne s'importent que par le circuit de validation "
              "(skill valider-depot, puis dossier validations/ de GitHub).")
        return 1

    existants = {p.name for p in PROJETS.iterdir() if p.is_dir()} if PROJETS.exists() else set()
    ident = identifiant(donnees, existants)
    tmp = Path(tempfile.mkdtemp(prefix="proposition-"))
    try:
        dossier = tmp / ident
        dossier.mkdir()
        ecrire_projet(dossier, donnees, vocab, ident)
        rapport = verifier(dossier, ident, existants, vocab)
        if rapport.erreurs:
            print("Proposition refusée par la vérification. Rien n'a été ajouté.\n")
            for e in rapport.erreurs:
                print("  - " + e)
            print("\nCorrigez ces points avec le contributeur, puis recommencez.")
            return 1
        PROJETS.mkdir(exist_ok=True)
        shutil.copytree(str(dossier), str(PROJETS / ident))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)

    print("Projet « %s » ajouté : projets/%s (statut : proposé, à faire relire)." % (donnees["titre"], ident))
    for a in rapport.avertissements:
        print("  avertissement : " + a)
    envoyer = "--publier" in options
    if "--demander" in options and not envoyer:
        try:
            envoyer = input("\nPublier maintenant sur GitHub ? (o/n) ").strip().lower().startswith("o")
        except EOFError:
            envoyer = False
        if not envoyer:
            print("Pas envoyé. Le projet est dans projets/%s : vous pourrez l'envoyer plus tard." % ident)
            return 0
    if envoyer:
        if publier(ident, une_ligne(donnees["titre"])):
            print("Envoyé sur GitHub. Le site sera mis à jour dans une ou deux minutes.")
            return 0
        return 1
    print("\nPour le publier : git add projets/%s, git commit, git push (ou relancez avec --publier)." % ident)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
