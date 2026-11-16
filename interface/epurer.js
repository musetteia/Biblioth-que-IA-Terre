/* Fichier généré par outils/synchroniser_epurer.py : ne pas modifier à la main.
   Source : boite-de-depot/Code.gs (bloc EPURER). */
var Epurer = (function () {
  var MARQUAGES = /(^|[^A-Za-zÀ-ÿ])(DIFFUSION\s+RESTREINTE|CONFIDENTIEL(?:\s+D[ÉE]FENSE)?|SECRET(?:\s+D[ÉE]FENSE)?|TR[ÈE]S\s+SECRET|NON\s+PROT[ÉE]G[ÉE]|RESTRICTED|NATO\s+(?:SECRET|CONFIDENTIAL|RESTRICTED))(?![A-Za-zÀ-ÿ])/g;
  var COURRIEL = /(?<![\w.+-])[\w.+-]+@([\w-]+(?:\.[\w-]+)+)/g;
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
