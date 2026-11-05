# -*- coding: utf-8 -*-
"""Analyse des pièces jointes d'un dépôt de la Bibliothèque IA Terre.

Module commun au skill « valider-depot » et au robot de la bibliothèque : le même code, donc les mêmes
règles, tourne chez le validateur puis à la fusion. Il ne fait AUCUN accès réseau, n'exécute aucun
fichier analysé et n'utilise que la bibliothèque standard de Python.

Types acceptés : .docx, .xlsx, .pptx, .pdf. Tout le reste est refusé (anciens formats .doc/.xls/.ppt,
fichiers à macros, archives, exécutables, fichiers chiffrés).

Pour chaque fichier, l'analyse :
  - vérifie que le type réel correspond à l'extension ;
  - refuse les macros, objets incorporés, ActiveX, liens externes dangereux, JavaScript PDF, lancements
    de programmes, fichiers chiffrés, archives piégées (« bombes ») et structures illisibles ;
  - anonymise les métadonnées de personnes (auteur, dernier enregistrement, auteurs de commentaires et de
    révisions, chemins d'ordinateur) en conservant le reste (titre, dates, sujet…) ;
  - signale au validateur, SANS rien modifier, les noms, adresses, numéros, consignes suspectes et
    éléments masqués trouvés dans le contenu du document ;
  - refuse un document qui contient une mention de protection ou une clé / un mot de passe.
Le contenu d'un document n'est jamais modifié : la mise en forme est ce qui compte.
"""
import hashlib
import html
import io
import re
import unicodedata
import zipfile
import zlib
import base64
import binascii

MAX_TOTAL = 15 * 1024 * 1024          # 15 Mo de pièces jointes par dépôt
MAX_FICHIERS = 10
MAX_DEZIP_TOTAL = 300 * 1024 * 1024   # taille totale décompressée d'un fichier Office
MAX_PARTIE_XML = 60 * 1024 * 1024
RATIO_MAX = 100                        # rapport de compression suspect (au-delà de 10 Mo décompressés)
MAX_FLUX_PDF = 64 * 1024 * 1024
MAX_FLUX_PDF_TOTAL = 256 * 1024 * 1024

EXT_ACCEPTEES = {".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx", ".pdf": "pdf"}
EXT_ANCIENNES = {".doc": "Word", ".xls": "Excel", ".ppt": "PowerPoint", ".dot": "Word", ".xlt": "Excel", ".pps": "PowerPoint"}
EXT_MACROS = {".docm", ".xlsm", ".pptm", ".dotm", ".xltm", ".potm", ".ppsm", ".xlam", ".ppam", ".sldm"}
NOMS_TYPE = {"docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint", "pdf": "PDF"}

GENERIQUES = {"", "[personne]", "xx", "claude", "python-docx", "python-pptx", "openpyxl", "unknown", "anonymous",
              "anonyme", "author", "auteur", "user", "utilisateur", "microsoft office user", "office user",
              "admin", "administrateur", "administrator", "reportlab"}
PERSONNE = "[personne]"

# -- fichiers que l'on ne veut pas voir dans un paquet Office --------------------------------------------------
PARTIE_EXECUTABLE = re.compile(r"\.(exe|dll|bat|cmd|ps1|vbs|vbe|js|jse|jar|scr|com|msi|lnk|hta|wsf|sh|py|pif|cpl|reg)$", re.I)
PARTIE_ARCHIVE = re.compile(r"\.(zip|rar|7z|gz|tgz|tar|cab|iso)$", re.I)
SCHEMAS_SUR = ("http", "https", "mailto")

CHAMP_DANGEREUX = re.compile(r"(?<![A-Za-z])(DDEAUTO|DDE|LINK|INCLUDETEXT|INCLUDEPICTURE|MACROBUTTON|DATABASE|IMPORT)(?![A-Za-z])")
FORMULE_DDE = re.compile(r"[A-Za-z_]+\|['\"]?[^<]*!")
FORMULE_XLM = re.compile(r"(?i)\b(WEBSERVICE|CALL|REGISTER|EXEC|FOPEN|FWRITE|URLDOWNLOADTOFILE)\s*\(")
ACTION_PPT = re.compile(r"ppaction://(?:program|macro|hlinkfile)", re.I)

ATTR_PERSONNE = re.compile(r'(?<=\s)((?:[A-Za-z0-9]+:)?(?:author|userId|displayName|userName|lastAuthor))="([^"]*)"')
ATTR_INITIALES = re.compile(r'(?<=\s)((?:[A-Za-z0-9]+:)?initials)="([^"]*)"')
ABS_PATH = re.compile(r'(<x15ac:absPath\b[^>]*?\burl=")([^"]*)(")')
ELEM_PERSONNE = {
    "docProps/core.xml": ("dc:creator", "cp:lastModifiedBy"),
    "docProps/app.xml": ("Manager",),
}
ELEM_TEXTE = {
    "docProps/core.xml": ("dc:title", "dc:subject", "cp:keywords", "dc:description", "cp:category"),
    "docProps/app.xml": ("Company",),
}

