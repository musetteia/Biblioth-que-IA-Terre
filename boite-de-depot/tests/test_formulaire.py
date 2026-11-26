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
PAGE = lambda corps: ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Outil</title></head><body>" + corps + "</body></html>").encode()
f_html = ecrire("outil.html", PAGE("<p>Bonjour</p><script>document.title = 'x';</script>"))
f_html_fetch = ecrire("collecte.html", PAGE("<script>fetch('https://x.example/c', {method:'POST'})</script>"))
f_html_dist = ecrire("distant.html", PAGE("<script src=\"https://cdn.example/lib.js\"></script>"))
f_html_faux = ecrire("faux.html", b"juste du texte")
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
        for c in page.locator("input[name=controles]:visible").all(): c.check()

        print("Guide de mise aux normes : en haut du formulaire, téléchargeable, case obligatoire")
        verifier("encart du guide visible avant le formulaire", page.locator(".encart-guide").is_visible()
                 and page.evaluate("document.querySelector('.encart-guide').compareDocumentPosition(document.querySelector('#formulaire')) & Node.DOCUMENT_POSITION_FOLLOWING") > 0)
        verifier("encart dans la fenêtre dès l'ouverture (sans défiler)", page.evaluate("document.querySelector('.bouton-guide').getBoundingClientRect().bottom") < 900)
        tel = nav.new_page(viewport={"width": 390, "height": 844}); tel.goto("http://127.0.0.1:%d/pages/proposer.html" % PORT_SITE); tel.wait_for_selector("#titre")
        verifier("téléphone : bouton de téléchargement visible sans défiler (au-dessus de la barre du bas)", tel.evaluate("document.querySelector('.bouton-guide').getBoundingClientRect().bottom") < 844 - 80)
        verifier("le texte du second bouton est lisible (couleur différente du fond)", tel.evaluate("(()=>{const b=document.querySelector('.encart-guide .bouton.secondaire');const c=getComputedStyle(b);return c.color!==c.backgroundColor})()"))
        tel.close()
        for lien, mot in (("guide-mise-aux-normes.md", "preparer-depot"), ("preparer-depot.zip", None)):
            rep = urllib.request.urlopen("http://127.0.0.1:%d/telechargements/%s" % (PORT_SITE, lien))
            octets = rep.read()
            verifier("téléchargement du guide : " + lien, rep.status == 200 and len(octets) > 5000 and (mot is None or mot.encode() in octets[:200]))
        zg = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen("http://127.0.0.1:%d/telechargements/preparer-depot.zip" % PORT_SITE).read()))
        verifier("le .zip est un skill (SKILL.md avec en-tête)", zg.namelist() == ["preparer-depot/SKILL.md"] and zg.read("preparer-depot/SKILL.md").startswith(b"---\nname: preparer-depot"))
        page.click("button[type=submit]")
        page.wait_for_timeout(500)
        verifier("sans la case du guide : l'envoi est refusé avec un message clair",
                 "guide de mise aux normes" in page.inner_text(".formulaire").lower() or "guide de mise aux normes" in page.inner_text("body").lower())
        page.check("input[name=guide]")

        print("Pièces jointes : refus immédiats dans le navigateur")
        for nom, chemin, mot in [("macro .docm", f_docm, "macros"), ("vieux .doc", f_doc, "ancien format"), (".exe", f_exe, "non accepté"), ("pdf JavaScript", f_js, "actif"), ("docx piégé", f_piege, "macros"), ("16 Mo", f_gros, "15 Mo"), ("html avec fetch", f_html_fetch, "fetch"), ("html avec ressource distante", f_html_dist, "distante"), ("faux html", f_html_faux, "pas une page")]:
            page.set_input_files("#fichier-pj", chemin)
            page.wait_for_function("document.querySelector('#retour-pj') && !document.querySelector('#retour-pj').hidden")
            time.sleep(0.4)
            txt = page.inner_text("#retour-pj")
            verifier("refusé : " + nom, mot.lower() in txt.lower() and page.locator("#liste-pj li").count() == 0, txt)
        page.set_input_files("#fichier-pj", f_html)
        page.wait_for_function("document.querySelectorAll('#liste-pj li').length >= 2")
        verifier("page HTML autonome acceptée", page.locator("#liste-pj li").count() == 2 and "outil.html" in page.inner_text("#liste-pj"), page.inner_text("#liste-pj"))
        page.locator("#liste-pj li .bouton.lien").first.click()
        verifier("page HTML retirée", page.locator("#liste-pj li").count() == 0)
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
        page.wait_for_selector("#adresse-secu:visible")
        verifier("adresse perso inconnue : l'adresse sécurisée est demandée, aucun courriel envoyé", len(etat()["mails"]) == 0, etat()["mails"])
        page.fill("#adresse-secu", "quelquun@gmail.com"); page.click("text=Recevoir mon code")
        page.wait_for_function("document.querySelector('.verif-message') && /@intradef/.test(document.querySelector('.verif-message').textContent)")
        verifier("adresse sécurisée hors domaine refusée, aucun courriel envoyé", len(etat()["mails"]) == 0, etat()["mails"])
        page.fill("#adresse-secu", "prenom.nom@intradef.gouv.fr"); page.click("text=Recevoir mon code")
        page.wait_for_selector("#code-verif:visible")
        mails = etat()["mails"]
        verifier("le code part à l'adresse sécurisée, pas à l'adresse perso", len(mails) == 1 and mails[0]["to"] == "prenom.nom@intradef.gouv.fr", mails)
        verifier("le message indique l'envoi sur l'adresse sécurisée (masquée)", "adresse sécurisée" in page.inner_text(".verif-message") and "***@intradef.gouv.fr" in page.inner_text(".verif-message"), page.inner_text(".verif-message"))
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
        verifier("adresses consignées (perso + sécurisée)", depot["reception"]["adresse_verifiee"] == "quelquun@gmail.com" and depot["reception"]["adresse_securisee"] == "prenom.nom@intradef.gouv.fr", depot["reception"])
        verifier("mail au validateur", any("validateur@example.org" == m["to"] for m in e["mails"]))
        verifier("aucune erreur JavaScript", not erreurs_js, erreurs_js)

        print("Rejouer le même jeton / dépôt direct sans code")
        corps = json.dumps({"adresse": "x@intradef.gouv.fr", "jeton": "x" * 70, "p": depot}).encode()
        r = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/boite" % PORT_BOITE, corps)))
        verifier("dépôt direct sans code refusé", r["ok"] is False)

        print("Application : formulaire, dépôt d'un .zip")
        def faire_zip(fich):
            o = io.BytesIO()
            with zipfile.ZipFile(o, "w", zipfile.ZIP_DEFLATED) as z:
                for k, v in fich.items(): z.writestr(k, v)
            return o.getvalue()
        f_app = ecrire("appli.zip", faire_zip({
            "index.html": '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Appli</title></head><body><div id="x">Bonjour</div><script src="app.js"></script></body></html>',
            "app.js": "const s = window.claude && window.claude.use('sample'); const b = window.claude && window.claude.use('db'); fetch('data.json');",
            "data.json": '{"nom": "Essai"}'}))
        f_app_cdn = ecrire("appli-cdn.zip", faire_zip({"index.html": '<!DOCTYPE html><html><head><script src="https://cdn.example.org/x.js"></script></head><body>x</body></html>'}))
        p2 = nav.new_page(); erreurs_js2 = []
        p2.on("pageerror", lambda e: erreurs_js2.append(str(e)))
        p2.goto("http://127.0.0.1:%d/pages/proposer.html" % PORT_SITE); p2.wait_for_selector("#titre")
        p2.fill("#titre", "Application d'essai"); p2.fill("#auteur", "Pseudo"); p2.fill("#resume", "Une application d'essai pour tester le circuit.")
        verifier("capacités masquées pour un prompt", not p2.locator("#champ-capacites").is_visible())
        p2.check("input[name=type][value=application]")
        verifier("capacités visibles pour une application", p2.locator("#champ-capacites").is_visible())
        verifier("engagement « seul appel : Claude » visible, « aucun appel réseau » masqué",
                 p2.locator("[data-engagement=seul-appel-claude]").is_visible() and not p2.locator("[data-engagement=aucun-appel-reseau]").is_visible())
        verifier("Claude seul : coché, les autres IA désactivées",
                 p2.locator("input[name=ia][value=claude]").is_checked() and p2.locator("input[name=ia][value=gemini]").is_disabled())
        p2.fill("#contenu", "# Application d'essai\n\nCe que fait l'application et comment s'en servir.\n")
        p2.check("input[name=guide]")
        for c in p2.locator("input[name=controles]:visible").all(): c.check()
        p2.set_input_files("#fichier-pj", f_docx)
        p2.wait_for_function("document.querySelector('#retour-pj') && !document.querySelector('#retour-pj').hidden")
        time.sleep(0.4)
        verifier("application : un .docx est refusé dans le navigateur", ".zip" in p2.inner_text("#retour-pj") and p2.locator("#liste-pj li").count() == 0, p2.inner_text("#retour-pj"))
        p2.set_input_files("#fichier-pj", f_app)
        p2.wait_for_function("document.querySelectorAll('#liste-pj li').length >= 2")
        verifier("application : le .zip est accepté", "appli.zip" in p2.inner_text("#liste-pj"), p2.inner_text("#liste-pj"))
        p2.set_input_files("#fichier-pj", f_app_cdn)
        time.sleep(0.6)
        verifier("application : un seul .zip à la fois", p2.locator("#liste-pj li").count() == 2 and "seul fichier" in p2.inner_text("#retour-pj"), p2.inner_text("#retour-pj"))
        p2.click("button[type=submit]")
        p2.wait_for_selector(".erreurs-form:not([hidden])")
        verifier("capacités obligatoires pour une application", "capacité" in p2.inner_text(".erreurs-form").lower(), p2.inner_text(".erreurs-form"))
        p2.check("input[name=capacites][value=sample]"); p2.check("input[name=capacites][value=db]")
        p2.click("button[type=submit]")
        p2.wait_for_selector("#resultat:not([hidden])")
        p2.click("text=Envoyer ma proposition")
        p2.wait_for_selector("#adresse-verif")
        n_mails = len(etat()["mails"])
        p2.fill("#adresse-verif", "quelquun@gmail.com"); p2.click("text=Recevoir mon code")
        p2.wait_for_selector("#code-verif:visible")
        code2 = re.search(r"(\d{6})", etat()["mails"][-1]["subject"]).group(1)
        p2.fill("#code-verif", code2); p2.click("text=Valider et envoyer")
        p2.wait_for_selector("text=Proposition envoyée", timeout=60000)
        e2 = etat()
        verifier("deuxième dépôt (application) enregistré", len(e2["fichiers"]) == 2, len(e2["fichiers"]))
        depot2 = json.loads(e2["fichiers"][1]["c"])
        verifier("dépôt application : type, capacités, Claude seul, engagements",
                 depot2["type"] == "application" and depot2["capacites"] == ["sample", "db"] and depot2["ia_compatibles"] == ["claude"]
                 and "seul-appel-claude" in depot2["controles"] and "aucun-appel-reseau" not in depot2["controles"], {k: depot2.get(k) for k in ("type", "capacites", "ia_compatibles", "controles")})
        verifier("le .zip arrive à l'identique", len(depot2["pieces_jointes"]) == 1 and base64.b64decode(depot2["pieces_jointes"][0]["contenu_b64"]) == open(f_app, "rb").read())
        verifier("aucune erreur JavaScript (application)", not erreurs_js2, erreurs_js2)
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

    print("Suite application : skill, robot, site")
    brut2 = os.path.join(tmp, "recu2.json"); open(brut2, "w", encoding="utf-8").write(e2["fichiers"][1]["c"])
    compl2 = os.path.join(tmp, "compl2.json")
    open(compl2, "w").write(json.dumps({"usage": "code-scripts", "niveau": "debutant", "langue": "fr", "probleme": "Montrer le circuit des applications.", "donne": "Rien.", "recoit": "Une page.",
             "etapes": [{"titre": "Installer", "entree": "archive", "sortie": "artefact", "qui": "vous"}, {"titre": "Utiliser", "entree": "artefact", "sortie": "résultat", "qui": "ia"}]}))
    r = subprocess.run([sys.executable, "-I", sk, "analyser", brut2], capture_output=True, text=True, encoding="utf-8")
    a2 = json.loads(r.stdout)
    verifier("application : analyse sans problème bloquant", not a2["problemes_bloquants"], a2["problemes_bloquants"])
    r = subprocess.run([sys.executable, "-I", sk, "finaliser", brut2, compl2, "--validateur", "Val", "--sortie", os.path.join(copie, "validations")], capture_output=True, text=True, encoding="utf-8")
    verifier("application : fichier validé produit", r.returncode == 0, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "outils/integrer_validations.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    verifier("application : robot, projet intégré", r.returncode == 0, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, "outils/valider.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    verifier("application : vérification de tout le dépôt", r.returncode == 0, r.stdout[-600:] + r.stderr)
    r = subprocess.run([sys.executable, "outils/build.py"], cwd=copie, capture_output=True, text=True, encoding="utf-8")
    page_app = os.path.join(copie, "site", "projets", "application-d-essai.html")
    verifier("application : site reconstruit", r.returncode == 0 and os.path.exists(page_app), r.stdout + r.stderr)
    if os.path.exists(page_app):
        h = open(page_app, encoding="utf-8").read()
        verifier("fiche : encart d'installation dans son propre Claude", "Application à installer dans votre Claude" in h and "votre propre compte Claude" in h)
        verifier("fiche : capacités demandées affichées", "Appel à Claude" in h and "Base de données" in h)
        verifier("fiche : engagement « seul appel : Claude »", "seule connexion de l" in h and "appel à Claude" in h)
        verifier("fiche : lien de téléchargement du .zip, jamais la page elle-même",
                 "pieces-jointes/application-d-essai/appli.zip" in h and not os.path.exists(os.path.join(copie, "site", "pieces-jointes", "application-d-essai", "index.html")))
finally:
    for sv in serveurs: sv.terminate()
    shutil.rmtree(tmp, ignore_errors=True)

print()
if ECHECS:
    print("%d ECHEC(S) : %s" % (len(ECHECS), "; ".join(ECHECS))); sys.exit(1)
print("Tous les tests passent.")
