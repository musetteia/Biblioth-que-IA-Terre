# -*- coding: utf-8 -*-
"""Génère le site statique dans site/ à partir des projets.

Usage : python outils/build.py

Le site généré fonctionne par simple double-clic sur site/index.html :
aucun serveur, aucun réseau, aucune installation.
La génération refuse de continuer si un projet n'est pas valide.
"""
import hashlib
import json
import re
import shutil
import sys
import zipfile

from commun import (
    INTERFACE, PROJETS, RACINE, ErreurFiche, analyser_filiation, analyser_fonctionnement, analyser_installation,
    charger_json, charger_vocabulaires, console_utf8, fichiers_projet, historique_git, liste_dossiers_projets,
    lire_projet,
)
from rendu import echapper, inline, rendre
import valider

SITE = RACINE / "site"
ORDRE_STATUT = {"recommande": 0, "relu": 1, "propose": 2}
PAGES = [
    ("DEBUTER.md", "debuter", "Débuter"),
    ("REGLES.md", "regles", "Règles de publication"),
    ("CONTRIBUER.md", "contribuer", "Contribuer"),
]
TITRES_COURTS = {"debuter": "Débuter", "regles": "Règles", "contribuer": "Contribuer"}

# Pictogrammes au trait (24 x 24), repris de la charte du Cercle IA EdG-T.
_TRAITS = {
    "catalogue": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "prompt": '<path d="M5 5h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H10l-4.5 3.5V16H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/><path d="M8 9.5h8M8 12.5h5"/>',
    "skill": '<path d="M12 3.5l8.5 4.5L12 12.5 3.5 8z"/><path d="M3.5 12L12 16.5 20.5 12"/><path d="M3.5 16L12 20.5 20.5 16"/>',
    "projet": '<path d="M3.5 7a1.5 1.5 0 0 1 1.5-1.5h4.5l2 2.5H19a1.5 1.5 0 0 1 1.5 1.5v8.5A1.5 1.5 0 0 1 19 19.5H5A1.5 1.5 0 0 1 3.5 18z"/>',
    "script": '<path d="M8.5 8L4.5 12l4 4M15.5 8l4 4-4 4M13.5 5.5l-3 13"/>',
    "debuter": '<path d="M6 3.5h11a1 1 0 0 1 1 1v15l-3-2-3 2-3-2-3 2v-15a1 1 0 0 1 1-1z"/><path d="M9 8h6M9 11.5h6"/>',
    "regles": '<path d="M12 3.5l7 3v5.5c0 4.2-3 7.2-7 8.5-4-1.3-7-4.3-7-8.5V6.5z"/><path d="M8.8 12l2.2 2.2 4.3-4.4"/>',
    "contribuer": '<circle cx="9" cy="9" r="3"/><circle cx="17" cy="10" r="2.3"/><path d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5M14.5 15.2c.8-.7 1.6-1 2.5-1 2 0 3.4 1.4 3.8 3.8"/>',
    "deposer": '<rect x="3.5" y="5.5" width="17" height="13" rx="1.5"/><path d="M4 7l8 6 8-6"/>',
    "video": '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M10.5 9.5v5l4.5-2.5z"/>',
}


def icone(nom):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true">%s</svg>' % _TRAITS.get(nom, _TRAITS["debuter"]))


# Ce que l'on trouve derrière chaque type (tuiles de l'accueil).
DESCRIPTIONS_TYPES = {
    "prompt": ("Prompts", "Consignes prêtes à copier dans l'IA"),
    "skill": ("Skills", "Savoir-faire à importer dans l'IA"),
    "projet": ("Projets", "Consignes et fichiers prêts à installer"),
    "script": ("Scripts", "Petits programmes pour votre poste"),
}
DESCRIPTIONS_PAGES = {
    "debuter": "Installer et utiliser une solution",
    "regles": "Ce qui peut être publié, et comment",
    "contribuer": "Qui relit, qui publie, comment aider",
}