CONSIGNES = [
    (re.compile(r"(?i)ignor(?:e|ez|er)\s+(?:toutes?\s+)?(?:les\s+)?(?:instructions?|consignes?|r[èe]gles?)\s+(?:pr[ée]c[ée]dentes?|ant[ée]rieures?|ci-dessus)"),
     "consigne d'ignorer les instructions précédentes"),
    (re.compile(r"(?i)ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?)"),
     "consigne d'ignorer les instructions précédentes"),
    (re.compile(r"(?i)ne\s+(?:dis|mentionne|r[ée]v[èe]le|montre|affiche)\s+(?:jamais|pas|rien)\s+(?:[àa]\s+l['’]utilisateur|ceci|cela)"),
     "consigne de cacher quelque chose à l'utilisateur"),
    (re.compile(r"(?i)do\s+not\s+(?:tell|mention|reveal|show)\s+(?:this\s+to\s+)?the\s+user"),
     "consigne de cacher quelque chose à l'utilisateur"),
    (re.compile(r"(?i)\b(?:envoie|envoyez|transmets|transmettez|transf[èe]re|poste|exfiltre|t[ée]l[ée]verse)\w*\b.{0,80}\b(?:[àa]|vers)\s+(?:https?://|\S+@\S+)"),
     "consigne d'envoyer des données vers une adresse extérieure"),
    (re.compile(r"(?i)\b(?:send|post|upload|forward|exfiltrate)\b.{0,80}\b(?:to|at)\s+(?:https?://|\S+@\S+)"),
     "consigne d'envoyer des données vers une adresse extérieure"),
    (re.compile(r"(?i)(?:r[ée]v[èe]le|affiche|donne|reveal|show|print|output)\s+(?:ton|votre|your|the)\s+(?:prompt\s+syst[èe]me|system\s+prompt)"),
     "demande de révéler le prompt système"),
    (re.compile(r"(?i)(?:tu\s+es\s+maintenant\s+en\s+mode|you\s+are\s+now\s+(?:in\s+)?(?:DAN|developer\s+mode)|mode\s+d[ée]veloppeur\s+activ)"),
     "tentative de changer le rôle de l'IA"),
    (re.compile(r"(?i)\b(?:curl|wget)\b[^\n]{0,200}\|\s*(?:sh|bash|python)\b"),
     "commande qui télécharge puis exécute du code"),
    (re.compile(r"(?i)powershell(?:\.exe)?\s+-(?:enc|encodedcommand|e)\b"),
     "commande PowerShell encodée"),
    (re.compile(r"(?i)(?:base64\s+-d|certutil\s+-decode|frombase64string)"),
     "décodage de contenu encodé"),
    (re.compile(r"[A-Za-z0-9+/]{240,}={0,2}"),
     "long bloc encodé (base64 probable)"),
    (re.compile(r"[​-‏‪-‮⁠-⁤﻿]"),
     "caractères invisibles ou de sens de lecture"),
]


def sha256(octets):
    return hashlib.sha256(octets).hexdigest()


def _vd():
    """Épuration de texte du skill (noms, adresses, numéros, clés, marquages), chargée à la demande."""
    import valider_depot
    return valider_depot


def repere_consignes(texte, source=""):
    """Consignes suspectes dans un texte lu par une IA (skill, document). Renvoie des alertes lisibles."""
    alertes = []
    vus = set()
    for motif, libelle in CONSIGNES:
        for m in motif.finditer(texte or ""):
            if libelle in vus:
                break
            vus.add(libelle)
            ligne = (texte or "").count("\n", 0, m.start()) + 1
            extrait = re.sub(r"\s+", " ", m.group(0))[:70]
            quoi = "%s%s" % ((source + " : ") if source else "", libelle)
            alertes.append("%s (ligne %d) : « %s »" % (quoi, ligne, extrait if "bloc encodé" not in libelle and "invisibles" not in libelle else "…"))
    return alertes


# -- noms de fichiers -----------------------------------------------------------------------------------------
def nom_sur(nom):
    """Nom de fichier sûr : sans chemin, sans caractères spéciaux, sans nom de personne ni adresse ni numéro."""
    base = re.split(r"[\\/]", str(nom or ""))[-1].strip()
    propre, _ = _vd().epurer_texte(base)
    base = propre.replace("[personne]", "personne").replace("[numéro retiré]", "numero").replace("[clé retirée]", "cle")
    base = unicodedata.normalize("NFC", base)
    stem, point, ext = base.rpartition(".")
    if not point:
        stem, ext = base, ""
    stem = re.sub(r"[^\w .()\-]", "-", stem, flags=re.UNICODE)
    stem = re.sub(r"[ \-]{2,}", " ", stem).strip(" .-")
    if not stem:
        stem = "document"
    stem = stem[:80]
    return stem + ("." + ext.lower() if ext else "")


# -- petites aides ---------------------------------------------------------------------------------------------
def _lire_borne(zf, info, limite):
    with zf.open(info) as f:
        donnees = f.read(limite + 1)
    if len(donnees) > limite:
        raise ValueError("partie « %s » démesurée une fois décompressée" % info.filename)
    return donnees


def _texte_xml(donnees):
    return donnees.decode("utf-8", "surrogateescape")


def _octets_xml(texte):
    return texte.encode("utf-8", "surrogateescape")


def _generique(valeur):
    v = html.unescape(valeur).strip().lower()
    return v in GENERIQUES


