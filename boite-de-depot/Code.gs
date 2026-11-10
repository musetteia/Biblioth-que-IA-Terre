/**
 * Boîte de dépôt de la Bibliothèque IA Terre.
 *
 * Ce script reçoit une proposition envoyée par le formulaire du site, retire ce qui
 * ne doit pas circuler (marquages, noms de personnes, adresses électroniques, téléphones, clés),
 * l'enregistre dans un dossier Drive PRIVÉ et prévient les validateurs par courriel,
 * fichier joint. Il ne publie rien : la publication se fait après validation humaine.
 *
 * Qui peut déposer : la personne indique son adresse (personnelle ou non) dans le formulaire.
 *  - Première fois : elle indique aussi une adresse d'un domaine sécurisé (intradef.gouv.fr,
 *    academie.def.gouv.fr, domaine exact, sans sous-domaine). Le script envoie le code à 6 chiffres à cette
 *    adresse sécurisée, la personne le saisit sur le site : l'adresse indiquée est alors « enrôlée »
 *    (on ne garde que son empreinte et l'adresse sécurisée de rattachement, pour un an renouvelable).
 *  - Dépôts suivants : le code est envoyé directement à l'adresse enrôlée.
 *  - Une adresse déjà d'un domaine sécurisé reçoit le code elle-même. Les validateurs (propriété
 *    « VALIDATEURS ») et les adresses de la propriété « EXEMPTES » sont dispensés de la règle de domaine,
 *    pas du code.
 * Seulement après la saisie du code le dépôt est accepté.
 *
 * Trois demandes possibles, toutes en POST :
 *   {action:'code',     adresse, securisee?}      -> envoie un code (à l'adresse, ou à l'adresse sécurisée à la 1re fois)
 *   {action:'verifier', adresse, code}            -> renvoie un jeton à usage unique (30 min)
 *   {action:'deposer',  adresse, jeton, p, ...}   -> enregistre le dépôt (avec pièces jointes éventuelles)
 *
 * Il ne lit aucun autre fichier du compte et n'expose aucune liste de dépôts.
 */

