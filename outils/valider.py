# -*- coding: utf-8 -*-
"""Vérifie les projets avant publication.

Usage :
    python outils/valider.py              # tous les projets
    python outils/valider.py mon-projet   # un ou plusieurs projets

Code de sortie : 0 si tout est conforme, 1 s'il reste au moins une erreur.
Les avertissements ne bloquent pas : ils signalent un point à regarder.
"""
import re
import sys

from commun import (
    CHAMPS_FACULTATIFS, CHAMPS_OBLIGATOIRES, EXTENSIONS_AUTORISEES, PROJETS, RACINE, SECTIONS_OBLIGATOIRES,
    TAILLE_MAX_FICHIER, ErreurFiche, analyser_filiation, analyser_fonctionnement, analyser_installation,
    charger_vocabulaires, console_utf8, est_piece_jointe, fichiers_projet, liste_dossiers_projets, lire_projet,
)

sys.path.insert(0, str(RACINE / "outils-validation" / "valider-depot" / "scripts"))   # même analyse que le skill et le robot

LETTRES = "A-Za-zÀ-ÿ"
MARQUAGES = re.compile(
    r"(?<![%s])(DIFFUSION\s+RESTREINTE|CONFIDENTIEL(?:\s+D[ÉE]FENSE)?|SECRET(?:\s+D[ÉE]FENSE)?|"
    r"TR[ÈE]S\s+SECRET|NON\s+PROT[ÉE]G[ÉE]|RESTRICTED|NATO\s+(?:SECRET|CONFIDENTIAL|RESTRICTED))(?![%s])" % (LETTRES, LETTRES)
)
COURRIEL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
DOMAINES_EXEMPLES = ("example.com", "example.org", "example.net", ".invalid", ".test", ".example")
TELEPHONE = re.compile(r"(?<![\d.])(?:\+33|0033|0)[1-9](?:[ .-]?\d{2}){4}(?![\d])")
ADRESSE_IP = re.compile(r"(?<!\d)(?<!\d\.)(?:\d{1,3}\.){3}\d{1,3}(?!\d)(?!\.\d)")
SECRETS = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"
    r"|(?i:api[_-]?key|jeton|token|mot[_ ]de[_ ]passe|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}"
)
URL = re.compile(r"https?://[^\s)>\"']+")
CODE_RESEAU = re.compile(
    r"^\s*(?:import|from)\s+(socket|urllib|requests|http|httpx|ftplib|smtplib|telnetlib|paramiko|aiohttp|websockets?|ssl|xmlrpc)\b"
)
CODE_DANGEREUX = re.compile(r"\b(os\.system|subprocess|eval\s*\(|exec\s*\(|__import__|pickle|ctypes)\b")


class Rapport:
    def __init__(self, nom):
        self.nom = nom
        self.erreurs = []
        self.avertissements = []

    def erreur(self, message):
        self.erreurs.append(message)

    def avertir(self, message):
        self.avertissements.append(message)


def _numero(texte, position):
    return texte.count("\n", 0, position) + 1


def _verifier_pieces_jointes(rapport, dossier, pieces):
    """Pièces jointes : mêmes contrôles que le skill valider-depot (aucune macro, aucun objet actif, aucun mot de passe…)."""
    import analyse_pj
    for rel in pieces:
        if len(rel.parts) != 2:
            rapport.erreur("%s : les pièces jointes doivent être directement dans pieces-jointes/ (pas de sous-dossier)." % rel.as_posix())
    lot = analyse_pj.analyser_lot([(r.name, (dossier / r).read_bytes()) for r in pieces])
    for x in lot["refus"]:
        rapport.erreur("pieces-jointes : " + x)
    for f in lot["fichiers"]:
        if f["nom"] != f["nom_origine"]:
            rapport.erreur("pieces-jointes/%s : nom de fichier à simplifier (« %s »)." % (f["nom_origine"], f["nom"]))
        if not f["refus"] and f["sha256"] != f["sha256_origine"]:
            rapport.erreur("pieces-jointes/%s : des métadonnées de personne n'ont pas été anonymisées (repasser par le skill valider-depot)." % f["nom_origine"])
    for x in lot["alertes"]:
        rapport.avertir("pieces-jointes : " + x)


