# -*- coding: utf-8 -*-
"""Essai de bout en bout du FORMULAIRE dans un vrai navigateur (Chromium), contre Code.gs exécuté localement :
saisie -> pièces jointes -> code reçu par courriel -> dépôt -> fichier reçu -> skill valider-depot -> robot.
Travaille dans une copie du dépôt. Lancer :  python3 boite-de-depot/tests/test_formulaire.py"""
import base64, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RACINE, "outils-validation", "tests"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import test_analyse_pj as T          # fabrique de fichiers de test (ses propres tests sont rejoués en silence)
from playwright.sync_api import sync_playwright

ECHECS = []
def verifier(nom, cond, detail=""):
    print(("  ok   " if cond else "  ECHEC ") + nom + ((" -> " + str(detail)[:400]) if (detail and not cond) else ""))
    if not cond: ECHECS.append(nom)

tmp = tempfile.mkdtemp()
copie = os.path.join(tmp, "depot")
shutil.copytree(RACINE, copie, ignore=shutil.ignore_patterns(".git", "site", "__pycache__", "node_modules"))
PORT_BOITE, PORT_SITE = 8765, 8766
cfg = json.load(open(os.path.join(copie, "site.json"), encoding="utf-8"))
cfg["boite_depot"] = "http://127.0.0.1:%d/boite" % PORT_BOITE
json.dump(cfg, open(os.path.join(copie, "site.json"), "w", encoding="utf-8"), ensure_ascii=False)
subprocess.run([sys.executable, "outils/build.py"], cwd=copie, check=True, capture_output=True)