// ===== EPURER:DEBUT (ce bloc est recopié tel quel dans interface/epurer.js) =====
var Epurer = (function () {
  var MARQUAGES = /(^|[^A-Za-zÀ-ÿ])(DIFFUSION\s+RESTREINTE|CONFIDENTIEL(?:\s+D[ÉE]FENSE)?|SECRET(?:\s+D[ÉE]FENSE)?|TR[ÈE]S\s+SECRET|NON\s+PROT[ÉE]G[ÉE]|RESTRICTED|NATO\s+(?:SECRET|CONFIDENTIAL|RESTRICTED))(?![A-Za-zÀ-ÿ])/g;
  var COURRIEL = /[\w.+-]+@([\w-]+(?:\.[\w-]+)+)/g;
  var DOMAINE_FICTIF = /(^|\.)(example\.(com|org|net)|invalid|test|example)$/;
  var TELEPHONE = /(^|[^\d.])((?:(?:\+33|0033)[ .-]?\(?0?\)?|0)[1-9](?:[ .-]?\d{2}){4})(?!\d)/g;
  var IP = /(^|[^\d])((?:\d{1,3}\.){3}\d{1,3})(?!\d)(?!\.\d)/g;
  var CLE_JETON = /\b(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})\b/g;
  var CLE_AFFECTEE = /((?:api[_-]?key|jeton|token|mot[_ ]de[_ ]passe|password)\s*[:=]\s*["']?)([A-Za-z0-9_\-]{12,})/gi;
  var CODE_RESEAU = /^\s*(?:import|from)\s+(socket|urllib|requests|http|httpx|ftplib|smtplib|telnetlib|paramiko|aiohttp|websockets?|ssl|xmlrpc)\b/m;
  var CODE_DANGER = /\b(os\.system|subprocess|eval\s*\(|exec\s*\(|__import__|pickle|ctypes)\b/;

  // Noms de personnes : « Prénom Nom », « Prénom de Nom » et « NOM Prénom » deviennent « [personne] ».
  // Un prénom seul n'est jamais retiré. La détection s'appuie sur une liste de prénoms courants :
  // un prénom rare ou étranger absent de la liste n'est pas reconnu (le validateur relit la fiche).
  var PRENOMS = {};
  [
    "adrien|alain|albert|alexandre|alexis|alfred|andre|antoine|arnaud|arthur|aurelien|axel|baptiste|",
    "benjamin|benoit|bernard|bertrand|bruno|cedric|charles|christian|christophe|clement|cyril|damien|",
    "daniel|david|denis|dominique|dylan|edouard|emile|emmanuel|eric|etienne|fabien|fabrice|felix|florent|",
    "florian|francis|franck|francois|frederic|gabriel|gaetan|gael|gerard|gilbert|gilles|guillaume|guy|",
    "gregory|henri|herve|hugo|hugues|jacques|jean|jeremy|jerome|joel|jonathan|jordan|joseph|jules|julien|",
    "justin|kevin|kilian|laurent|leo|leon|leonard|lionel|loic|louis|lucas|luc|ludovic|marc|marcel|",
    "mathieu|mathis|matthieu|maurice|maxence|maxime|mehdi|michel|mickael|nathan|nicolas|noe|olivier|",
    "pascal|patrice|patrick|paul|philippe|pierre|quentin|raphael|raymond|remi|rene|richard|robert|roger|",
    "roland|romain|samuel|sebastien|serge|simon|stephane|sylvain|theo|thibault|thierry|thomas|timothee|",
    "tristan|valentin|victor|vincent|vivien|william|xavier|yann|yannick|yves|yvan|zacharie|amine|karim|",
    "mohamed|mohammed|ahmed|ali|omar|youssef|rachid|nabil|samir|hamid|farid|kamel|abdel|bilal|ibrahim|",
    "mamadou|moussa|sofiane|anthony|jimmy|jeremie|cyrille|regis|martin|mael|ethan|enzo|evan|tom|timeo|",
    "yanis|lilian|nolan|noah|liam|gaspard|augustin|aymeric|barthelemy|bastien|brice|corentin|didier|",
    "dimitri|eliott|elie|fernand|gauthier|ghislain|gustave|hector|hippolyte|igor|isidore|lenny|lorenzo|",
    "malo|mathias|melvin|morgan|nelson|norbert|octave|oscar|pablo|rodolphe|ruben|sacha|stanislas|steeve|",
    "sullivan|tanguy|teddy|ulysse|urbain|vladimir|wilfried|yoann|zinedine|adele|agathe|agnes|aline|alice|",
    "amandine|amelie|anais|anne|annie|anouk|aurelie|aurore|beatrice|bernadette|brigitte|camille|capucine|",
    "carine|carole|caroline|catherine|cecile|cecilia|celine|chantal|charlotte|chloe|christelle|",
    "christiane|christine|claire|clara|clemence|colette|corinne|claudine|constance|delphine|denise|diane|",
    "edith|eleonore|elisa|elise|elodie|emilie|emma|estelle|eva|eve|fabienne|fanny|flora|florence|",
    "francoise|frederique|gabrielle|genevieve|ghislaine|gisele|helene|henriette|hortense|ines|irene|",
    "isabelle|jacqueline|jeanne|jessica|joelle|josephine|josette|julia|julie|juliette|justine|karine|",
    "laetitia|laure|laura|laurence|lea|leila|lena|liliane|lina|lisa|lola|louise|lucie|lucile|lydie|",
    "madeleine|magali|manon|marguerite|maria|marie|marielle|marine|marion|marthe|martine|mathilde|maud|",
    "maude|melanie|michele|michelle|mireille|monique|myriam|nadege|nadia|nadine|natacha|nathalie|nicole|",
    "noemie|odette|odile|olga|pascale|paulette|pauline|perrine|raymonde|rachel|rebecca|renee|rita|roxane|",
    "sabine|sabrina|salome|sandra|sandrine|sara|sarah|severine|sidonie|simone|solange|sonia|sophie|",
    "stephanie|suzanne|sylvie|tatiana|therese|valerie|vanessa|veronique|virginie|viviane|yolande|yvette|",
    "yvonne|zoe|maelle|maeva|lou|jade|louna|ambre|anaelle|apolline|clementine|elena|elsa|emeline|eugenie|",
    "fatima|amina|khadija|samira|yasmine|malika|leonie|margaux|melissa|oceane|ophelie|priscilla|penelope|",
    "romane|rosalie|segolene|stella|tiphaine|victorine|wendy|laurie|lilou|lise|lorene|marjorie|morgane|",
    "noa|orane|john|james|michael|peter|mark|andrew|steven|brian|jennifer|emily|linda|susan|karen|nancy|",
    "betty|helen|donna|carol|ruth|sharon|amanda|deborah|george|edward|henry|jack|harry|oliver|jacob|mike|",
    "bob|tim|sam|ben|jim|joe|steve|matt|chris|nick|dan|alex|kate|katie"
  ].join("|").split("|").forEach(function (p) { PRENOMS[p] = true; });
  var PARTICULES = { de: true, du: true, des: true, la: true, le: true, les: true, van: true, von: true, der: true, den: true, di: true, da: true, del: true, el: true, al: true, bin: true, mac: true, ter: true, ten: true };
  var MOT = /[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]*/g;

  function sansAccent(s) { return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function majuscule(m) { return /^[A-ZÀ-ÖØ-Þ]/.test(m); }
  function toutMajuscule(m) { return m.length >= 2 && m === m.toUpperCase() && m !== m.toLowerCase(); }
  function estPrenom(m) {
    if (!majuscule(m)) { return false; }
    return m.split('-').every(function (c) { return c !== '' && PRENOMS[sansAccent(c)] === true; });
  }
  function estNom(m) { return m.length >= 2 && (majuscule(m) || /^[dDlL]['’][A-ZÀ-ÖØ-Þ]/.test(m)); }

  function retirerNoms(texte, n) {
    var mots = [], m;
    MOT.lastIndex = 0;
    while ((m = MOT.exec(texte)) !== null) { mots.push({ t: m[0], d: m.index, f: m.index + m[0].length }); }
    function colles(i) { return /^[ \t]+$/.test(texte.slice(mots[i].f, mots[i + 1].d)); }
    var spans = [], i = 0, dernier = -1;
    while (i < mots.length) {
      if (!estPrenom(mots[i].t)) { i++; continue; }
      // « Prénom Nom » : un ou deux noms, avec d'éventuelles particules (de, du, van…).
      var fin = -1, noms = 0, k = i + 1;
      while (noms < 2 && k < mots.length && colles(k - 1)) {
        var p = k;
        while (p - k < 2 && p + 1 < mots.length && PARTICULES[mots[p].t] === true && colles(p)) { p++; }
        if (estNom(mots[p].t)) { noms++; fin = p; k = p + 1; } else { break; }
      }
      if (fin >= 0) { spans.push([mots[i].d, mots[fin].f]); n.nom++; dernier = fin; i = fin + 1; continue; }
      // « NOM Prénom » : un à trois mots tout en majuscules juste avant le prénom.
      var debut = i, c = 0;
      while (c < 3 && debut - 1 > dernier && colles(debut - 1) && toutMajuscule(mots[debut - 1].t) &&
             (c > 0 || mots[debut - 1].t.length >= 3)) { debut--; c++; }
      if (c > 0) { spans.push([mots[debut].d, mots[i].f]); n.nom++; }
      dernier = i; i++;
    }
    if (!spans.length) { return texte; }
    var res = '', pos = 0;
    spans.forEach(function (s) { res += texte.slice(pos, s[0]) + '[personne]'; pos = s[1]; });
    return res + texte.slice(pos);
  }

  function texte(brut) {
    var n = { marquage: 0, nom: 0, courriel: 0, telephone: 0, cle: 0, ip: 0 };
    var t = String(brut == null ? '' : brut);
    t = t.replace(MARQUAGES, function (m, avant) { n.marquage++; return avant; });
    t = retirerNoms(t, n);
    t = t.replace(COURRIEL, function (m, dom) {
      if (DOMAINE_FICTIF.test(dom.toLowerCase())) { return m; }
      n.courriel++; return 'nom@example.org';
    });
    t = t.replace(TELEPHONE, function (m, avant) { n.telephone++; return avant + '[numéro retiré]'; });
    t = t.replace(CLE_JETON, function () { n.cle++; return '[clé retirée]'; });
    t = t.replace(CLE_AFFECTEE, function (m, debut) { n.cle++; return debut + '[clé retirée]'; });
    t = t.replace(IP, function (m, avant, ip) {
      if (!ip.split('.').every(function (o) { return +o <= 255; })) { return m; }
      n.ip++; return avant + '192.0.2.1';
    });
    // Un marquage retiré ne doit pas laisser une ligne vide en tête ni des espaces doubles.
    if (n.marquage) { t = t.replace(/[ \t]{2,}/g, ' '); }
    return { texte: t, retraits: n };
  }

  function somme(a, b) { for (var k in b) { a[k] = (a[k] || 0) + b[k]; } }

  function parcourir(valeur, total) {
    if (typeof valeur === 'string') { var r = texte(valeur); somme(total, r.retraits); return r.texte; }
    if (Array.isArray(valeur)) { return valeur.map(function (v) { return parcourir(v, total); }); }
    if (valeur && typeof valeur === 'object') {
      var o = {}; Object.keys(valeur).forEach(function (k) { o[k] = parcourir(valeur[k], total); }); return o;
    }
    return valeur;
  }

  // Renvoie la proposition épurée, le décompte des retraits (jamais les valeurs retirées)
  // et des alertes à l'intention du validateur.
  function proposition(p) {
    var total = { marquage: 0, nom: 0, courriel: 0, telephone: 0, cle: 0, ip: 0 };
    var propre = parcourir(p, total);
    var alertes = [];
    if (propre && propre.type === 'script') {
      if (CODE_RESEAU.test(propre.contenu || '')) { alertes.push('Le script contacte (ou peut contacter) un service extérieur.'); }
      if (CODE_DANGER.test(propre.contenu || '')) { alertes.push('Le script contient une instruction non autorisée (commande système, évaluation de texte…).'); }
    }
    if (total.cle) { alertes.push('Une clé ou un mot de passe figurait dans le dépôt : prévenir l\'auteur pour qu\'il la révoque (elle a déjà circulé).'); }
    var nbTotal = 0; for (var k in total) { nbTotal += total[k]; }
    if (nbTotal >= 10) { alertes.push('Épuration importante (' + nbTotal + ' retraits) : vérifier que le contenu reste utilisable et ne repose pas sur des données réelles.'); }
    return { proposition: propre, retraits: total, alertes: alertes };
  }

  return { texte: texte, proposition: proposition };
})();
// ===== EPURER:FIN =====

var LIBELLES = { marquage: 'marquage', nom: 'nom de personne (prénom et nom)', courriel: 'adresse électronique', telephone: 'numéro de téléphone', cle: 'clé ou mot de passe', ip: 'adresse IP' };
var MAX_OCTETS_SANS_PJ = 200000;            // taille maximale d'un dépôt sans pièce jointe
var MAX_OCTETS_DEPOT = 22 * 1024 * 1024;     // 15 Mo de pièces jointes, encodées en base64, plus le texte
var MAX_PJ_OCTETS = 15 * 1024 * 1024;
var MAX_PJ_NOMBRE = 10;
var EXT_PJ = { docx: 'PK', xlsx: 'PK', pptx: 'PK', pdf: '%PDF' };
var MAX_PAR_HEURE = 30;       // dépôts acceptés par heure, tous émetteurs confondus
var MAX_DEPOTS_PAR_ADRESSE_JOUR = 6;
var MAX_CODES_PAR_ADRESSE_HEURE = 3;
var MAX_CODES_PAR_HEURE = 40; // tous émetteurs confondus
var MAX_VERIFS_PAR_HEURE = 300;
var RESERVE_COURRIELS = 30;   // quota de courriels toujours gardé pour prévenir les validateurs
var DUREE_CODE = 900;         // secondes
var DUREE_JETON = 1800;
var ESSAIS_MAX = 5;
var FORMAT = 'bibliotheque-ia-terre/proposition';
var DOMAINES_AUTORISES = ['intradef.gouv.fr', 'academie.def.gouv.fr'];
var DUREE_ENROLEMENT_JOURS = 365;   // une adresse enrôlée le reste un an après son dernier dépôt vérifié

/** À lancer UNE fois à la main (menu « Exécuter »), pour autoriser le script et préparer le dossier. */
function installer() {
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('DOSSIER_ID')) {
    var dossier = DriveApp.createFolder('Bibliothèque IA - dépôts (privé)');
    props.setProperty('DOSSIER_ID', dossier.getId());
  }
  if (!props.getProperty('VALIDATEURS')) {
    props.setProperty('VALIDATEURS', Session.getEffectiveUser().getEmail());
  }
  Logger.log('Dossier : ' + DriveApp.getFolderById(props.getProperty('DOSSIER_ID')).getUrl());
  Logger.log('Validateurs : ' + props.getProperty('VALIDATEURS'));
  Logger.log('Quota de courriels restant aujourd\'hui : ' + MailApp.getRemainingDailyQuota());
}

function doGet() {
  return ContentService.createTextOutput('Boîte de dépôt de la Bibliothèque IA Terre : en service.');
}

function doPost(e) {
  var rep;
  try {
    var brut = (e && e.postData && e.postData.contents) || '';
    if (brut.length > MAX_OCTETS_DEPOT) { rep = { ok: false, erreur: 'Dépôt trop volumineux.' }; }
    else {
      var env = JSON.parse(brut);
      if (env && env.action === 'code') { rep = demanderCode_(env, brut.length); }
      else if (env && env.action === 'verifier') { rep = verifierCode_(env, brut.length); }
      else { rep = traiter_(env); }
    }
  } catch (err) {
    rep = { ok: false, erreur: 'Dépôt illisible.' };
  }
  return ContentService.createTextOutput(JSON.stringify(rep)).setMimeType(ContentService.MimeType.JSON);
}

// ---------- outils ----------
function hex_(octets) {
  return octets.map(function (b) { return ('0' + ((b < 0 ? b + 256 : b)).toString(16)).slice(-2); }).join('');
}
function sha256_(texte) { return hex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, texte, Utilities.Charset.UTF_8)); }
function heure_() { return Utilities.formatDate(new Date(), 'Europe/Paris', 'yyyyMMddHH'); }
function jour_() { return Utilities.formatDate(new Date(), 'Europe/Paris', 'yyyyMMdd'); }

/** Compteur à durée limitée ; renvoie vrai si la limite est dépassée. À appeler sous verrou. */
function compter_(cle, max, duree) {
  var cache = CacheService.getScriptCache();
  var n = parseInt(cache.get(cle) || '0', 10) + 1;
  cache.put(cle, String(n), duree);
  return n > max;
}

function liste_(propriete) {
  return (PropertiesService.getScriptProperties().getProperty(propriete) || '')
    .split(',').map(function (s) { return s.trim().toLowerCase(); }).filter(Boolean);
}

/** Forme stricte d'adresse, en minuscules ; renvoie '' si elle n'est pas acceptable. */
function adresse_(brut) {
  var a = String(brut == null ? '' : brut).trim().toLowerCase();
  if (a.length > 120 || !/^[a-z0-9][a-z0-9._%+'-]{0,63}@[a-z0-9][a-z0-9.-]{1,80}\.[a-z]{2,}$/.test(a)) { return ''; }
  if (a.indexOf('..') >= 0) { return ''; }
  return a;
}

/** Domaine exact d'un domaine sécurisé. */
function domaineSecurise_(a) { return DOMAINES_AUTORISES.indexOf(a.slice(a.lastIndexOf('@') + 1)) >= 0; }

/** Domaine sécurisé, ou adresse dispensée de la règle de domaine (validateurs, propriété EXEMPTES). */
function autorisee_(a) {
  if (domaineSecurise_(a)) { return true; }
  return liste_('VALIDATEURS').indexOf(a) >= 0 || liste_('EXEMPTES').indexOf(a) >= 0;
}

// ---------- adresses enrôlées (empreinte seulement) ----------
function cleEnrol_(a) { return 'E' + sha256_(a).slice(0, 40); }

/** Adresse sécurisée de rattachement si l'adresse est enrôlée et non expirée, sinon ''. */
function enrolee_(a) {
  var brut = PropertiesService.getScriptProperties().getProperty(cleEnrol_(a));
  if (!brut) { return ''; }
  try {
    var e = JSON.parse(brut);
    if (!e || !e.s || !e.d || (Date.now() - e.d) > DUREE_ENROLEMENT_JOURS * 86400000) { return ''; }
    return String(e.s);
  } catch (err) { return ''; }
}
function enroler_(a, securisee) {
  PropertiesService.getScriptProperties().setProperty(cleEnrol_(a), JSON.stringify({ s: securisee, d: Date.now() }));
}
function masquer_(a) {
  var i = a.lastIndexOf('@');
  return a.slice(0, 1) + '***' + a.slice(i);
}

/** À lancer à la main pour retirer une adresse enrôlée : écrire l'adresse dans la propriété « REVOQUER », puis exécuter. */
function revoquer() {
  var props = PropertiesService.getScriptProperties();
  var a = adresse_(props.getProperty('REVOQUER'));
  if (!a) { Logger.log('Propriété REVOQUER absente ou invalide.'); return; }
  var existait = !!props.getProperty(cleEnrol_(a));
  props.deleteProperty(cleEnrol_(a));
  props.deleteProperty('REVOQUER');
  Logger.log(existait ? 'Adresse retirée des adresses enrôlées.' : 'Cette adresse n\'était pas enrôlée.');
}

function codeAleatoire_() {
  var o = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, Utilities.getUuid() + Utilities.getUuid() + String(Date.now()));
  var n = 0;
  for (var i = 0; i < 4; i++) { n = n * 256 + (o[i] < 0 ? o[i] + 256 : o[i]); }
  return ('000000' + (n % 1000000)).slice(-6);
}

// ---------- étape 1 : envoi du code ----------
function demanderCode_(env, taille) {
  if (taille > 2000) { return { ok: false, erreur: 'Demande illisible.' }; }
  var a = adresse_(env.adresse);
  if (!a) { return { ok: false, erreur: 'Adresse électronique invalide.' }; }
  var sec = env.securisee ? adresse_(env.securisee) : '';
  if (env.securisee && !sec) { return { ok: false, besoin_securisee: true, erreur: 'Adresse sécurisée invalide.' }; }

  // Où part le code ? (dest) et à quelle adresse sécurisée l'adresse est-elle rattachée ? (rattache)
  var dest, rattache = '', enrolement = false;
  if (autorisee_(a)) { dest = a; }                      // domaine sécurisé, validateur ou exemptée : le code lui est envoyé
  else {
    var deja = enrolee_(a);
    if (deja) { dest = a; rattache = deja; }             // adresse déjà enrôlée : le code lui est envoyé
    else if (!sec) {
      return { ok: false, besoin_securisee: true, erreur: 'Première utilisation de cette adresse : indiquez aussi une adresse sécurisée (@intradef.gouv.fr ou @academie.def.gouv.fr).' };
    } else if (!domaineSecurise_(sec)) {
      return { ok: false, besoin_securisee: true, erreur: 'L\'adresse sécurisée doit se terminer par @intradef.gouv.fr ou @academie.def.gouv.fr.' };
    } else { dest = sec; rattache = sec; enrolement = true; }
  }

  var verrou = LockService.getScriptLock();
  verrou.waitLock(10000);
  try {
    if (compter_('ca' + sha256_(dest) + heure_(), MAX_CODES_PAR_ADRESSE_HEURE, 3700) ||
        (dest !== a && compter_('cp' + sha256_(a) + heure_(), MAX_CODES_PAR_ADRESSE_HEURE, 3700))) {
      return { ok: false, erreur: 'Trop de codes demandés pour cette adresse. Réessayez dans une heure.' };
    }
    if (compter_('cg' + heure_(), MAX_CODES_PAR_HEURE, 3700) || MailApp.getRemainingDailyQuota() < RESERVE_COURRIELS) {
      return { ok: false, erreur: 'Service momentanément saturé. Réessayez plus tard.' };
    }
    var code = codeAleatoire_();
    var sel = Utilities.getUuid();
    // Le code est lié à l'adresse indiquée dans le formulaire (a), même s'il part vers l'adresse sécurisée.
    CacheService.getScriptCache().put('c' + sha256_(a), JSON.stringify({ h: sha256_(sel + a + code), s: sel, e: 0, r: rattache, n: enrolement ? 1 : 0 }), DUREE_CODE);
    var debut = 'Bonjour,\n\n';
    var objet = enrolement
      ? 'Quelqu\'un (vous, sans doute) veut déposer sur la Bibliothèque IA Terre avec l\'adresse ' + a + ' et l\'a rattachée à votre adresse sécurisée.\n' +
        'Votre code de vérification : ' + code + '\n\n' +
        'Saisissez-le sur la page de dépôt : il valide à la fois l\'adresse ' + a + ' et le dépôt. Les prochains dépôts de cette adresse se vérifieront directement sur elle.\n'
      : 'Votre code de vérification pour déposer sur la Bibliothèque IA Terre : ' + code + '\n\n' + 'Saisissez-le sur la page de dépôt.\n';
    MailApp.sendEmail({
      to: dest, name: 'Bibliothèque IA Terre',
      subject: 'Votre code de vérification : ' + code,
      body: debut + objet + 'Il est valable 15 minutes.\n' +
            'Si vous n\'êtes pas à l\'origine de cette demande, ignorez ce message : rien ne sera déposé.\n'
    });
    return { ok: true, envoye_a: dest === a ? 'adresse' : 'securisee', masque: masquer_(dest) };
  } finally { verrou.releaseLock(); }
}

// ---------- étape 2 : vérification du code ----------
function verifierCode_(env, taille) {
  if (taille > 2000) { return { ok: false, erreur: 'Demande illisible.' }; }
  var a = adresse_(env.adresse);
  var code = String(env.code == null ? '' : env.code).replace(/\s+/g, '');
  if (!a || !/^\d{6}$/.test(code)) { return { ok: false, erreur: 'Code ou adresse invalide.' }; }
  var verrou = LockService.getScriptLock();
  verrou.waitLock(10000);
  try {
    if (compter_('vg' + heure_(), MAX_VERIFS_PAR_HEURE, 3700)) { return { ok: false, erreur: 'Service momentanément saturé. Réessayez plus tard.' }; }
    var cache = CacheService.getScriptCache();
    var cle = 'c' + sha256_(a);
    var brut = cache.get(cle);
    if (!brut) { return { ok: false, erreur: 'Code expiré ou inconnu. Demandez un nouveau code.' }; }
    var entree = JSON.parse(brut);
    if (entree.e >= ESSAIS_MAX) { cache.remove(cle); return { ok: false, erreur: 'Trop d\'essais. Demandez un nouveau code.' }; }
    if (sha256_(entree.s + a + code) !== entree.h) {
      entree.e++;
      if (entree.e >= ESSAIS_MAX) { cache.remove(cle); } else { cache.put(cle, JSON.stringify(entree), DUREE_CODE); }
      return { ok: false, erreur: 'Code incorrect.' };
    }
    cache.remove(cle);                                   // un code ne sert qu'une fois
    if (entree.r) { enroler_(a, entree.r); }             // enrôlement (1re fois) ou renouvellement d'un an
    var jeton = Utilities.getUuid() + Utilities.getUuid();
    cache.put('j' + sha256_(jeton), JSON.stringify({ a: a, r: entree.r || '' }), DUREE_JETON);
    return { ok: true, jeton: jeton };
  } finally { verrou.releaseLock(); }
}

// ---------- étape 3 : le dépôt ----------
function limiteAtteinte_() {
  var verrou = LockService.getScriptLock();
  verrou.waitLock(10000);
  try { return compter_('n' + heure_(), MAX_PAR_HEURE, 3700); } finally { verrou.releaseLock(); }
}

function nomFichier_(titre) {
  var base = String(titre || 'projet').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'projet';
  return 'proposition-' + base + '-' + Utilities.formatDate(new Date(), 'Europe/Paris', 'yyyyMMdd-HHmmss') + '.json';
}

/** Contrôle côté serveur des pièces jointes : nombre, taille, type annoncé, signature, empreinte. L'analyse approfondie est faite par le skill. */
function controlerPj_(liste) {
  if (liste == null || (Array.isArray(liste) && !liste.length)) { return { ok: true, pj: [] }; }
  if (!Array.isArray(liste) || liste.length > MAX_PJ_NOMBRE) { return { ok: false, erreur: 'Trop de pièces jointes (maximum ' + MAX_PJ_NOMBRE + ').' }; }
  var total = 0, sortie = [];
  for (var i = 0; i < liste.length; i++) {
    var x = liste[i];
    if (!x || typeof x.nom !== 'string' || typeof x.contenu_b64 !== 'string' || typeof x.sha256 !== 'string') {
      return { ok: false, erreur: 'Pièce jointe ' + (i + 1) + ' invalide.' };
    }
    var m = /\.([A-Za-z0-9]{2,5})$/.exec(x.nom);
    var ext = m ? m[1].toLowerCase() : '';
    if (!EXT_PJ.hasOwnProperty(ext)) { return { ok: false, erreur: 'Type de pièce jointe non accepté : ' + x.nom.slice(0, 60) + ' (acceptés : .docx .xlsx .pptx .pdf).' }; }
    if (!/^[A-Za-z0-9+\/]*={0,2}$/.test(x.contenu_b64) || x.contenu_b64.length % 4 !== 0) { return { ok: false, erreur: 'Pièce jointe illisible : ' + x.nom.slice(0, 60) }; }
    var octets = Utilities.base64Decode(x.contenu_b64);
    total += octets.length;
    if (total > MAX_PJ_OCTETS) { return { ok: false, erreur: 'Pièces jointes trop lourdes (maximum 15 Mo au total).' }; }
    var debut = octets.slice(0, 8).map(function (b) { return String.fromCharCode(b < 0 ? b + 256 : b); }).join('');
    if (debut.indexOf(EXT_PJ[ext]) !== 0 && !(ext === 'pdf' && debut.indexOf('%PDF') >= 0)) {
      return { ok: false, erreur: 'Le contenu de « ' + x.nom.slice(0, 60) + ' » ne correspond pas à son type.' };
    }
    var h = hex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, octets));
    if (h !== x.sha256.toLowerCase()) { return { ok: false, erreur: 'Pièce jointe abîmée pendant l\'envoi : ' + x.nom.slice(0, 60) + '. Recommencez.' }; }
    sortie.push({ nom: x.nom, taille: octets.length, sha256: h, contenu_b64: x.contenu_b64 });
  }
  return { ok: true, pj: sortie, total: total };
}

function traiter_(enveloppe) {
  if (enveloppe && enveloppe.piege) { return { ok: true }; }            // champ-piège rempli : on fait semblant
  var p = enveloppe && enveloppe.p;
  if (!p || p.format !== FORMAT || typeof p.titre !== 'string' || !p.titre.trim()) {
    return { ok: false, erreur: 'Ce n\'est pas une proposition de la bibliothèque.' };
  }
  // Adresse vérifiée : le jeton obtenu avec le code est obligatoire.
  var adresse = adresse_(enveloppe.adresse);
  var cache = CacheService.getScriptCache();
  var cleJeton = 'j' + sha256_(String(enveloppe.jeton || ''));
  var jeton = null;
  try { jeton = JSON.parse(cache.get(cleJeton) || 'null'); } catch (err) { jeton = null; }
  if (!adresse || !enveloppe.jeton || !jeton || jeton.a !== adresse) {
    return { ok: false, erreur: 'Adresse non vérifiée ou vérification expirée. Recommencez la vérification par code.', verification: true };
  }
  var pjBrut = p.pieces_jointes;
  delete p.pieces_jointes;                                              // le base64 ne doit jamais passer par l'épuration de texte
  if (!pjBrut || !pjBrut.length) {
    if (JSON.stringify(p).length > MAX_OCTETS_SANS_PJ) { return { ok: false, erreur: 'Dépôt trop volumineux.' }; }
  } else if (JSON.stringify(p).length > MAX_OCTETS_SANS_PJ) { return { ok: false, erreur: 'Texte du dépôt trop volumineux.' }; }
  var verrou = LockService.getScriptLock();
  verrou.waitLock(10000);
  try {
    if (compter_('d' + sha256_(adresse) + jour_(), MAX_DEPOTS_PAR_ADRESSE_JOUR, 90000)) {
      return { ok: false, erreur: 'Nombre maximal de dépôts atteint aujourd\'hui pour cette adresse.' };
    }
  } finally { verrou.releaseLock(); }
  if (limiteAtteinte_()) { return { ok: false, erreur: 'Trop de dépôts en ce moment. Réessayez dans une heure.' }; }

  var controle = controlerPj_(pjBrut);
  if (!controle.ok) { return { ok: false, erreur: controle.erreur }; }

  var props = PropertiesService.getScriptProperties();
  var epure = Epurer.proposition(p);
  // Les noms de fichiers passent aussi par l'épuration (un nom de personne dans un nom de fichier).
  var pj = controle.pj.map(function (x) {
    var r = Epurer.texte(x.nom);
    for (var k in r.retraits) { epure.retraits[k] = (epure.retraits[k] || 0) + r.retraits[k]; }
    return { nom: r.texte, taille: x.taille, sha256: x.sha256, contenu_b64: x.contenu_b64 };
  });
  // Le fichier transmis aux validateurs porte un bloc « reception » (ce qui a été retiré, alertes) que le
  // skill de validation lit puis retire : il n'est jamais publié.
  var recu = Utilities.formatDate(new Date(), 'Europe/Paris', "yyyy-MM-dd'T'HH:mm:ssXXX");
  var fichier = {};
  Object.keys(epure.proposition).forEach(function (k) { fichier[k] = epure.proposition[k]; });
  if (pj.length) { fichier.pieces_jointes = pj; }
  fichier.reception = { recu_le: recu, retraits: epure.retraits, alertes: epure.alertes, boite: 2, adresse_verifiee: adresse, adresse_securisee: jeton.r || '' };
  var json = JSON.stringify(fichier, null, 2);
  var nom = nomFichier_(p.titre);

  var dossierId = props.getProperty('DOSSIER_ID');
  if (!dossierId) { return { ok: false, erreur: 'Boîte non installée.' }; }
  DriveApp.getFolderById(dossierId).createFile(nom, json, 'application/json');

  var retraits = Object.keys(epure.retraits).filter(function (k) { return epure.retraits[k]; })
    .map(function (k) { return '- ' + epure.retraits[k] + ' × ' + LIBELLES[k]; });
  var contact = String(enveloppe.contact || '').slice(0, 200);
  var q = epure.proposition;
  var corps = [
    'Nouveau dépôt reçu dans la boîte de la Bibliothèque IA Terre.',
    '',
    'Titre : ' + q.titre,
    'Type : ' + q.type + ' · Pseudo : ' + (q.auteur || '(non renseigné)'),
    'IA indiquées : ' + (Array.isArray(q.ia_compatibles) ? q.ia_compatibles.join(', ') : ''),
    'Résumé : ' + (q.resume || ''),
    'Adresse vérifiée par code (à ne pas publier) : ' + adresse,
    jeton.r ? 'Adresse sécurisée de rattachement (à ne pas publier) : ' + jeton.r : '',
    contact ? 'Autre contact laissé par l\'auteur (à ne pas publier) : ' + contact : '',
    '',
    pj.length ? 'Pièces jointes (' + pj.length + ', ' + (controle.total / 1048576).toFixed(1) + ' Mo) :\n' + pj.map(function (x) { return '- ' + x.nom + ' (' + Math.round(x.taille / 1024) + ' Ko)'; }).join('\n') +
      '\n(Elles sont à l\'intérieur du fichier joint : le skill les contrôle — macros, objets actifs, mots de passe… — avant toute validation.)' : 'Aucune pièce jointe.',
    '',
    retraits.length ? 'Éléments retirés automatiquement (valeurs non conservées) :\n' + retraits.join('\n') : 'Aucun élément à retirer.',
    epure.alertes.length ? '\nÀ VÉRIFIER :\n- ' + epure.alertes.join('\n- ') : '',
    '',
    'Fichier joint : ' + nom,
    '',
    'POUR VALIDER (le skill « valider-depot » doit être installé dans votre Claude) :',
    '1. Enregistrez le fichier joint sur votre ordinateur.',
    '2. Ouvrez une conversation Claude et glissez-y le fichier.',
    '3. Écrivez : Valide ce dépôt avec le skill valider-depot.',
    'Rien n\'est publié tant que le dépôt n\'a pas été validé et fusionné.'
  ].join('\n');

  var dest = liste_('VALIDATEURS');
  var envoye = false;
  if (dest.length && MailApp.getRemainingDailyQuota() > 0) {
    MailApp.sendEmail({
      to: dest.join(','), subject: '[Bibliothèque IA] Dépôt : ' + q.titre + ' (' + q.type + ')' + (pj.length ? ' + ' + pj.length + ' pièce(s) jointe(s)' : ''),
      body: corps, name: 'Bibliothèque IA Terre - dépôts',
      attachments: [Utilities.newBlob(json, 'application/json', nom)]
    });
    envoye = true;
  }
  cache.remove(cleJeton);                                // le jeton ne sert qu'une fois
  return { ok: true, prevenu: envoye, retraits: epure.retraits };
}
