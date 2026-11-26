# -*- coding: utf-8 -*-
"""Applications (.zip) : analyse de l'archive, skill valider-depot, robot et validateur du dépôt, de bout en bout.
Lancer :  python3 -I outils-validation/tests/test_application.py"""
import base64, hashlib, io, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = Path(ICI).parent.parent
SCRIPTS = RACINE / "outils-validation" / "valider-depot" / "scripts"
SCRIPT = SCRIPTS / "valider_depot.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RACINE / "outils"))
import analyse_pj  # noqa: E402

ECHECS = []


def verifier(nom, cond, detail=""):
    print(("  ok   " if cond else "  ECHEC ") + nom + ((" -> " + str(detail)[:400]) if (detail and not cond) else ""))
    if not cond:
        ECHECS.append(nom)


def fabriquer_zip(fichiers, dossier_racine=""):
    sortie = io.BytesIO()
    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, contenu in fichiers.items():
            z.writestr(dossier_racine + nom, contenu)
    return sortie.getvalue()


INDEX = ('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Appli</title><link rel="stylesheet" href="style.css"></head>'
         '<body><div id="x">Bonjour</div><script src="app.js"></script></body></html>')
APP_JS = ("const use = n => (window.claude && typeof window.claude.use === 'function') ? Promise.resolve(window.claude.use(n)) : Promise.resolve(null);\n"
          "const s = use('sample'); const b = use('db');\n"
          "fetch('data.json').then(r => r.json()).then(j => { document.getElementById('x').textContent = j.nom; });\n")
SAIN = {"index.html": INDEX, "app.js": APP_JS, "data.json": '{"nom": "Ouvertures"}', "style.css": "body{margin:0}",
        "moteur.wasm": b"\x00asm\x01\x00\x00\x00" + b"\x00" * 16}


def avec(**changes):
    d = dict(SAIN)
    for k, v in changes.items():
        k = k.replace("__", ".")
        if v is None:
            d.pop(k, None)
        else:
            d[k] = v
    return d


def analyser(octets, nom="app.zip"):
    return analyse_pj.analyser_fichier(nom, octets, application=True)


def refuse(nom, fichiers, mot):
    r = analyser(fabriquer_zip(fichiers))
    verifier(nom, bool(r["refus"]) and any(mot.lower() in x.lower() for x in r["refus"]), r["refus"] or "(aucun refus)")


print("Archive saine")
b = fabriquer_zip(SAIN)
r = analyser(b)
verifier("aucun refus", not r["refus"], r["refus"])
verifier("capacités détectées : db et sample", r["capacites_detectees"] == ["db", "sample"], r.get("capacites_detectees"))
verifier("archive rendue canonique : l'analyser de nouveau ne change rien (point fixe)",
         analyser(r["octets"])["octets"] == r["octets"] and analyser(r["octets"])["sha256"] == r["sha256"])
verifier("fetch() relatif signalé au validateur, pas refusé", any("fetch" in x for x in r["alertes"]), r["alertes"])
verifier("wasm signalé au validateur", any("WebAssembly" in x for x in r["alertes"]), r["alertes"])
verifier("dossier racine unique accepté", not analyser(fabriquer_zip(SAIN, "mon-appli/"))["refus"])
mac = dict(SAIN); mac["__MACOSX/._index.html"] = b"x"; mac[".DS_Store"] = b"x"
r2 = analyser(fabriquer_zip(mac))
verifier("__MACOSX et .DS_Store retirés avec alerte", not r2["refus"] and any("système" in x for x in r2["alertes"]) and r2["octets"] == r["octets"], r2["refus"] or r2["alertes"])