def analyser_contenu(rapport, chemin_affiche, texte, est_python):
    for m in MARQUAGES.finditer(texte):
        rapport.erreur("%s, ligne %d : mention de protection « %s ». Aucun contenu protégé n'a sa place ici."
                       % (chemin_affiche, _numero(texte, m.start()), m.group(1)))
    for m in COURRIEL.finditer(texte):
        domaine = m.group(1).lower()
        if domaine.endswith(DOMAINES_EXEMPLES) or domaine in DOMAINES_EXEMPLES:
            continue
        if "def.gouv.fr" in domaine or "intradef" in domaine:
            rapport.erreur("%s, ligne %d : adresse du ministère (« %s »). Utilisez nom@example.org."
                           % (chemin_affiche, _numero(texte, m.start()), m.group(0)))
        else:
            rapport.erreur("%s, ligne %d : adresse électronique « %s ». Utilisez nom@example.org."
                           % (chemin_affiche, _numero(texte, m.start()), m.group(0)))
    for m in TELEPHONE.finditer(texte):
        rapport.erreur("%s, ligne %d : numéro de téléphone « %s »." % (chemin_affiche, _numero(texte, m.start()), m.group(0).strip()))
    for m in ADRESSE_IP.finditer(texte):
        octets = [int(x) for x in m.group(0).split(".")]
        if all(o <= 255 for o in octets):
            rapport.erreur("%s, ligne %d : adresse IP « %s »." % (chemin_affiche, _numero(texte, m.start()), m.group(0)))
    for m in SECRETS.finditer(texte):
        rapport.erreur("%s, ligne %d : clé, jeton ou mot de passe apparent." % (chemin_affiche, _numero(texte, m.start())))
    for m in URL.finditer(texte):
        if "example." not in m.group(0):
            rapport.avertir("%s, ligne %d : lien externe %s — le relecteur doit le vérifier."
                            % (chemin_affiche, _numero(texte, m.start()), m.group(0)))
    if est_python:
        for numero, ligne in enumerate(texte.split("\n"), start=1):
            if CODE_RESEAU.match(ligne):
                rapport.erreur("%s, ligne %d : le script contacte (ou peut contacter) un service extérieur : %s"
                               % (chemin_affiche, numero, ligne.strip()))
            if CODE_DANGEREUX.search(ligne):
                rapport.erreur("%s, ligne %d : instruction non autorisée dans un script partagé : %s"
                               % (chemin_affiche, numero, ligne.strip()))