def _balises_texte(xml, balise):
    """Textes des éléments <balise>…</balise> (sans interpréter le XML : aucune entité externe n'est lue)."""
    return re.findall(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (re.escape(balise), re.escape(balise)), xml, re.S)


def _extraire_texte_ooxml(zf, ext):
    morceaux = []
    for info in zf.infolist():
        n = info.filename
        if not n.lower().endswith(".xml"):
            continue
        if ext == "docx" and re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$", n):
            motif = "w:t"
        elif ext == "xlsx" and (n == "xl/sharedStrings.xml" or re.match(r"xl/worksheets/sheet\d+\.xml$", n)):
            motif = "t"
        elif ext == "pptx" and re.match(r"ppt/(slides|notesSlides)/[^/]+\.xml$", n):
            motif = "a:t"
        else:
            continue
        try:
            xml = _texte_xml(_lire_borne(zf, info, MAX_PARTIE_XML))
        except ValueError:
            continue
        if motif == "w:t":
            xml = xml.replace("</w:p>", "</w:p>\n")
        for t in _balises_texte(xml, motif):
            morceaux.append(html.unescape(re.sub(r"<[^>]+>", "", t)))
    return "\n".join(morceaux)


# -- analyse d'un paquet Office (docx, xlsx, pptx) -----------------------------------------------------------
def _analyser_ooxml(octets, ext, res):
    refus, alertes = res["refus"], res["alertes"]
    vd = _vd()
    try:
        zf = zipfile.ZipFile(io.BytesIO(octets))
    except zipfile.BadZipFile:
        refus.append("le fichier n'est pas un document %s valide (archive illisible)." % NOMS_TYPE[ext])
        return octets
    with zf:
        infos = zf.infolist()
        noms = [i.filename for i in infos]
        if len(infos) > 8000:
            refus.append("archive anormale : %d éléments." % len(infos))
            return octets
        total = 0
        for i in infos:
            n = i.filename
            if n.startswith("/") or ".." in n.replace("\\", "/").split("/") or re.match(r"^[A-Za-z]:", n):
                refus.append("élément « %s » : chemin dangereux dans l'archive." % n[:60])
            if i.flag_bits & 0x1:
                refus.append("fichier chiffré ou protégé par mot de passe : il ne peut pas être contrôlé.")
                return octets
            total += i.file_size
            if i.file_size > 10 * 1024 * 1024 and i.compress_size and i.file_size / max(i.compress_size, 1) > RATIO_MAX:
                refus.append("élément « %s » : taux de compression anormal (bombe de décompression)." % n[:60])
        if total > MAX_DEZIP_TOTAL:
            refus.append("contenu démesuré une fois décompressé (%d Mo)." % (total // (1024 * 1024)))
        if refus:
            return octets

        # type réel
        principal = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml", "pptx": "ppt/presentation.xml"}[ext]
        if "[Content_Types].xml" not in noms:
            refus.append("ce n'est pas un document Office (« [Content_Types].xml » absent).")
            return octets
        if principal not in noms:
            refus.append("le contenu réel n'est pas un document %s malgré son extension." % NOMS_TYPE[ext])
            return octets
        try:
            types = _texte_xml(_lire_borne(zf, zf.getinfo("[Content_Types].xml"), MAX_PARTIE_XML))
        except ValueError as e:
            refus.append(str(e))
            return octets
        if re.search(r"macroEnabled", types, re.I) or re.search(r"vbaProject", types, re.I):
            refus.append("le document contient des macros.")

        # parties interdites
        for n in noms:
            bas = n.lower()
            if "vbaproject" in bas or "vbadata" in bas:
                refus.append("macros VBA (« %s »)." % n[:60])
            elif "macrosheets/" in bas or "dialogsheets/" in bas:
                refus.append("feuilles de macros Excel 4 (« %s »)." % n[:60])
            elif "/embeddings/" in bas or bas.startswith(("word/embeddings", "xl/embeddings", "ppt/embeddings")):
                refus.append("objet incorporé (« %s »)." % n[:60])
            elif "activex" in bas:
                refus.append("composant ActiveX (« %s »)." % n[:60])
            elif "customui" in bas:
                refus.append("ruban personnalisé, pouvant lier des macros (« %s »)." % n[:60])
            elif "externallinks/" in bas:
                refus.append("liens vers d'autres classeurs (« %s »)." % n[:60])
            elif PARTIE_EXECUTABLE.search(bas):
                refus.append("programme caché dans le document (« %s »)." % n[:60])
            elif PARTIE_ARCHIVE.search(bas):
                refus.append("archive imbriquée dans le document (« %s »)." % n[:60])
        if any(n.startswith("customXml/") for n in noms):
            alertes.append("le document embarque des données personnalisées (customXml) : à vérifier.")

        # relations
        liens = []
        for n in noms:
            if not n.lower().endswith(".rels"):
                continue
            try:
                rel = _texte_xml(_lire_borne(zf, zf.getinfo(n), MAX_PARTIE_XML))
            except ValueError:
                continue
            for r in re.findall(r"<Relationship\b[^>]*>", rel):
                if not re.search(r'TargetMode="External"', r, re.I):
                    continue
                t = re.search(r'\bType="([^"]*)"', r)
                cible = re.search(r'\bTarget="([^"]*)"', r)
                kind = (t.group(1).rsplit("/", 1)[-1] if t else "?")
                cible = html.unescape(cible.group(1)) if cible else ""
                schema = cible.split(":", 1)[0].lower() if ":" in cible[:12] else ""
                if kind == "hyperlink" and schema in SCHEMAS_SUR:
                    liens.append(cible)
                elif kind == "hyperlink":
                    refus.append("lien dangereux (« %s »)." % cible[:60])
                else:
                    refus.append("lien externe de type « %s » (« %s »)." % (kind, cible[:60]))
        if liens:
            uniques = sorted(set(liens))
            alertes.append("%d lien(s) externe(s) à vérifier : %s%s." % (len(uniques), ", ".join(u[:60] for u in uniques[:8]), "…" if len(uniques) > 8 else ""))

        # contenus actifs dans le XML
        masques = {"vanish": 0, "feuilles": 0, "diapos": 0}
        modifs = {}
        anonymises = {"personnes": 0, "chemins": 0, "textes": 0}
        for i in infos:
            n = i.filename
            if not n.lower().endswith(".xml"):
                continue
            if not (n.startswith(("word/", "xl/", "ppt/", "docProps/"))):
                continue
            try:
                brut = _lire_borne(zf, i, MAX_PARTIE_XML)
            except ValueError as e:
                refus.append(str(e))
                continue
            if brut[:2] in (b"\xff\xfe", b"\xfe\xff"):
                alertes.append("« %s » est encodé en UTF-16 : métadonnées non contrôlées." % n)
                continue
            xml = _texte_xml(brut)
            nouveau = xml
            if ext == "docx" and n.startswith("word/"):
                for m in re.finditer(r"<w:instrText[^>]*>(.*?)</w:instrText>|<w:fldSimple\b[^>]*\bw:instr=\"([^\"]*)\"", xml, re.S):
                    champ = html.unescape(m.group(1) or m.group(2) or "")
                    d = CHAMP_DANGEREUX.search(champ)
                    if d:
                        refus.append("champ dangereux %s dans le document." % d.group(1))
                if "<w:vanish" in xml:
                    masques["vanish"] += xml.count("<w:vanish")
            if ext == "xlsx" and n.startswith("xl/"):
                for f in _balises_texte(xml, "f"):
                    formule = html.unescape(f)
                    if FORMULE_DDE.search(formule):
                        refus.append("formule d'échange dynamique (DDE) : « %s »." % formule[:50])
                    if FORMULE_XLM.search(formule):
                        refus.append("formule pouvant appeler un programme ou un service : « %s »." % formule[:50])
                if n == "xl/workbook.xml":
                    masques["feuilles"] += len(re.findall(r'<sheet\b[^>]*\bstate="(?:hidden|veryHidden)"', xml))
            if ext == "pptx" and n.startswith("ppt/"):
                if ACTION_PPT.search(xml):
                    refus.append("lien qui lance un programme ou une macro (« %s »)." % n[:50])
                if re.search(r"<p:oleObj\b|<p:control\b", xml):
                    refus.append("objet ou contrôle incorporé (« %s »)." % n[:50])
                if re.match(r"ppt/slides/[^/]+\.xml$", n) and re.search(r'<p:sld\b[^>]*\bshow="0"', xml):
                    masques["diapos"] += 1

            # anonymisation des métadonnées de personnes
            def remplacer_attr(m, valeur=PERSONNE):
                if _generique(m.group(2)):
                    return m.group(0)
                anonymises["personnes"] += 1
                return '%s="%s"' % (m.group(1), valeur)
            if n.startswith(("word/", "xl/")):
                nouveau = ATTR_PERSONNE.sub(remplacer_attr, nouveau)
                nouveau = ATTR_INITIALES.sub(lambda m: remplacer_attr(m, "XX"), nouveau)
            if n in ("ppt/commentAuthors.xml", "ppt/authors.xml"):
                nouveau = re.sub(r'(?<=\s)(name)="([^"]*)"', remplacer_attr, nouveau)
                nouveau = ATTR_INITIALES.sub(lambda m: remplacer_attr(m, "XX"), nouveau)
                nouveau = ATTR_PERSONNE.sub(remplacer_attr, nouveau)
            if re.match(r"xl/comments\d*\.xml$", n):
                def auteur(m):
                    if _generique(m.group(2)):
                        return m.group(0)
                    anonymises["personnes"] += 1
                    return m.group(1) + PERSONNE + m.group(3)
                nouveau = re.sub(r"(<author(?:\s[^>]*)?>)(.*?)(</author>)", auteur, nouveau, flags=re.S)
            if n == "xl/workbook.xml":
                def chemin(m):
                    if not m.group(2):
                        return m.group(0)
                    anonymises["chemins"] += 1
                    return m.group(1) + m.group(3)
                nouveau = ABS_PATH.sub(chemin, nouveau)
            for balise in ELEM_PERSONNE.get(n, ()):
                def p(m):
                    if _generique(m.group(2)):
                        return m.group(0)
                    anonymises["personnes"] += 1
                    return m.group(1) + PERSONNE + m.group(3)
                nouveau = re.sub(r"(<%s(?:\s[^>]*)?>)(.*?)(</%s>)" % (re.escape(balise), re.escape(balise)), p, nouveau, flags=re.S)
            for balise in ELEM_TEXTE.get(n, ()):
                def t(m):
                    brut_t = html.unescape(m.group(2))
                    propre, c = vd.epurer_texte(brut_t)
                    if propre == brut_t:
                        return m.group(0)
                    anonymises["textes"] += 1
                    return m.group(1) + html.escape(propre, quote=False) + m.group(3)
                nouveau = re.sub(r"(<%s(?:\s[^>]*)?>)(.*?)(</%s>)" % (re.escape(balise), re.escape(balise)), t, nouveau, flags=re.S)
            if n == "docProps/app.xml":
                def lien_base(m):
                    if not m.group(2).strip():
                        return m.group(0)
                    anonymises["chemins"] += 1
                    return m.group(1) + m.group(3)
                nouveau = re.sub(r"(<HyperlinkBase>)(.*?)(</HyperlinkBase>)", lien_base, nouveau, flags=re.S)
            if n == "docProps/custom.xml" and "<property" in xml:
                alertes.append("propriétés personnalisées présentes (docProps/custom.xml) : à vérifier.")
            if nouveau != xml:
                modifs[n] = _octets_xml(nouveau)

        if masques["vanish"]:
            alertes.append("texte masqué dans le document (%d passage(s)) : à lire avant publication." % masques["vanish"])
        if masques["feuilles"]:
            alertes.append("%d feuille(s) Excel masquée(s) : à vérifier." % masques["feuilles"])
        if masques["diapos"]:
            alertes.append("%d diapositive(s) masquée(s) : à vérifier." % masques["diapos"])

        # lecture du contenu : on signale, on ne modifie pas
        texte = _extraire_texte_ooxml(zf, ext)
        _controles_contenu(texte, res)

        res["anonymises"] = {k: v for k, v in anonymises.items() if v}
        if refus or not modifs:
            return octets
        sortie = io.BytesIO()
        with zipfile.ZipFile(sortie, "w") as zo:
            for i in infos:
                donnees = modifs.get(i.filename)
                if donnees is None:
                    donnees = zf.read(i)
                zi = zipfile.ZipInfo(i.filename, i.date_time)
                zi.compress_type = i.compress_type
                zi.external_attr = i.external_attr
                zi.create_system = i.create_system
                zo.writestr(zi, donnees)
        return sortie.getvalue()


def _controles_contenu(texte, res):
    """Noms, adresses, numéros, clés, marquages et consignes dans le texte d'un document (sans le modifier)."""
    vd = _vd()
    _, c = vd.epurer_texte(texte)
    if c["marquage"]:
        res["refus"].append("mention de protection (DIFFUSION RESTREINTE, CONFIDENTIEL…) dans le document : la bibliothèque est « NON PROTÉGÉ ».")
    if c["cle"]:
        res["refus"].append("clé, jeton ou mot de passe apparent dans le document (%d) : l'auteur doit le révoquer." % c["cle"])
    libelles = {"nom": "nom(s) de personne", "courriel": "adresse(s) de messagerie", "telephone": "numéro(s) de téléphone", "ip": "adresse(s) IP"}
    details = ["%d %s" % (c[k], libelles[k]) for k in ("nom", "courriel", "telephone", "ip") if c[k]]
    if details:
        res["alertes"].append("le contenu du document comprend : %s. Il n'est pas modifié : le validateur décide (accepter, ou faire corriger par l'auteur)." % ", ".join(details))
    res["alertes"] += repere_consignes(texte, "contenu du document")


# -- analyse d'un PDF -----------------------------------------------------------------------------------------
FILTRES_IMAGE = {b"DCTDecode", b"DCT", b"JPXDecode", b"CCITTFaxDecode", b"CCF", b"JBIG2Decode"}


def _decoder_flux(donnees, filtres, budget):
    """Décode un flux PDF (Flate, ASCII85, ASCIIHex, RunLength). Renvoie None si illisible, False pour une image."""
    for f in filtres:
        if f in FILTRES_IMAGE:
            return False
        if f in (b"FlateDecode", b"Fl"):
            d = zlib.decompressobj()
            try:
                donnees = d.decompress(donnees, MAX_FLUX_PDF)
            except zlib.error:
                try:
                    d = zlib.decompressobj(-15)
                    donnees = d.decompress(donnees[2:], MAX_FLUX_PDF)
                except zlib.error:
                    return None
            if d.unconsumed_tail:
                raise ValueError("flux démesuré une fois décompressé")
            budget[0] += len(donnees)
            if budget[0] > MAX_FLUX_PDF_TOTAL:
                raise ValueError("PDF démesuré une fois décompressé")
        elif f in (b"ASCII85Decode", b"A85"):
            brut = donnees.strip()
            if brut.startswith(b"<~"):
                brut = brut[2:]
            if brut.endswith(b"~>"):
                brut = brut[:-2]
            try:
                donnees = base64.a85decode(brut, adobe=False, ignorechars=b" \t\n\r\x0b\f\x00")
            except Exception:
                return None
        elif f in (b"ASCIIHexDecode", b"AHx"):
            brut = re.sub(rb"[^0-9A-Fa-f]", b"", donnees.split(b">")[0])
            if len(brut) % 2:
                brut += b"0"
            try:
                donnees = binascii.unhexlify(brut)
            except binascii.Error:
                return None
        elif f in (b"RunLengthDecode", b"RL"):
            sortie, i = bytearray(), 0
            while i < len(donnees):
                n = donnees[i]
                if n == 128:
                    break
                if n < 128:
                    sortie += donnees[i + 1:i + 2 + n]
                    i += 2 + n
                else:
                    sortie += donnees[i + 1:i + 2] * (257 - n)
                    i += 2
                if len(sortie) > MAX_FLUX_PDF:
                    raise ValueError("flux démesuré une fois décompressé")
            donnees = bytes(sortie)
        else:
            return None   # LZW, Crypt, etc. : non pris en charge
    return donnees


def _flux_pdf(octets):
    """Liste de (dictionnaire, données) pour chaque flux du PDF."""
    flux = []
    pos = 0
    while True:
        m = re.compile(rb"stream\r?\n").search(octets, pos)
        if not m:
            break
        fin = octets.find(b"endstream", m.end())
        if fin < 0:
            break
        debut_dict = octets.rfind(b"obj", 0, m.start())
        dico = octets[debut_dict if debut_dict >= 0 else max(0, m.start() - 400):m.start()]
        flux.append((dico, octets[m.end():fin], m.start(), fin + 9))
        pos = fin + 9
    return flux


def _filtres(dico):
    m = re.search(rb"/Filter\s*(\[[^\]]*\]|/[A-Za-z0-9]+)", dico)
    if not m:
        return []
    return re.findall(rb"/([A-Za-z0-9]+)", m.group(1))


def _chaine_pdf(octets, debut):
    """Fin d'une chaîne littérale (…) commençant à debut (sur la parenthèse ouvrante)."""
    profondeur, i = 0, debut
    while i < len(octets):
        c = octets[i:i + 1]
        if c == b"\\":
            i += 2
            continue
        if c == b"(":
            profondeur += 1
        elif c == b")":
            profondeur -= 1
            if profondeur == 0:
                return i
        i += 1
    return -1


def _remplacer_auteur_pdf(octets, hors_flux, res):
    """Remplace l'auteur par « [personne] » sans changer la longueur du fichier (le PDF reste valide)."""
    donnees = bytearray(octets)
    n = 0
    for m in re.finditer(rb"/Author\s*([(<])", octets):
        d = m.end() - 1
        if not any(a <= d < b for a, b in hors_flux):
            pass
        else:
            continue   # dans un flux : on ne touche pas
        if m.group(1) == b"(":
            f = _chaine_pdf(octets, d)
            if f < 0:
                continue
            interieur = octets[d + 1:f]
            if interieur.strip().lower() in (b"", b"[personne]") or interieur.decode("latin-1").strip().lower() in GENERIQUES:
                continue
            cible = PERSONNE.encode()
            nouveau = cible + b" " * (len(interieur) - len(cible)) if len(interieur) >= len(cible) else b"_" * len(interieur)
            donnees[d + 1:f] = nouveau
            n += 1
        else:
            f = octets.find(b">", d)
            if f < 0:
                continue
            hexa = re.sub(rb"\s", b"", octets[d + 1:f])
            if len(hexa) < 2:
                continue
            try:
                lu = binascii.unhexlify(hexa + (b"0" if len(hexa) % 2 else b""))
            except binascii.Error:
                continue
            txt = lu[2:].decode("utf-16-be", "ignore") if lu[:2] == b"\xfe\xff" else lu.decode("latin-1")
            if txt.strip().lower() in GENERIQUES:
                continue
            taille = f - d - 1
            if taille >= 44:
                nouveau = (b"FEFF" + PERSONNE.encode("utf-16-be").hex().upper().encode()).ljust(taille, b"0")
                nouveau = nouveau[:48] + b"0020" * ((taille - 48) // 4) + b"0" * ((taille - 48) % 4) if taille > 48 else nouveau
            else:
                nouveau = (b"5F" * (taille // 2)).ljust(taille, b"0")
            donnees[d + 1:f] = nouveau[:taille]
            n += 1
    return bytes(donnees), n


def _analyser_pdf(octets, res):
    refus, alertes = res["refus"], res["alertes"]
    if b"%PDF-" not in octets[:1024]:
        refus.append("le fichier n'est pas un PDF (en-tête absent).")
        return octets
    flux = _flux_pdf(octets)
    budget = [0]
    hors_flux = [(a, b) for (_, _, a, b) in flux]
    corpus = bytearray()
    prec = 0
    for a, b in hors_flux:
        corpus += octets[prec:a]
        prec = b
    corpus += octets[prec:]
    textes = []
    illisible = 0
    try:
        for dico, donnees, a, b in flux:
            if b"/Crypt" in dico:
                refus.append("flux chiffré : le PDF ne peut pas être contrôlé.")
                return octets
            filtres = _filtres(dico)
            if re.search(rb"/Type\s*/(?:Metadata)", dico):
                deco = _decoder_flux(donnees, filtres, budget) if filtres else donnees
                if deco:
                    corpus += b"\n" + deco
                continue
            est_obj = bool(re.search(rb"/Type\s*/ObjStm", dico))
            if re.search(rb"/Subtype\s*/Image", dico) or re.search(rb"/Type\s*/XRef", dico):
                continue
            deco = _decoder_flux(donnees, filtres, budget) if filtres else donnees
            if deco is False:
                continue
            if deco is None:
                if est_obj:
                    refus.append("structure du PDF illisible (flux d'objets non décodable) : il ne peut pas être contrôlé.")
                    return octets
                illisible += 1
                continue
            if est_obj:
                corpus += b"\n" + deco
            else:
                textes.append(deco)
                # un flux ordinaire ne contient pas de dictionnaires d'actions : s'il en contient, on les analyse
                for m in re.finditer(rb"/S\s*/(?:JavaScript|Launch|GoToR|GoToE|SubmitForm|ImportData)\b|/JS\s*[(<]|/EmbeddedFiles?\b|/XFA\b|/RichMedia\b", deco):
                    corpus += b"\n" + m.group(0)
    except ValueError as e:
        refus.append("%s (bombe de décompression possible)." % e)
        return octets
    scan = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), bytes(corpus))

    if re.search(rb"/Encrypt\b", scan):
        refus.append("PDF chiffré ou protégé par mot de passe : il ne peut pas être contrôlé.")
        return octets
    interdits = [
        (rb"/JavaScript\b", "JavaScript"), (rb"/JS(?![A-Za-z])", "JavaScript"), (rb"/Launch\b", "lancement de programme"),
        (rb"/EmbeddedFiles?\b", "fichier incorporé"), (rb"/RichMedia\b", "contenu multimédia actif"),
        (rb"/XFA\b", "formulaire XFA"), (rb"/SubmitForm\b", "envoi de formulaire"), (rb"/ImportData\b", "import de données"),
        (rb"/GoToR\b", "ouverture d'un fichier distant"), (rb"/GoToE\b", "ouverture d'un fichier incorporé"),
    ]
    vus = set()
    for motif, nom in interdits:
        if re.search(motif, scan) and nom not in vus:
            vus.add(nom)
            refus.append("le PDF contient %s." % nom)
    if re.search(rb"/AcroForm\b", scan):
        alertes.append("le PDF contient un formulaire (AcroForm) : à tester.")
    if re.search(rb"/OpenAction\b", scan):
        alertes.append("le PDF définit une action à l'ouverture : à vérifier (sans JavaScript, c'est généralement un simple zoom).")
    if re.search(rb"/(?:3D|Movie|Sound)\b", scan):
        alertes.append("le PDF contient un élément multimédia (3D, vidéo ou son).")
    uris = sorted({u.decode("latin-1")[:60] for u in re.findall(rb"/URI\s*\(([^)]*)\)", scan)})
    if uris:
        alertes.append("%d lien(s) externe(s) à vérifier : %s%s." % (len(uris), ", ".join(uris[:8]), "…" if len(uris) > 8 else ""))
    if illisible:
        alertes.append("%d flux du PDF n'ont pas pu être décodés : leur texte n'est pas analysé." % illisible)

    # contenu : texte des pages (analyse partielle) + métadonnées
    morceaux = []
    for t in textes:
        for m in re.finditer(rb"\(((?:[^()\\]|\\.){1,500})\)\s*(?:Tj|'|\")", t):
            morceaux.append(m.group(1))
        for m in re.finditer(rb"\[((?:[^\]\\]|\\.)*)\]\s*TJ", t):
            morceaux.append(b"".join(re.findall(rb"\(((?:[^()\\]|\\.)*)\)", m.group(1))))
    texte = "\n".join(re.sub(rb"\\(.)", rb"\1", x).decode("latin-1") for x in morceaux)
    meta = []
    for cle in (rb"Title", rb"Subject", rb"Keywords"):
        for m in re.finditer(rb"/" + cle + rb"\s*\(((?:[^()\\]|\\.)*)\)", octets):
            meta.append(m.group(1).decode("latin-1"))
    texte += "\n" + "\n".join(meta)
    if textes and not morceaux:
        alertes.append("le texte du PDF n'a pas pu être lu (polices ou structure particulières) : le contenu doit être relu par le validateur.")
    _controles_contenu(texte, res)

    nouveau, n = _remplacer_auteur_pdf(octets, hors_flux, res)
    auteurs_flux = 0
    for dico, donnees, a, b in flux:
        if re.search(rb"/Type\s*/Metadata", dico) and re.search(rb"<dc:creator>|<pdf:Author>", donnees):
            auteurs_flux += 1
    if auteurs_flux:
        nouveau2, n2 = _remplacer_xmp(nouveau)
        nouveau, n = nouveau2, n + n2
    if n:
        res["anonymises"] = {"personnes": n}
    return nouveau


def _remplacer_xmp(octets):
    """Remplace, à longueur constante, les auteurs des métadonnées XMP non compressées."""
    donnees = bytearray(octets)
    n = 0
    for m in re.finditer(rb"(<dc:creator>.*?</dc:creator>|<pdf:Author>.*?</pdf:Author>)", octets, re.S):
        bloc = m.group(0)
        def li(x):
            nonlocal n
            valeur = x.group(2)
            if valeur.decode("utf-8", "ignore").strip().lower() in GENERIQUES or len(valeur) == 0:
                return x.group(0)
            cible = PERSONNE.encode()
            nouveau = cible + b" " * (len(valeur) - len(cible)) if len(valeur) >= len(cible) else b"_" * len(valeur)
            n += 1
            return x.group(1) + nouveau + x.group(3)
        remplace = re.sub(rb"(<rdf:li[^>]*>)([^<]*)(</rdf:li>)", li, bloc)
        remplace = re.sub(rb"(<pdf:Author>)([^<]*)(</pdf:Author>)", li, remplace)
        if remplace != bloc and len(remplace) == len(bloc):
            donnees[m.start():m.end()] = remplace
    return bytes(donnees), n


# -- point d'entrée par fichier -------------------------------------------------------------------------------
def analyser_fichier(nom_origine, octets):
    nom = nom_sur(nom_origine)
    ext = ("." + nom.rsplit(".", 1)[-1].lower()) if "." in nom else ""
    res = {"nom_origine": str(nom_origine), "nom": nom, "extension": ext, "type": None, "taille_origine": len(octets),
           "sha256_origine": sha256(octets), "refus": [], "alertes": [], "anonymises": {}, "octets": octets}
    if nom != str(nom_origine):
        res["alertes"].append("nom de fichier modifié par précaution : « %s » devient « %s »." % (str(nom_origine)[:60], nom))
    if ext in EXT_ANCIENNES:
        res["refus"].append("ancien format %s (%s) : il ne peut pas être contrôlé. Le convertir en %s (Enregistrer sous)."
                            % (EXT_ANCIENNES[ext], ext, {"Word": ".docx", "Excel": ".xlsx", "PowerPoint": ".pptx"}[EXT_ANCIENNES[ext]]))
    elif ext in EXT_MACROS:
        res["refus"].append("format à macros (%s) : refusé. Enregistrer sans macros (%s)." % (ext, ext[:-1] + "x"))
    elif ext not in EXT_ACCEPTEES:
        res["refus"].append("type de fichier non accepté (%s). Acceptés : .docx, .xlsx, .pptx, .pdf." % (ext or "sans extension"))
    elif not octets:
        res["refus"].append("fichier vide.")
    else:
        type_ = EXT_ACCEPTEES[ext]
        res["type"] = type_
        signature_ok = octets[:4] == b"PK\x03\x04" if type_ != "pdf" else b"%PDF-" in octets[:1024]
        if not signature_ok:
            if octets[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
                res["refus"].append("le contenu réel est un ancien format Office (OLE) malgré l'extension %s." % ext)
            else:
                res["refus"].append("le contenu réel ne correspond pas à l'extension %s." % ext)
        else:
            try:
                final = _analyser_pdf(octets, res) if type_ == "pdf" else _analyser_ooxml(octets, type_, res)
            except (ValueError, RuntimeError, MemoryError) as e:
                res["refus"].append("analyse impossible : %s." % e)
                final = octets
            if not res["refus"]:
                res["octets"] = final
    res["taille"] = len(res["octets"])
    res["sha256"] = sha256(res["octets"])
    return res


def analyser_lot(fichiers, declarees=None):
    """fichiers : liste de (nom, octets). declarees : liste de {nom, taille, sha256} annoncée par le dépôt (facultatif).
    Renvoie {"refus": [...], "alertes": [...], "fichiers": [...], "taille_totale": n}."""
    lot = {"refus": [], "alertes": [], "fichiers": [], "taille_totale": 0}
    if len(fichiers) > MAX_FICHIERS:
        lot["refus"].append("trop de pièces jointes : %d (maximum %d)." % (len(fichiers), MAX_FICHIERS))
    total = sum(len(o) for _, o in fichiers)
    lot["taille_totale"] = total
    if total > MAX_TOTAL:
        lot["refus"].append("pièces jointes trop lourdes : %.1f Mo (maximum %d Mo par dépôt)." % (total / 1048576, MAX_TOTAL // 1048576))
    utilises = set()
    for nom, octets in fichiers[:MAX_FICHIERS]:
        r = analyser_fichier(nom, octets)
        base, point, ext = r["nom"].rpartition(".")
        n = 2
        while r["nom"].lower() in utilises:
            r["nom"] = "%s-%d.%s" % (base, n, ext)
            n += 1
        utilises.add(r["nom"].lower())
        lot["fichiers"].append(r)
        for x in r["refus"]:
            lot["refus"].append("« %s » : %s" % (r["nom"], x))
        for x in r["alertes"]:
            lot["alertes"].append("« %s » : %s" % (r["nom"], x))
    if declarees is not None:
        reçus = {r["sha256_origine"]: r for r in lot["fichiers"]}
        annoncees = set()
        for d in declarees:
            h = str((d or {}).get("sha256") or "").lower()
            annoncees.add(h)
            if h not in reçus:
                lot["refus"].append("pièce jointe annoncée mais non reçue ou modifiée : « %s »." % str((d or {}).get("nom"))[:60])
        for h, r in reçus.items():
            if h not in annoncees:
                lot["alertes"].append("« %s » : pièce jointe non annoncée par le dépôt." % r["nom"])
    return lot


def controles_acceptes(type_):
    base = ["type réel conforme à l'extension", "aucun objet incorporé ni composant actif", "aucun lien externe dangereux",
            "aucun mot de passe, aucune mention de protection"]
    if type_ == "pdf":
        return base + ["aucun JavaScript, aucun lancement de programme"]
    return base + ["aucune macro", "métadonnées de personnes anonymisées"]