print("Archive refusée")
refuse("CDN dans une balise script", avec(index__html=INDEX.replace('src="app.js"', 'src="https://cdn.example.org/lib.js"')), "distante")
refuse("police en ligne dans le CSS", avec(style__css="@import url('https://fonts.example.org/x.css');"), "distante")
refuse("adresse distante dans un script", avec(app__js=APP_JS + "const u = 'https://exemple.org/collecte';"), "adresse distante")
refuse("adresse sans protocole dans un script", avec(app__js=APP_JS + "const u = '//exemple.org/collecte';"), "adresse distante")
refuse("WebSocket", avec(app__js=APP_JS + "new WebSocket('ws://a');"), "WebSocket")
refuse("eval", avec(app__js=APP_JS + "eval('1+1');"), "eval")
refuse("new Function", avec(app__js=APP_JS + "new Function('return 1');"), "new Function")
refuse("import dynamique", avec(app__js=APP_JS + "import('x.js');"), "import")
refuse("sendBeacon", avec(app__js=APP_JS + "navigator.sendBeacon('x');"), "sendBeacon")
refuse("service worker", avec(app__js=APP_JS + "navigator.serviceWorker.register('sw.js');"), "service worker")
refuse("iframe dans la page", avec(index__html=INDEX.replace("<div", '<iframe src="x.html"></iframe><div')), "iframe")
refuse("chemin d'évasion", {"index.html": INDEX, "../evil.js": "1"}, "chemin")
refuse("chemin absolu", {"index.html": INDEX, "/etc/x.js": "1"}, "chemin")
refuse("exécutable", avec(**{"outil.exe": b"MZ\x00\x00"}), "non accepté")
refuse("SVG (peut contenir du script)", avec(**{"icone.svg": "<svg><script>1</script></svg>"}), "non accepté")
refuse("archive imbriquée", avec(**{"autre.zip": b"PK\x03\x04"}), "non accepté")
refuse("sans index.html", avec(index__html=None, **{"accueil.html": INDEX}), "index.html")
refuse("wasm factice", avec(moteur__wasm=b"pas du wasm"), "extension")
refuse("JSON invalide", avec(data__json="{pas du json"), "JSON")
refuse("clé apparente dans un script", avec(app__js=APP_JS + "const k = 'sk-ant-api03-" + "A" * 40 + "';"), "clé")
refuse("fichier vide", avec(**{"vide.txt": ""}), "vide")
refuse("noms en double (casse)", {"index.html": INDEX, "A.js": "1", "a.js": "2"}, "double")
bombe = fabriquer_zip(avec(**{"gros.txt": b"0" * (12 * 1024 * 1024)}))
r = analyser(bombe)
verifier("bombe de décompression refusée", bool(r["refus"]) and any("compression" in x or "démesurée" in x for x in r["refus"]), r["refus"] or len(bombe))
r = analyser(b"PK\x03\x04pas une archive")
verifier("archive illisible refusée", bool(r["refus"]))
r = analyse_pj.analyser_fichier("app.zip", b, application=False)
verifier("un .zip hors type application reste refusé", bool(r["refus"]))
r = analyse_pj.analyser_fichier("page.html", INDEX.encode(), application=True)
verifier("une application n'accepte pas un .html seul", bool(r["refus"]))
lot = analyse_pj.analyser_lot([("a.zip", b), ("b.zip", b)], application=True)
verifier("une application = exactement un fichier", bool(lot["refus"]))

print("Fichier de dépôt : skill puis robot")


def pj(nom, octets):
    return {"nom": nom, "taille": len(octets), "sha256": hashlib.sha256(octets).hexdigest(), "contenu_b64": base64.b64encode(octets).decode()}


def depot(octets, **changes):
    d = {"format": "bibliotheque-ia-terre/proposition", "titre": "Appli de test", "resume": "Une application d'essai.", "type": "application",
         "usage": "code-scripts", "niveau": "debutant", "langue": "fr", "auteur": "Pseudo",
         "probleme": "Montrer le circuit.", "donne": "Rien.", "recoit": "Une page.",
         "etapes": [{"titre": "Ouvrir", "entree": "archive", "sortie": "page", "qui": "vous"}, {"titre": "Jouer", "entree": "page", "sortie": "résultat", "qui": "ia"}],
         "ia_compatibles": ["claude"], "capacites": ["sample", "db"],
         "controles": ["aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "seul-appel-claude"],
         "contenu": "# Appli de test\n\nCe que fait l'application, et comment s'en servir.\n",
         "pieces_jointes": [pj("appli.zip", octets)], "reception": {"adresse": "x@intradef.gouv.fr"}}
    d.update(changes)
    return d


def lancer(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT)] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8")


def ecrire(dossier, nom, obj):
    c = os.path.join(dossier, nom)
    open(c, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False))
    return c


