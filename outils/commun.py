# -*- coding: utf-8 -*-
"""Fonctions communes aux outils de la bibliothèque.

Python 3.8 ou plus récent suffit. Aucune installation de paquet n'est nécessaire,
ce qui permet de travailler sur un poste sans accès au réseau.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PROJETS = RACINE / "projets"
MODELES = RACINE / "modele"
INTERFACE = RACINE / "interface"

EXTENSIONS_AUTORISEES = {".md", ".txt", ".py", ".json", ".csv", ".yaml", ".yml"}
TAILLE_MAX_FICHIER = 200_000  # octets

# Pièces jointes (documents Office et PDF) : uniquement dans projets/<id>/pieces-jointes/, jamais lues comme du texte.
DOSSIER_PJ = "pieces-jointes"
EXTENSIONS_PJ = {".docx", ".xlsx", ".pptx", ".pdf"}


def est_piece_jointe(rel):
    """Vrai pour un chemin relatif (Path) rangé dans le dossier des pièces jointes."""
    return len(rel.parts) > 1 and rel.parts[0] == DOSSIER_PJ

SECTIONS_OBLIGATOIRES = ["Le problème résolu", "Entrées et sorties", "Limites connues"]

CHAMPS_OBLIGATOIRES = [
    "titre", "resume", "type", "usage", "ia_compatibles", "langue", "niveau",
    "statut", "version", "donnees", "filiation", "licence", "controles",
    "auteur", "relu_par",
]
CHAMPS_FACULTATIFS = ["version_plus_recente", "etiquettes", "validation_ia"]


class ErreurFiche(Exception):
    """Problème de lecture ou de contenu d'une fiche."""


def console_utf8():
    """Évite les erreurs d'affichage des accents sur une console Windows."""
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def charger_json(nom):
    return json.loads((RACINE / nom).read_text(encoding="utf-8"))


def charger_vocabulaires():
    return charger_json("vocabulaires.json")


# --------------------------------------------------------------------------
# En-tête de fiche (sous-ensemble simple de YAML)
# --------------------------------------------------------------------------

def decouper_front_matter(texte):
    """Retourne (lignes_de_l_en_tete, corps). Lève ErreurFiche si l'en-tête est absent."""
    texte = texte.lstrip("﻿").replace("\r\n", "\n")
    lignes = texte.split("\n")
    if not lignes or lignes[0].strip() != "---":
        raise ErreurFiche("L'en-tête est absent : le fichier doit commencer par une ligne ---")
    for i in range(1, len(lignes)):
        if lignes[i].strip() == "---":
            return lignes[1:i], "\n".join(lignes[i + 1:]).lstrip("\n")
    raise ErreurFiche("L'en-tête n'est pas refermé : il manque la seconde ligne ---")


def _sans_commentaire(valeur):
    sortie = []
    entre_guillemets = False
    for i, c in enumerate(valeur):
        if c == '"':
            entre_guillemets = not entre_guillemets
        elif c == "#" and not entre_guillemets and (i == 0 or valeur[i - 1] in " \t"):
            break
        sortie.append(c)
    return "".join(sortie).rstrip()


def _scalaire(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"')
    return v


def _separer_liste(s):
    elements, courant, entre_guillemets = [], [], False
    for c in s:
        if c == '"':
            entre_guillemets = not entre_guillemets
            courant.append(c)
        elif c == "," and not entre_guillemets:
            elements.append("".join(courant))
            courant = []
        else:
            courant.append(c)
    elements.append("".join(courant))
    return [e for e in elements if e.strip() != ""]


def analyser_front_matter(lignes):
    meta = {}
    for numero, ligne in enumerate(lignes, start=2):
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+)\s*:\s*(.*)$", ligne)
        if not m:
            raise ErreurFiche("En-tête, ligne %d illisible : « %s »" % (numero, ligne.strip()))
        cle, brut = m.group(1), _sans_commentaire(m.group(2)).strip()
        if cle in meta:
            raise ErreurFiche("En-tête, ligne %d : le champ « %s » est présent deux fois" % (numero, cle))
        if brut.startswith("[") and brut.endswith("]"):
            meta[cle] = [_scalaire(x) for x in _separer_liste(brut[1:-1])]
        else:
            meta[cle] = _scalaire(brut)
    return meta


def remplacer_champ(texte, cle, valeur_brute):
    """Remplace (ou ajoute à la fin de l'en-tête) un champ, en conservant le reste du texte."""
    texte = texte.replace("\r\n", "\n")
    lignes = texte.split("\n")
    fin = None
    for i in range(1, len(lignes)):
        if lignes[i].strip() == "---":
            fin = i
            break
    if fin is None:
        raise ErreurFiche("En-tête non refermé")
    motif = re.compile(r"^%s\s*:" % re.escape(cle))
    for i in range(1, fin):
        if motif.match(lignes[i]):
            lignes[i] = "%s: %s" % (cle, valeur_brute)
            return "\n".join(lignes)
    lignes.insert(fin, "%s: %s" % (cle, valeur_brute))
    return "\n".join(lignes)