def valider_projet(projet, tous_ids, vocab):
    pid = projet["id"]
    rapport = Rapport(pid)
    meta, dossier = projet["meta"], projet["dossier"]

    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", pid):
        rapport.erreur("Le nom du dossier « %s » doit être en minuscules, chiffres et tirets (ex. mon-projet)." % pid)

    for champ in CHAMPS_OBLIGATOIRES:
        if champ not in meta or meta[champ] in ("", []) and champ != "controles":
            rapport.erreur("README.md : le champ « %s » est manquant ou vide." % champ)
    connus = set(CHAMPS_OBLIGATOIRES) | set(CHAMPS_FACULTATIFS)
    for champ in meta:
        if champ not in connus:
            rapport.erreur("README.md : le champ « %s » n'existe pas. Champs possibles : %s." % (champ, ", ".join(sorted(connus))))

    def valeur_dans(champ, vocabulaire):
        v = meta.get(champ)
        if isinstance(v, str) and v and v not in vocabulaire:
            rapport.erreur("README.md : %s = « %s » n'est pas une valeur autorisée (%s)." % (champ, v, ", ".join(vocabulaire)))

    for champ in ("type", "usage", "langue", "niveau", "statut", "donnees"):
        valeur_dans(champ, vocab[champ])

    if isinstance(meta.get("titre"), str) and len(meta["titre"]) > 80:
        rapport.erreur("README.md : le titre dépasse 80 caractères.")
    if isinstance(meta.get("resume"), str) and len(meta["resume"]) > 200:
        rapport.erreur("README.md : le résumé dépasse 200 caractères.")
    # Deux régimes de données : exemples fictifs (règle d'origine) ou faits réels de sources ouvertes (exception encadrée).
    if meta.get("donnees") and meta["donnees"] not in ("exemples-fictifs", "sources-ouvertes"):
        rapport.erreur("README.md : donnees doit valoir « exemples-fictifs » ou « sources-ouvertes ».")

    ia = meta.get("ia_compatibles", [])
    if isinstance(ia, list):
        for v in ia:
            if v not in vocab["ia"]:
                rapport.erreur("README.md : ia_compatibles contient « %s » (autorisé : %s)." % (v, ", ".join(vocab["ia"])))
        if "toutes" in ia and len(ia) > 1:
            rapport.erreur("README.md : « toutes » ne se combine pas avec d'autres IA.")
    elif ia:
        rapport.erreur("README.md : ia_compatibles doit être une liste, par exemple [claude, mistral].")

    etiquettes = meta.get("etiquettes", [])
    if not isinstance(etiquettes, list):
        rapport.erreur("README.md : etiquettes doit être une liste, par exemple [notes, fiche].")
    else:
        if len(etiquettes) > 5:
            rapport.erreur("README.md : 5 étiquettes au maximum (%d trouvées)." % len(etiquettes))
        for e in etiquettes:
            if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", e):
                rapport.erreur("README.md : l'étiquette « %s » doit être en minuscules sans accent ni espace (ex. veille-presse)." % e)

    controles = meta.get("controles", [])
    if not isinstance(controles, list):
        rapport.erreur("README.md : controles doit être une liste.")
    else:
        if meta.get("donnees") == "sources-ouvertes":
            # Régime « sources ouvertes » : on n'exige pas « aucune-donnee-reelle » ni « exemples-fictifs »,
            # qui seraient faux ; on exige à la place l'absence d'information protégée et la citation des sources.
            requis = ["aucune-donnee-protegee", "sources-citees", "aucun-nom-adresse"]
        else:
            requis = ["aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "aucun-appel-reseau"]
        for c in requis:
            if c not in controles:
                rapport.erreur("README.md : le contrôle « %s » n'est pas attesté (%s). Vérifiez le point, puis ajoutez-le à controles."
                               % (c, vocab["controles"][c]))
        for c in controles:
            if c not in vocab["controles"]:
                rapport.erreur("README.md : contrôle inconnu « %s »." % c)

    statut = meta.get("statut")
    relu_par = meta.get("relu_par", "")
    if statut in ("relu", "recommande") and (not relu_par or relu_par.startswith("[")):
        rapport.erreur("README.md : le statut « %s » exige un relecteur réel dans relu_par." % statut)

    genre, ids = analyser_filiation(meta.get("filiation", ""))
    if genre not in vocab["filiation"]:
        rapport.erreur("README.md : filiation = « %s » inconnue (autorisé : original, adaptation:id, fusion:id1,id2, version-simplifiee:id)." % meta.get("filiation"))
    elif genre == "original" and ids:
        rapport.erreur("README.md : « original » ne prend pas d'identifiant.")
    elif genre != "original" and not ids:
        rapport.erreur("README.md : filiation « %s » doit indiquer un projet, par exemple %s:id-du-projet." % (genre, genre))
    for i in ids:
        if i not in tous_ids:
            rapport.erreur("README.md : filiation cite « %s », qui n'existe pas dans projets/." % i)
        if i == pid:
            rapport.erreur("README.md : un projet ne peut pas être son propre parent.")
    nv = meta.get("version_plus_recente", "aucune")
    if nv not in ("", "aucune") and nv not in tous_ids:
        rapport.erreur("README.md : version_plus_recente cite « %s », qui n'existe pas." % nv)

    # Fiche : sections et texte de modèle
    titres = re.findall(r"^##\s+(.*?)\s*$", projet["corps"], re.MULTILINE)
    for section in SECTIONS_OBLIGATOIRES:
        if section not in titres:
            rapport.erreur("README.md : la section « ## %s » est absente de la fiche." % section)
    if "À remplacer" in projet["corps"] or "A remplacer" in projet["corps"]:
        rapport.erreur("README.md : du texte du modèle (« À remplacer ») est encore présent.")

    # Fichiers
    fichiers = fichiers_projet(dossier)
    noms = {f.as_posix() for f in fichiers}
    pieces = []
    for rel in fichiers:
        p = dossier / rel
        if est_piece_jointe(rel):
            pieces.append(rel)
            continue
        if rel.suffix.lower() not in EXTENSIONS_AUTORISEES:
            rapport.erreur("%s : type de fichier non autorisé (autorisés : %s)." % (rel.as_posix(), " ".join(sorted(EXTENSIONS_AUTORISEES))))
            continue
        if p.stat().st_size > TAILLE_MAX_FICHIER:
            rapport.erreur("%s : fichier trop volumineux (maximum %d Ko)." % (rel.as_posix(), TAILLE_MAX_FICHIER // 1000))
            continue
        try:
            texte = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            rapport.erreur("%s : le fichier doit être enregistré en UTF-8." % rel.as_posix())
            continue
        analyser_contenu(rapport, rel.as_posix(), texte, rel.suffix.lower() == ".py")
        if rel.name != "README.md" and ("À remplacer" in texte or "A remplacer" in texte):
            rapport.erreur("%s : du texte du modèle (« À remplacer ») est encore présent." % rel.as_posix())

    if pieces:
        _verifier_pieces_jointes(rapport, dossier, pieces)

    # Fichiers imposés selon le type
    t = meta.get("type")
    if t == "prompt" and "prompt.md" not in noms:
        rapport.erreur("Un projet de type « prompt » doit contenir prompt.md (le texte à copier-coller).")
    if t == "projet" and "instructions.md" not in noms:
        rapport.erreur("Un projet de type « projet » doit contenir instructions.md.")
    if t == "script" and not any(n.endswith(".py") for n in noms):
        rapport.erreur("Un projet de type « script » doit contenir au moins un fichier .py.")
    if t == "skill":
        if "SKILL.md" not in noms:
            rapport.erreur("Un projet de type « skill » doit contenir SKILL.md.")
        else:
            try:
                from commun import analyser_front_matter, decouper_front_matter
                lignes, _ = decouper_front_matter((dossier / "SKILL.md").read_text(encoding="utf-8"))
                m = analyser_front_matter(lignes)
                for c in ("name", "description"):
                    if not m.get(c):
                        rapport.erreur("SKILL.md : le champ « %s » est manquant dans l'en-tête." % c)
            except ErreurFiche as e:
                rapport.erreur("SKILL.md : %s" % e)

    # Schéma de fonctionnement
    if "fonctionnement.md" in noms:
        try:
            etapes = analyser_fonctionnement((dossier / "fonctionnement.md").read_text(encoding="utf-8"))
            if len(etapes) < 2:
                rapport.erreur("fonctionnement.md : au moins deux étapes (## Titre) sont attendues.")
            for n, e in enumerate(etapes, start=1):
                if e["qui"] not in ("vous", "ia"):
                    rapport.erreur("fonctionnement.md, étape %d « %s » : « - qui: » doit valoir vous ou ia." % (n, e["titre"]))
                if not e["entree"] or not e["sortie"]:
                    rapport.erreur("fonctionnement.md, étape %d « %s » : « - entrée: » et « - sortie: » sont obligatoires." % (n, e["titre"]))
        except ErreurFiche as e:
            rapport.erreur(str(e))
    else:
        rapport.avertir("fonctionnement.md est absent : l'onglet « Fonctionnement » ne s'affichera pas.")

    # Installation
    if "installation.md" in noms:
        try:
            commun, par_ia = analyser_installation((dossier / "installation.md").read_text(encoding="utf-8"), vocab["ia"])
            if not commun and not par_ia:
                rapport.erreur("installation.md est vide.")
            if isinstance(ia, list) and "toutes" not in ia:
                for k in par_ia:
                    if k not in ia and k != "toutes":
                        rapport.erreur("installation.md : section pour « %s », qui n'est pas dans ia_compatibles." % vocab["ia"][k])
        except ErreurFiche as e:
            rapport.erreur(str(e))
    else:
        rapport.avertir("installation.md est absent : l'onglet « Installer » ne s'affichera pas.")

    return rapport


def main(argv):
    console_utf8()
    vocab = charger_vocabulaires()
    dossiers = liste_dossiers_projets()
    tous_ids = {d.name for d in dossiers}
    demandes = argv[1:]
    for d in demandes:
        if d not in tous_ids:
            print("Projet introuvable : %s" % d)
            return 2
    rapports = []
    for dossier in dossiers:
        if demandes and dossier.name not in demandes:
            continue
        try:
            projet = lire_projet(dossier)
        except ErreurFiche as e:
            r = Rapport(dossier.name)
            r.erreur("README.md : %s" % e)
            rapports.append(r)
            continue
        rapports.append(valider_projet(projet, tous_ids, vocab))

    total_erreurs = 0
    for r in rapports:
        etat = "OK" if not r.erreurs else "ERREUR"
        print("[%s] %s" % (etat, r.nom))
        for e in r.erreurs:
            print("    erreur       : %s" % e)
        for a in r.avertissements:
            print("    avertissement: %s" % a)
        total_erreurs += len(r.erreurs)
    n_ok = sum(1 for r in rapports if not r.erreurs)
    print("\n%d projet(s) conforme(s) sur %d. %d erreur(s)." % (n_ok, len(rapports), total_erreurs))
    return 1 if total_erreurs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