with tempfile.TemporaryDirectory() as tmp:
    c = ecrire(tmp, "ok.json", depot(b))
    a = json.loads(lancer("analyser", c).stdout)
    verifier("analyser : aucun problème bloquant", not a["problemes_bloquants"], a["problemes_bloquants"])
    compl = ecrire(tmp, "compl.json", {})
    r = lancer("finaliser", c, compl, "--validateur", "Val", "--sortie", tmp)
    verifier("finaliser réussit", r.returncode == 0, r.stdout + r.stderr)
    valide = os.path.join(tmp, "valide-appli-de-test.json")
    v = json.load(open(valide, encoding="utf-8"))
    verifier("l'archive validée est dans le fichier", len(v["pieces_jointes"]) == 1 and v["capacites"] == ["sample", "db"])

    # Robot : intégration dans un dossier de projets temporaire, puis vérification complète
    import integrer_validations as iv, importer, commun, valider  # noqa: E402
    projets = Path(tmp) / "projets"
    projets.mkdir()
    iv.PROJETS = projets
    vocab = commun.charger_vocabulaires()
    try:
        ident, d = iv.integrer(Path(valide), vocab, set())
        verifier("le robot fabrique le projet", (projets / ident / "pieces-jointes" / "appli.zip").exists(), ident)
        fiche = (projets / ident / "README.md").read_text(encoding="utf-8")
        verifier("la fiche déclare type, capacités et Claude seul", "type: application" in fiche and "capacites: [sample, db]" in fiche and "ia_compatibles: [claude]" in fiche, fiche[:500])
        verifier("la fiche porte « seul-appel-claude » et pas « aucun-appel-reseau »", "seul-appel-claude" in fiche and "aucun-appel-reseau" not in fiche)
        inst = (projets / ident / "installation.md").read_text(encoding="utf-8")
        verifier("l'installation contient le message de publication avec les capacités", "Publie ces fichiers comme un artefact" in inst and "`db`" in inst and "`sample`" in inst, inst)
        rapport = importer.verifier(projets / ident, ident, set(), vocab)
        verifier("le projet fabriqué passe toutes les vérifications", not rapport.erreurs, rapport.erreurs)
    except importer.ErreurProposition as e:
        verifier("le robot fabrique le projet", False, e)

    print("Dépôts incohérents")
    for libelle, changes in [
        ("capacité utilisée mais non déclarée", {"capacites": ["sample"]}),
        ("aucune capacité déclarée", {"capacites": []}),
        ("capacité inconnue", {"capacites": ["sample", "db", "root"]}),
        ("autre IA que Claude", {"ia_compatibles": ["claude", "gemini"]}),
        ("engagement faux « aucun-appel-reseau »", {"controles": ["aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "aucun-appel-reseau"]}),
        ("engagement « seul-appel-claude » manquant", {"controles": ["aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse"]}),
    ]:
        a = json.loads(lancer("analyser", ecrire(tmp, "i.json", depot(b, **changes))).stdout)
        verifier(libelle + " : problème bloquant", bool(a["problemes_bloquants"]), a)
        r = lancer("finaliser", ecrire(tmp, "i2.json", depot(b, **changes)), compl, "--validateur", "Val", "--sortie", os.path.join(tmp, "z"))
        verifier(libelle + " : finaliser refuse", r.returncode == 1, r.stdout)
    sans = depot(b); sans["pieces_jointes"] = []
    r = lancer("finaliser", ecrire(tmp, "s.json", sans), compl, "--validateur", "Val", "--sortie", os.path.join(tmp, "z"))
    verifier("application sans archive refusée", r.returncode == 1)
    prompt = depot(b, type="prompt", capacites=[], controles=["aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "aucun-appel-reseau"])
    prompt["contenu"] = "Texte"
    r = lancer("finaliser", ecrire(tmp, "p.json", prompt), compl, "--validateur", "Val", "--sortie", os.path.join(tmp, "z"))
    verifier("un prompt avec un .zip est refusé", r.returncode == 1, r.stdout)
    piege = depot(fabriquer_zip(avec(app__js=APP_JS + "eval('1');")))
    r = lancer("finaliser", ecrire(tmp, "e.json", piege), compl, "--validateur", "Val", "--sortie", os.path.join(tmp, "z"))
    verifier("archive piégée : finaliser refuse", r.returncode == 1 and "eval" in r.stdout, r.stdout)
    verifier("archive piégée : aucun fichier produit", not os.path.exists(os.path.join(tmp, "z")))

print("Archive canonique : indépendante de la compression (zlib varie selon la machine)")
def zip_niveau(niveau):
    sortie = io.BytesIO()
    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED, compresslevel=niveau) as z:
        for nom, contenu in SAIN.items():
            z.writestr(nom, contenu)
    return sortie.getvalue()
bruts = [zip_niveau(1), zip_niveau(9), fabriquer_zip(SAIN)]
verifier("les compressions donnent des octets bruts différents", len({hashlib.sha256(b).hexdigest() for b in bruts}) > 1)
canos = [analyser(b)["octets"] for b in bruts]
verifier("même archive canonique quelle que soit la compression", len({hashlib.sha256(c).hexdigest() for c in canos}) == 1)
verifier("l'archive canonique est un point fixe", analyser(canos[0])["octets"] == canos[0])

print("Application réelle fournie (échecs contre Claude)")
reel = "/mnt/user-data/uploads/eba9d5ce-echecs-contre-claude.zip"
if os.path.exists(reel):
    r = analyser(open(reel, "rb").read())
    verifier("refusée tant que les CDN ne sont pas embarqués (2 motifs, pas d'autre)", len(r["refus"]) == 2 and all("index.html" in x for x in r["refus"]), r["refus"])
    verifier("les fichiers du moteur et les données passent", not any("stockfish" in x or "openings" in x for x in r["refus"]))
else:
    print("  (archive réelle absente : ignoré)")

print("\n" + (str(len(ECHECS)) + " ECHEC(S) : " + ", ".join(ECHECS) if ECHECS else "Tous les tests passent."))
sys.exit(1 if ECHECS else 0)