def js_json(objet):
    s = json.dumps(objet, ensure_ascii=False)
    return s.replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def remplir(gabarit, valeurs):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: valeurs.get(m.group(1), ""), gabarit)


class Constructeur:
    def __init__(self):
        self.site = charger_json("site.json")
        self.vocab = charger_vocabulaires()
        self.gabarit = (INTERFACE / "gabarit.html").read_text(encoding="utf-8")
        self.pages_docs = [(f, s, t) for f, s, t in PAGES if (RACINE / f).exists()]

    # -- coque commune ------------------------------------------------------
    def nav(self, racine, active):
        liens = [("Catalogue", racine + "catalogue.html", "catalogue")]
        for _, slug, titre in self.pages_docs:
            liens.append((TITRES_COURTS.get(slug, titre), racine + "pages/%s.html" % slug, slug))
        liens.append(("Déposer", racine + "pages/proposer.html", "proposer"))
        return "".join(
            '<a class="nb" href="%s"%s>%s<span>%s</span></a>'
            % (url, ' aria-current="page"' if cle == active else "", icone("deposer" if cle == "proposer" else cle), echapper(titre))
            for titre, url, cle in liens
        )

    def page(self, chemin_sortie, titre_page, contenu, racine, active, donnees=None, scripts=(), classe="", garde=""):
        s = self.site
        scripts = tuple(scripts) + ("coque.js",)
        valeurs = {
            "titre_page": echapper(titre_page),
            "racine": racine,
            "protection": echapper(s.get("protection", "NON PROTÉGÉ")),
            "signature": echapper(s.get("signature", "Solutions IA partagées")),
            "garde": garde,
            "nav": self.nav(racine, active),
            "nom": echapper(s["nom"]),
            "sous_nom": echapper(s["sous_nom"]),
            "contenu": contenu,
            "pied": echapper(s["pied"]),
            "pied_droite": echapper(s["pied_droite"]),
            "classe_corps": classe,
            "donnees": ('<script type="application/json" id="donnees">%s</script>' % js_json(donnees)) if donnees is not None else "",
            "scripts": "".join('<script src="%sassets/%s?v=%s"></script>' % (racine, nom, self.version(nom)) for nom in scripts),
        }
        chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
        html = remplir(self.gabarit, valeurs)
        # « ?v= » change à chaque modification de la feuille de style : les navigateurs rechargent la nouvelle version.
        html = html.replace('assets/style.css"', 'assets/style.css?v=%s"' % self.version("style.css"))
        chemin_sortie.write_text(html, encoding="utf-8")

    def version(self, nom):
        """Empreinte courte d'un fichier de l'interface. Elle change dès que le fichier change, ce qui oblige
        les navigateurs à télécharger la nouvelle version au lieu de garder l'ancienne en mémoire."""
        f = INTERFACE / nom
        return hashlib.sha256(f.read_bytes()).hexdigest()[:10] if f.is_file() else "0"

    # -- projets ------------------------------------------------------------
    def lire_tous(self):
        dossiers = liste_dossiers_projets()
        tous_ids = {d.name for d in dossiers}
        projets, bilan = [], []
        for d in dossiers:
            try:
                p = lire_projet(d)
            except ErreurFiche as e:
                bilan.append("%s : %s" % (d.name, e))
                continue
            rapport = valider.valider_projet(p, tous_ids, self.vocab)
            for e in rapport.erreurs:
                bilan.append("%s : %s" % (d.name, e))
            projets.append(p)
        if bilan:
            print("La génération s'arrête : %d erreur(s) de validation." % len(bilan))
            for ligne in bilan:
                print("  - " + ligne)
            print("\nCorrigez-les (python outils/valider.py donne le détail), puis relancez.")
            sys.exit(1)
        return projets

    def libelle(self, categorie, valeur):
        return self.vocab[categorie].get(valeur, valeur)

    def resume_catalogue(self, p):
        m = p["meta"]
        return {
            "id": p["id"], "titre": m["titre"], "resume": m["resume"], "type": m["type"], "usage": m["usage"],
            "ia": m["ia_compatibles"], "niveau": m["niveau"], "statut": m["statut"], "version": m["version"],
            "etiquettes": m.get("etiquettes", []), "langue": m["langue"],
        }

    def creer_archive(self, pid, dossier):
        """Crée telechargements/<id>.zip : le dossier du projet, avec son nom pour racine de l'archive."""
        cible = SITE / "telechargements"
        cible.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(cible / ("%s.zip" % pid)), "w", zipfile.ZIP_DEFLATED) as z:
            for rel in fichiers_projet(dossier):
                info = zipfile.ZipInfo("%s/%s" % (pid, rel.as_posix()), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, (dossier / rel).read_bytes())

    def construire_projet(self, p, tous):
        m, dossier = p["meta"], p["dossier"]
        pid = p["id"]
        self.creer_archive(pid, dossier)
        telecharger = (
            '<p class="telechargement"><a class="bouton" href="../telechargements/%s.zip" download>Télécharger le projet (.zip)</a> '
            '<span class="doux">Un seul fichier, qui contient tous les fichiers du projet.</span></p>' % echapper(pid)
        )
        fichiers = []
        for rel in fichiers_projet(dossier):
            texte = (dossier / rel).read_text(encoding="utf-8")
            fichiers.append({"chemin": rel.as_posix(), "taille": len(texte.encode("utf-8")), "texte": texte})
        noms = {f["chemin"] for f in fichiers}

        etapes = []
        if "fonctionnement.md" in noms:
            for e in analyser_fonctionnement((dossier / "fonctionnement.md").read_text(encoding="utf-8")):
                e["texte_html"] = inline(e["texte"]) if e["texte"] else ""
                etapes.append(e)

        installation = None
        if "installation.md" in noms:
            commun, par_ia = analyser_installation((dossier / "installation.md").read_text(encoding="utf-8"), self.vocab["ia"])
            ias = [k for k in self.vocab["ia"] if k != "toutes"] if "toutes" in m["ia_compatibles"] else list(m["ia_compatibles"])
            installation = {
                "commun_html": rendre(commun) if commun else "",
                "par_ia_html": {k: rendre(v) for k, v in par_ia.items()},
                "ias": [{"id": k, "libelle": self.libelle("ia", k)} for k in ias],
            }

        genre, ids_parents = analyser_filiation(m["filiation"])
        lignee = {
            "genre": genre, "genre_libelle": self.libelle("filiation", genre),
            "parents": [{"id": i, "titre": next(x["meta"]["titre"] for x in tous if x["id"] == i)} for i in ids_parents],
            "adaptations": [],
            "plus_recente": None,
        }
        for x in tous:
            g, ids = analyser_filiation(x["meta"]["filiation"])
            if pid in ids:
                lignee["adaptations"].append({"id": x["id"], "titre": x["meta"]["titre"], "genre": self.libelle("filiation", g)})
        nv = m.get("version_plus_recente", "aucune")
        if nv not in ("", "aucune"):
            lignee["plus_recente"] = {"id": nv, "titre": next(x["meta"]["titre"] for x in tous if x["id"] == nv)}

        historique = historique_git(dossier)
        p["historique"] = historique

        donnees = {
            "id": pid, "titre": m["titre"], "etapes": etapes, "installation": installation,
            "fichiers": fichiers,
            "commande_dupliquer": "python outils/nouveau.py mon-projet --depuis %s" % pid,
        }

        # --- HTML du projet
        onglets = [("fiche", "Fiche")]
        if etapes:
            onglets.append(("fonctionnement", "Fonctionnement"))
        if installation:
            onglets.append(("installer", "Installer"))
        onglets.append(("fichiers", "Fichiers et versions"))
        boutons = "".join(
            '<button type="button" role="tab" id="onglet-%s" aria-controls="panneau-%s" aria-selected="%s" tabindex="%s" data-onglet="%s">%s</button>'
            % (cle, cle, "true" if i == 0 else "false", "0" if i == 0 else "-1", cle, echapper(libelle))
            for i, (cle, libelle) in enumerate(onglets)
        )

        controles = "".join(
            '<li><svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 10.5l4 4 8-9"/></svg>'
            '<span>%s</span></li>' % echapper(self.libelle("controles", c))
            for c in m["controles"]
        )

        def facette(titre, contenu_html):
            return '<div class="facette"><span class="etiquette-mono">%s</span>%s</div>' % (echapper(titre), contenu_html)

        ia_libelles = [self.libelle("ia", k) for k in m["ia_compatibles"]]
        etiquettes = "".join(
            '<a class="etiquette" href="../catalogue.html#tag=%s">%s</a>' % (echapper(t), echapper(t)) for t in m.get("etiquettes", [])
        )
        filiation_html = '<span>%s</span>' % echapper(lignee["genre_libelle"])
        if lignee["parents"]:
            filiation_html = "<span>%s</span>%s" % (
                echapper(lignee["genre_libelle"]),
                "".join('<a href="%s.html">%s</a>' % (x["id"], echapper(x["titre"])) for x in lignee["parents"]),
            )
        lignee_extra = ""
        if lignee["adaptations"]:
            lignee_extra += facette("Adaptations", "".join('<a href="%s.html">%s</a>' % (x["id"], echapper(x["titre"])) for x in lignee["adaptations"]))
        if lignee["plus_recente"]:
            lignee_extra += facette("Version plus récente", '<a href="%s.html">%s</a>' % (lignee["plus_recente"]["id"], echapper(lignee["plus_recente"]["titre"])))

        aside = "".join([
            facette("Type", "<span>%s</span>" % echapper(self.libelle("type", m["type"]))),
            facette("Usage", "<span>%s</span>" % echapper(self.libelle("usage", m["usage"]))),
            facette("Compatible avec", '<div class="puces">%s</div>' % "".join('<span class="puce">%s</span>' % echapper(x) for x in ia_libelles)),
            facette("Niveau", "<span>%s</span>" % echapper(self.libelle("niveau", m["niveau"]))),
            facette("Langue", "<span>%s</span>" % echapper(self.libelle("langue", m["langue"]))),
            facette("Données", "<span>%s</span>" % echapper(self.libelle("donnees", m["donnees"]))),
            facette("Filiation", filiation_html),
            lignee_extra,
            facette("Étiquettes", '<div class="puces">%s</div>' % etiquettes) if etiquettes else "",
            facette("Licence", "<span>%s</span>" % echapper(m["licence"])),
            facette("Auteur", "<span>%s</span>" % echapper(m["auteur"])),
            facette("Relu par", "<span>%s</span>" % echapper(m["relu_par"])),
            facette("Validation", "<span>%s</span>" % echapper(m["validation_ia"])) if m.get("validation_ia") else "",
        ])

        histo = "".join(
            '<li><span class="mono accent">%s</span><span>%s</span><span class="mono doux">%s · %s</span></li>'
            % (echapper(h["hash"]), echapper(h["message"]), echapper(h["auteur"]), echapper(h["date"]))
            for h in historique
        ) or '<li><span class="doux">L\'historique apparaît une fois le projet enregistré dans Git (git commit).</span></li>'

        contenu = """
<div class="row topbar"><a class="menu-back" href="../catalogue.html">← Catalogue</a></div>
<div class="entete-projet f-head" style="--tc: var(--t-%(type_cle)s)">
  <div class="meta-ligne">
    <span class="pill type">%(type)s</span>
    <span class="statut statut-%(statut_cle)s">%(statut)s</span>
    <span class="pill plain">v%(version)s</span>
  </div>
  <h1>%(titre)s</h1>
  <span class="tricolore" role="img" aria-label="Drapeau français"></span>
  <p class="chapeau">%(resume)s</p>
</div>
<div class="barre-onglets" role="tablist" aria-label="Sections du projet">%(boutons)s</div>
<div class="corps-projet">
  <div class="principal-projet">
    <section class="panneau actif" id="panneau-fiche" role="tabpanel" aria-labelledby="onglet-fiche">
      <div class="doc">%(readme)s</div>
      <section class="encadre">
        <h2>Contrôles avant publication</h2>
        <ul class="controles">%(controles)s</ul>
      </section>
    </section>
    <section class="panneau" id="panneau-fonctionnement" role="tabpanel" aria-labelledby="onglet-fonctionnement" hidden>
      <h2>Comment ça fonctionne</h2>
      <p class="doux">Cliquez sur une étape pour voir ce qui entre, ce qui sort, et un exemple fictif.</p>
      <div id="schema"></div>
    </section>
    <section class="panneau" id="panneau-installer" role="tabpanel" aria-labelledby="onglet-installer" hidden>
      <h2>Installer avec votre IA</h2>
      %(telecharger)s
      <div id="installation"></div>
    </section>
    <section class="panneau" id="panneau-fichiers" role="tabpanel" aria-labelledby="onglet-fichiers" hidden>
      <h2>Fichiers du projet</h2>
      %(telecharger)s
      <div id="fichiers"></div>
      <h2>Historique des versions</h2>
      <ul class="historique">%(histo)s</ul>
      <h2>Adapter ce projet</h2>
      <p>Pour créer votre propre version, qui garde un lien vers l'original, lancez cette commande à la racine du dépôt :</p>
      <div class="commande"><code id="commande-dupliquer"></code><button type="button" class="bouton secondaire" id="copier-commande">Copier</button></div>
    </section>
  </div>
  <aside class="lateral-projet" aria-label="Informations sur le projet"><h2 class="titre-lateral">Fiche technique</h2>%(aside)s</aside>
</div>
""" % {
            "type": echapper(self.libelle("type", m["type"])), "type_cle": echapper(m["type"]), "statut_cle": echapper(m["statut"]),
            "statut": echapper(self.libelle("statut", m["statut"])), "version": echapper(m["version"]),
            "titre": echapper(m["titre"]), "resume": echapper(m["resume"]), "boutons": boutons,
            "readme": rendre(p["corps"]), "controles": controles, "histo": histo, "aside": aside, "telecharger": telecharger,
        }
        self.page(SITE / "projets" / ("%s.html" % pid), "%s — %s" % (m["titre"], self.site["nom"]), contenu, "../", "catalogue",
                  donnees=donnees, scripts=("projet.js",), classe="page-projet")

    # -- catalogue et pages ---------------------------------------------------
    def construire_catalogue(self, projets):
        s = self.site
        donnees = {
            "vocab": {k: self.vocab[k] for k in ("type", "usage", "ia", "niveau", "statut")},
            "ordre_statut": ORDRE_STATUT,
            "projets": [self.resume_catalogue(p) for p in projets],
        }
        contenu = """
<div class="row topbar"><a class="menu-back" href="index.html"><span aria-hidden="true">☰</span> Retour au menu</a></div>
<h1 class="titre-page">Catalogue</h1>
<p class="muted intro-catalogue">%s</p>
<div class="search">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>
  <label for="recherche" class="sr-only">Rechercher une solution</label>
  <input id="recherche" type="search" placeholder="Chercher une solution, un usage, une IA…" autocomplete="off">
</div>
<div class="chips" id="puces-type" role="group" aria-label="Type de solution"></div>
<div class="row ligne-filtres"><div class="row" id="selecteurs"></div><span id="compteur" class="count"></span></div>
<div class="row" id="puces-actives-ligne" hidden><span id="puces-actives" class="row"></span><button type="button" class="link" id="reinitialiser">Effacer les filtres</button></div>
<section class="resultats" aria-live="polite">
  <div id="cartes" class="stack"></div>
  <div id="vide" class="empty card" hidden><b>Aucune solution ne correspond.</b><span class="muted">Retirez un filtre ou élargissez la recherche.</span></div>
</section>
""" % echapper(s["introduction"])
        self.page(SITE / "catalogue.html", "Catalogue — %s" % s["nom"], contenu, "", "catalogue", donnees=donnees,
                  scripts=("catalogue.js",), classe="page-catalogue")

    def a_la_une(self, projets):
        """Le projet ajouté le plus récemment (date du premier enregistrement Git). Sans Git : le premier recommandé."""
        dates = [(p["historique"][-1]["date"], p) for p in projets if p.get("historique")]
        if dates:
            date, p = max(dates, key=lambda x: x[0])
            return "Dernier ajout · %s" % self.date_lisible(date), p
        for p in projets:
            if p["meta"]["statut"] == "recommande":
                return "À la une · recommandé", p
        return ("À la une", projets[0]) if projets else (None, None)

    @staticmethod
    def date_lisible(iso):
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        try:
            a, m, j = (int(x) for x in iso.split("-"))
            return "%d %s %d" % (j, mois[m - 1], a)
        except (ValueError, IndexError):
            return iso

    def construire_accueil(self, projets):
        s = self.site
        n = len(projets)
        tuiles = ['<a class="tile" href="catalogue.html" style="--tc: var(--bleu)"><span class="ic">%s</span><span class="n">%d</span>'
                  '<span><b>Catalogue</b><small>Toutes les solutions</small></span></a>' % (icone("catalogue"), n)]
        for t in self.vocab["type"]:
            nb = sum(1 for p in projets if p["meta"]["type"] == t)
            titre, aide = DESCRIPTIONS_TYPES.get(t, (self.libelle("type", t), ""))
            tuiles.append('<a class="tile" href="catalogue.html#type=%s" style="--tc: var(--t-%s)"><span class="ic">%s</span><span class="n">%d</span>'
                          '<span><b>%s</b><small>%s</small></span></a>' % (t, t, icone(t), nb, echapper(titre), echapper(aide)))
        for _, slug, titre in self.pages_docs:
            tuiles.append('<a class="tile" href="pages/%s.html" style="--tc: var(--t-doc)"><span class="ic">%s</span>'
                          '<span><b>%s</b><small>%s</small></span></a>'
                          % (slug, icone(slug), echapper(titre), echapper(DESCRIPTIONS_PAGES.get(slug, ""))))
        video = ""
        if self.video_presente():
            video = ('<button type="button" class="tile wide" id="ouvrir-tuto" style="--tc: var(--vert)"><span class="ic">%s</span>'
                     '<span><b>La bibliothèque en vidéo</b><small>Une minute pour comprendre, avec sous-titres</small></span></button>'
                     % icone("video")) + self.bloc_video()
        etiquette, une = self.a_la_une(projets)
        bloc_une = ""
        if une:
            bloc_une = ('<a class="home-now" href="projets/%s.html"><span class="dot" aria-hidden="true"></span>'
                        '<span><span class="k">%s</span><b>%s</b></span></a>'
                        % (une["id"], echapper(etiquette), echapper(une["meta"]["titre"])))
        contenu = """
<section class="home-hero">
  <h1>%(nom)s <span>%(sous)s</span></h1>
  <span class="tricolore" role="img" aria-label="Drapeau français"></span>
  <p>%(accroche)s</p>
</section>
<div class="choix">
  <a class="gros" href="catalogue.html" style="--gc: var(--bleu)"><span class="gi">%(i_cat)s</span><b>Consulter</b><small>%(n)d solution%(pl)s, sans compte</small></a>
  <a class="gros" href="pages/proposer.html" style="--gc: var(--vert)"><span class="gi">%(i_dep)s</span><b>Déposer</b><small>Proposer mon projet, sans compte</small></a>
</div>
%(une)s
<div class="home-grid">%(tuiles)s</div>
%(video)s
""" % {"nom": echapper(s["nom"]), "sous": echapper(s["sous_nom"].capitalize()), "accroche": echapper(s["accroche"]),
           "i_cat": icone("catalogue"), "i_dep": icone("deposer"), "n": n, "pl": "s" if n > 1 else "",
           "une": bloc_une, "tuiles": "".join(tuiles), "video": video}
        garde = """<script>try{if(sessionStorage.getItem('bib-garde')!=='1'){document.documentElement.classList.add('avec-garde');sessionStorage.setItem('bib-garde','1');}}catch(e){}</script>
<div id="garde" role="dialog" aria-modal="true" aria-label="Page de garde">
  <svg class="circ" viewBox="0 0 600 260" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M0 40h160l26 26h170l26-26h218"/><path d="M0 120h110l26-26h200l26 26h238"/><path d="M60 200h150l26 26h190l26-26h148"/><path d="M240 66v-40M380 94v60M470 40v-30M520 120v80M300 226v30"/><g fill="currentColor" stroke="none"><circle cx="160" cy="40" r="4"/><circle cx="356" cy="66" r="4"/><circle cx="136" cy="94" r="4"/><circle cx="362" cy="120" r="4"/><circle cx="470" cy="10" r="4"/><circle cx="520" cy="200" r="4"/><circle cx="240" cy="26" r="4"/><circle cx="210" cy="200" r="4"/><circle cx="426" cy="226" r="4"/></g></svg>
  <div class="cv-body">
    <img class="cv-ins" src="assets/insigne.png" alt="Insigne de l'École de Guerre – Terre" width="84" height="101">
    <div class="cv-org">%(signature)s</div>
    <h1 class="cv-title">%(nom1)s <span>%(nom2)s %(sous)s</span></h1>
    <span class="tricolore" role="img" aria-label="Drapeau français"></span>
    <p class="cv-sub">%(accroche)s</p>
    <div class="cv-choix">
      <a class="cv-go" href="catalogue.html">Consulter<small>Trouver une solution</small></a>
      <a class="cv-alt" href="pages/proposer.html">Déposer<small>Proposer mon projet</small></a>
    </div>
    <a class="cv-entrer" href="index.html" data-garde="accueil">Voir l'accueil de la bibliothèque →</a>
  </div>
</div>""" % {"signature": echapper(s.get("signature", "Solutions IA partagées").upper()), "nom1": echapper(" ".join(s["nom"].split()[:-1]) or s["nom"]),
             "nom2": echapper(s["nom"].split()[-1] if len(s["nom"].split()) > 1 else ""),
             "sous": echapper(s["sous_nom"].capitalize()), "accroche": echapper(s["accroche"])}
        scripts = ("video.js",) if self.video_presente() else ()
        self.page(SITE / "index.html", "%s %s" % (s["nom"], s["sous_nom"].capitalize()), contenu, "", "accueil",
                  scripts=scripts, classe="page-accueil is-home", garde=garde)

    def video_presente(self):
        """Le bouton n'apparaît que si interface/video/tuto.mp4 existe."""
        return (INTERFACE / "video" / "tuto.mp4").is_file()

    def bloc_video(self):
        if not self.video_presente():
            return ""
        piste = ""
        if (INTERFACE / "video" / "tuto.vtt").is_file():
            piste = '<track kind="subtitles" srclang="fr" label="Français" src="assets/video/tuto.vtt" default>'
        return """  <dialog class="fenetre-tuto" id="fenetre-tuto" aria-labelledby="titre-tuto">
    <div class="fenetre-tete"><h2 id="titre-tuto">La bibliothèque en vidéo</h2><button type="button" class="bouton secondaire fermer-tuto">Fermer</button></div>
    <video controls preload="none" playsinline src="assets/video/tuto.mp4">%s</video>
    <p class="fenetre-note">Sans son : les explications s'affichent en sous-titres. Le détail écrit reste dans <a href="pages/debuter.html">Débuter</a>.</p>
  </dialog>
""" % piste

    def construire_docs(self):
        liens = {f: "%s.html" % slug for f, slug, _ in self.pages_docs}
        for fichier, slug, titre in self.pages_docs:
            corps = rendre((RACINE / fichier).read_text(encoding="utf-8"))
            for f, cible in liens.items():
                corps = corps.replace('href="%s"' % f, 'href="%s"' % cible)
            contenu = '<article class="doc doc-page">%s</article>' % corps
            self.page(SITE / "pages" / ("%s.html" % slug), "%s — %s" % (titre, self.site["nom"]), contenu, "../", slug, classe="page-doc")

    def construire_proposer(self):
        intro = (
            "Vous avez un prompt, un skill, un script ou un projet qui sert ? Partagez-le en remplissant ce formulaire. "
            "Pas de compte, pas d'installation : glissez votre fichier ou collez votre texte, rien ne part avant que vous cliquiez sur « Envoyer ». "
            "Utilisez uniquement des exemples fictifs."
        )
        contenu = (
            '<article class="doc doc-page page-formulaire"><h1>Proposer un projet</h1><p class="chapeau">%s</p>'
            '<p class="avis-regle"><strong>Avant de commencer :</strong> aucune donnée réelle, aucun nom, aucune adresse. '
            'Si une mention de protection, un nom de personne, une adresse de messagerie, un numéro de téléphone ou une clé se glisse dans votre texte, '
            'il sera retiré automatiquement avant l\'envoi : votre dépôt ne sera pas refusé. Les <a href="regles.html">règles de publication</a> expliquent pourquoi.</p>'
            '<noscript><p class="avis-js">Ce formulaire demande JavaScript.</p></noscript>'
            '<div id="formulaire"></div></article>'
        ) % echapper(intro)
        donnees = {
            "vocab": dict({k: self.vocab[k] for k in ("type", "usage", "ia", "langue", "niveau")},
                          # Le formulaire reste réservé aux exemples fictifs : seuls les quatre engagements d'origine y figurent.
                          controles={k: self.vocab["controles"][k] for k in
                                     ("aucune-donnee-reelle", "exemples-fictifs", "aucun-nom-adresse", "aucun-appel-reseau")}),
            "contact": self.site.get("contact_propositions", "Envoyez ce fichier à la personne qui gère la bibliothèque."),
            # Adresse de la boîte de dépôt (script Google). Vide : le formulaire propose seulement le téléchargement.
            "boite": self.site.get("boite_depot", ""),
        }
        self.page(SITE / "pages" / "proposer.html", "Proposer un projet — %s" % self.site["nom"], contenu, "../", "proposer",
                  donnees=donnees, scripts=("epurer.js", "proposer.js"), classe="page-doc")

    def lancer(self):
        projets = self.lire_tous()
        if SITE.exists():
            shutil.rmtree(str(SITE))
        SITE.mkdir(parents=True)
        (SITE / "assets").mkdir()
        for nom in ("style.css", "catalogue.js", "projet.js", "proposer.js", "epurer.js", "coque.js", "insigne.png"):
            shutil.copy(str(INTERFACE / nom), str(SITE / "assets" / nom))
        for dossier in ("polices", "video"):
            if (INTERFACE / dossier).is_dir():
                shutil.copytree(str(INTERFACE / dossier), str(SITE / "assets" / dossier))
        if (INTERFACE / "video.js").is_file():
            shutil.copy(str(INTERFACE / "video.js"), str(SITE / "assets" / "video.js"))
        projets.sort(key=lambda p: (ORDRE_STATUT.get(p["meta"]["statut"], 9), p["meta"]["titre"].lower()))
        for p in projets:
            self.construire_projet(p, projets)
        self.construire_catalogue(projets)
        self.construire_accueil(projets)
        self.construire_docs()
        self.construire_proposer()
        print("Site généré : %d projet(s), %d page(s) de documentation." % (len(projets), len(self.pages_docs)))
        print("Ouvrez site/index.html dans votre navigateur (double-clic).")


if __name__ == "__main__":
    console_utf8()
    Constructeur().lancer()