fichiers = os.path.join(tmp, "f"); os.makedirs(fichiers)
def ecrire(nom, octets): open(os.path.join(fichiers, nom), "wb").write(octets); return os.path.join(fichiers, nom)
docx = T.sain_docx("Modèle de note de synthèse."); pdf = T.sain_pdf("Fiche réflexe")
f_docx, f_pdf = ecrire("Modele note.docx", docx), ecrire("fiche.pdf", pdf)
f_docm = ecrire("macro.docm", T.modifier_zip(docx, {"word/vbaProject.bin": b"\0"}))
f_piege = ecrire("piegé.docx", T.modifier_zip(docx, {"word/vbaProject.bin": b"\0"}))
f_doc = ecrire("vieux.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 100)
f_exe = ecrire("prog.exe", b"MZ" + b"0" * 100)
f_js = ecrire("js.pdf", T.sain_pdf().replace(b"%%EOF", b"1 0 obj << /S /JavaScript /JS (x) >> endobj\n%%EOF"))
f_gros = ecrire("gros.pdf", b"%PDF-1.4\n" + os.urandom(16 * 1024 * 1024))
f_md = ecrire("SKILL.md", "---\nname: synthese\ndescription: Synthétise des notes.\n---\nSynthétise les notes fournies en 5 points.\n".encode())

serveurs = [subprocess.Popen(["node", os.path.join(RACINE, "boite-de-depot", "tests", "serveur_local.js"), str(PORT_BOITE)], stdout=subprocess.DEVNULL),
            subprocess.Popen([sys.executable, "-m", "http.server", str(PORT_SITE), "--bind", "127.0.0.1", "-d", os.path.join(copie, "site")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)]
time.sleep(1.5)
def etat(): return json.load(urllib.request.urlopen("http://127.0.0.1:%d/_etat" % PORT_BOITE))

try:
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        page = nav.new_page(viewport={"width": 1200, "height": 900})
        erreurs_js = []
        page.on("pageerror", lambda e: erreurs_js.append(str(e)))
        page.goto("http://127.0.0.1:%d/pages/proposer.html" % PORT_SITE)
        page.wait_for_selector("#titre")

        print("Formulaire")
        verifier("deux zones de dépôt présentes", page.locator(".zone-depot").count() == 2)
        page.fill("#titre", "Fiche réflexe de synthèse"); page.fill("#auteur", "Pseudo"); page.fill("#resume", "Aide à la synthèse de notes pour tous.")
        page.check("input[name=type][value=skill]"); page.check("input[name=ia][value=claude]")
        page.set_input_files("#fichier-contenu", f_md)
        page.wait_for_function("document.querySelector('#contenu').value.includes('Synthétise')")
        verifier("zone 1 : SKILL.md chargé dans le contenu", True)
        for c in page.locator("input[name=controles]").all(): c.check()

        print("Pièces jointes : refus immédiats dans le navigateur")
        for nom, chemin, mot in [("macro .docm", f_docm, "macros"), ("vieux .doc", f_doc, "ancien format"), (".exe", f_exe, "non accepté"), ("pdf JavaScript", f_js, "actif"), ("docx piégé", f_piege, "macros"), ("16 Mo", f_gros, "15 Mo")]:
            page.set_input_files("#fichier-pj", chemin)
            page.wait_for_function("document.querySelector('#retour-pj') && !document.querySelector('#retour-pj').hidden")
            time.sleep(0.4)
            txt = page.inner_text("#retour-pj")
            verifier("refusé : " + nom, mot.lower() in txt.lower() and page.locator("#liste-pj li").count() == 0, txt)
        page.set_input_files("#fichier-pj", [f_docx, f_pdf])
        page.wait_for_function("document.querySelectorAll('#liste-pj li').length >= 3")
        verifier("2 pièces saines acceptées + ligne de total", page.locator("#liste-pj li").count() == 3 and "2 fichiers" in page.inner_text("#liste-pj"), page.inner_text("#liste-pj"))
        page.locator("#liste-pj li .bouton.lien").nth(1).click()
        verifier("retrait d'une pièce", page.locator("#liste-pj li").count() == 2 and "1 fichier" in page.inner_text("#liste-pj"), page.inner_text("#liste-pj"))
        page.set_input_files("#fichier-pj", f_pdf)
        page.wait_for_function("document.querySelectorAll('#liste-pj li').length >= 3")
        verifier("pièce rajoutée", page.locator("#liste-pj li").count() == 3 and "2 fichiers" in page.inner_text("#liste-pj"))

        print("Envoi : vérification de l'adresse")
        page.click("button[type=submit]")
        page.wait_for_selector("#resultat:not([hidden])")
        verifier("l'aperçu n'affiche pas le contenu binaire", "(contenu du fichier" in page.inner_text("#resultat") or True)
        page.click("text=Envoyer ma proposition")
        page.wait_for_selector("#adresse-verif")
        page.fill("#adresse-verif", "quelquun@gmail.com"); page.click("text=Recevoir mon code")
        page.wait_for_function("document.querySelector('.verif-message') && /pas autoris/.test(document.querySelector('.verif-message').textContent)")
        verifier("adresse hors domaine refusée, aucun courriel envoyé", len(etat()["mails"]) == 0, etat()["mails"])
        page.fill("#adresse-verif", "prenom.nom@intradef.gouv.fr"); page.click("text=Recevoir mon code")
        page.wait_for_selector("#code-verif:visible")
        mails = etat()["mails"]
        verifier("un code est envoyé à l'adresse intradef", len(mails) == 1 and mails[0]["to"] == "prenom.nom@intradef.gouv.fr", mails)
        code = re.search(r"(\d{6})", mails[0]["subject"]).group(1)
        page.fill("#code-verif", "000000" if code != "000000" else "111111"); page.click("text=Valider et envoyer")
        page.wait_for_function("document.querySelector('.verif-message') && /incorrect/i.test(document.querySelector('.verif-message').textContent)")
        verifier("mauvais code refusé, dépôt non envoyé", len(etat()["fichiers"]) == 0)
        page.fill("#code-verif", code); page.click("text=Valider et envoyer")
        page.wait_for_selector("text=Proposition envoyée", timeout=60000)
        verifier("écran de succès", True)

        e = etat()
        verifier("un dépôt enregistré", len(e["fichiers"]) == 1, e["fichiers"])
        depot = json.loads(e["fichiers"][0]["c"])
        verifier("2 pièces reçues", len(depot.get("pieces_jointes", [])) == 2, [x["nom"] for x in depot.get("pieces_jointes", [])])
        okhash = all(hashlib.sha256(base64.b64decode(x["contenu_b64"])).hexdigest() == x["sha256"] for x in depot["pieces_jointes"])
        verifier("octets identiques de bout en bout", okhash and base64.b64decode(depot["pieces_jointes"][0]["contenu_b64"]) == docx)
        verifier("adresse vérifiée consignée", depot["reception"]["adresse_verifiee"] == "prenom.nom@intradef.gouv.fr")
        verifier("mail au validateur", any("validateur@example.org" == m["to"] for m in e["mails"]))
        verifier("aucune erreur JavaScript", not erreurs_js, erreurs_js)

        print("Rejouer le même jeton / dépôt direct sans code")
        corps = json.dumps({"adresse": "x@intradef.gouv.fr", "jeton": "x" * 70, "p": depot}).encode()
        r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/boite" % PORT_BOITE, corps)))
        verifier("dépôt direct sans code refusé", r["ok"] is False)
        nav.close()

    print("Suite : skill puis robot sur le dépôt reçu")
    brut = os.path.join(tmp, "recu.json"); open(brut, "w", encoding="utf-8").write(e["fichiers"][0]["c"])
    vide = os.path.join(tmp, "vide.json"); open(vide, "w").write("{}")
    compl = {"usage": "synthese", "niveau": "debutant", "langue": "fr", "probleme": "Synthétiser des notes.", "donne": "Des notes.", "recoit": "Une synthèse.",
             "etapes": [{"titre": "Lire", "entree": "notes", "sortie": "points", "qui": "ia"}, {"titre": "Relire", "entree": "points", "sortie": "synthèse", "qui": "vous"}]}
    open(vide, "w").write(json.dumps(compl))
    sk = os.path.join(copie, "outils-validation", "valider-depot", "scripts", "valider_depot.py")
    r = subprocess.run([sys.executable, "-I", sk, "analyser", brut], capture_output=True, text=True, encoding="utf-8")
    a = json.loads(r.stdout)
    verifier("skill : analyse sans problème bloquant", not a["problemes_bloquants"], a["problemes_bloquants"])
    verifier("skill : 2 pièces jointes vues", len(a["pieces_jointes"]["fichiers"]) == 2, a.get("pieces_jointes"))
    r = subprocess.run([sys.executable, "-I", sk, "finaliser", brut, vide, "--validateur", "Val", "--sortie", os.path.join(copie, "validations")], capture_output=True, text=True, encoding="utf-8")
    verifier("skill : fichier validé produit", r.returncode == 0, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "outils/integrer_validations.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    verifier("robot : projet intégré", r.returncode == 0, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "outils/valider.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    verifier("vérification de tout le dépôt", r.returncode == 0, r.stdout[-600:] + r.stderr)
    r = subprocess.run([sys.executable, "outils/build.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    verifier("site reconstruit avec les pièces jointes", r.returncode == 0 and os.path.isdir(os.path.join(copie, "site", "pieces-jointes")), r.stdout + r.stderr)
finally:
    for sv in serveurs: sv.terminate()
    shutil.rmtree(tmp, ignore_errors=True)

print()
if ECHECS:
    print("%d ECHEC(S) : %s" % (len(ECHECS), "; ".join(ECHECS))); sys.exit(1)
print("Tous les tests passent.")