# --------------------------------------------------------------------------
# Projets
# --------------------------------------------------------------------------

def liste_dossiers_projets():
    if not PROJETS.exists():
        return []
    return sorted(p for p in PROJETS.iterdir() if p.is_dir() and not p.name.startswith("."))


def lire_projet(dossier):
    readme = dossier / "README.md"
    if not readme.exists():
        raise ErreurFiche("README.md est absent du dossier du projet")
    texte = readme.read_text(encoding="utf-8")
    lignes, corps = decouper_front_matter(texte)
    meta = analyser_front_matter(lignes)
    return {"id": dossier.name, "dossier": dossier, "meta": meta, "corps": corps, "texte": texte}


def fichiers_projet(dossier):
    """Chemins relatifs (README.md en premier, puis ordre alphabétique)."""
    chemins = []
    for p in dossier.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(dossier)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        chemins.append(rel)
    chemins.sort(key=lambda r: (r.as_posix() != "README.md", r.as_posix().lower()))
    return chemins


def historique_git(dossier):
    """Dernières modifications d'un dossier, d'après Git. Liste vide si Git est indisponible."""
    try:
        r = subprocess.run(
            ["git", "log", "--format=%h%x1f%an%x1f%ad%x1f%s", "--date=short", "--",
             dossier.relative_to(RACINE).as_posix()],
            cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    historique = []
    for ligne in r.stdout.splitlines():
        parties = ligne.split("\x1f")
        if len(parties) == 4:
            historique.append({"hash": parties[0], "auteur": parties[1], "date": parties[2], "message": parties[3]})
    return historique


def analyser_filiation(valeur):
    """'original' ou 'adaptation:id1,id2'. Retourne (genre, [ids])."""
    valeur = (valeur or "").strip()
    if ":" not in valeur:
        return valeur, []
    genre, _, ids = valeur.partition(":")
    return genre.strip(), [i.strip() for i in ids.split(",") if i.strip()]


# --------------------------------------------------------------------------
# fonctionnement.md et installation.md
# --------------------------------------------------------------------------

def _decouper_sections(texte):
    """Découpe sur les titres de niveau 2. Retourne [(titre, [lignes])]."""
    sections, courant = [], None
    dans_bloc = False
    for ligne in texte.replace("\r\n", "\n").split("\n"):
        if re.match(r"^(```|~~~)", ligne):
            dans_bloc = not dans_bloc
        m = re.match(r"^##\s+(.*?)\s*$", ligne) if not dans_bloc else None
        if m and not ligne.startswith("###"):
            courant = (m.group(1), [])
            sections.append(courant)
        elif courant is not None:
            courant[1].append(ligne)
    return sections


def analyser_fonctionnement(texte):
    """Étapes du schéma. Chaque étape : titre, qui (vous|ia), entree, sortie, texte, exemple."""
    etapes = []
    for titre, lignes in _decouper_sections(texte):
        etape = {"titre": re.sub(r"^\d+[.)]\s*", "", titre), "qui": "", "entree": "", "sortie": "",
                 "texte": "", "exemple": ""}
        description, bloc, dans_bloc = [], [], False
        for ligne in lignes:
            if re.match(r"^(```|~~~)", ligne):
                if not dans_bloc:
                    dans_bloc = True
                    bloc = []
                else:
                    dans_bloc = False
                    if not etape["exemple"]:
                        etape["exemple"] = "\n".join(bloc)
                continue
            if dans_bloc:
                bloc.append(ligne)
                continue
            m = re.match(r"^-\s*(qui|entr[ée]e|sortie)\s*:\s*(.*)$", ligne, re.IGNORECASE)
            if m:
                cle = m.group(1).lower().replace("é", "e")
                etape[{"qui": "qui", "entree": "entree", "sortie": "sortie"}[cle]] = m.group(2).strip()
            elif ligne.strip():
                description.append(ligne.strip())
        etape["texte"] = " ".join(description)
        etape["qui"] = etape["qui"].lower()
        etapes.append(etape)
    return etapes


def analyser_installation(texte, vocab_ia):
    """Retourne (texte_commun, {id_ia: texte}). Les sections portent le nom d'une IA ou « Étapes communes »."""
    libelles = {v.lower(): k for k, v in vocab_ia.items()}
    commun, par_ia = "", {}
    for titre, lignes in _decouper_sections(texte):
        corps = "\n".join(lignes).strip()
        cle = titre.strip().lower()
        if cle in ("étapes communes", "etapes communes", "commun"):
            commun = corps
        elif cle in libelles:
            par_ia[libelles[cle]] = corps
        else:
            raise ErreurFiche("installation.md : section « %s » inconnue (attendu : « Étapes communes » ou un nom d'IA : %s)"
                              % (titre, ", ".join(v for k, v in vocab_ia.items() if k != "toutes")))
    return commun, par_ia
