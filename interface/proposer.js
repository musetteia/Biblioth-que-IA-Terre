/* Formulaire « Proposer un projet ». Tout se prépare dans le navigateur ; rien n'est envoyé
   tant que le contributeur n'a pas cliqué sur « Envoyer ». Les marquages, noms de personnes, adresses,
   téléphones et clés sont retirés automatiquement (epurer.js) au lieu de bloquer le dépôt. */
(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('donnees').textContent);
  var V = D.vocab;
  var RACINE = document.getElementById('formulaire');
  var CLE_BROUILLON = 'bibliotheque-ia-brouillon';
  var MAX_ETAPES = 8;

  var AIDE_TYPE = {
    prompt: 'Un texte à coller dans une conversation avec une IA.',
    skill: 'Une compétence packagée, que certains outils savent charger.',
    projet: 'Des consignes et des documents pour un espace de travail dédié.',
    script: 'Un petit programme Python qui travaille sur des fichiers.'
  };
  var CONTENU = {
    prompt: ['Le prompt', 'Le texte du prompt, tel que l\'utilisateur le collera dans l\'IA : glissez votre fichier dans le cadre ci-dessous, ou collez le texte.'],
    projet: ['Les instructions du projet', 'Les instructions à donner à l\'IA (étape par étape, avec les garde-fous) : glissez votre fichier dans le cadre ci-dessous, ou collez le texte.'],
    skill: ['Le contenu du skill', 'Glissez le .zip du skill ou son fichier SKILL.md dans le cadre ci-dessous, ou collez le contenu de SKILL.md. L\'en-tête (nom, description) sera ajouté si vous l\'oubliez.'],
    script: ['Le code Python', 'Le code complet : glissez votre fichier .py dans le cadre ci-dessous, ou collez le code. Il ne doit utiliser aucun accès réseau ni lancer de commande système.']
  };

  // ---- petits outils DOM ---------------------------------------------------
  function el(nom, attrs, enfants) {
    var n = document.createElement(nom);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'classe') { n.className = attrs[k]; }
      else if (k === 'texte') { n.textContent = attrs[k]; }
      else { n.setAttribute(k, attrs[k]); }
    });
    (enfants || []).forEach(function (e) { if (e) { n.appendChild(e); } });
    return n;
  }
  function trouver(id) { return document.getElementById(id); }
  function valeur(id) { var n = trouver(id); return n ? n.value.trim() : ''; }

  function champ(id, titre, aide, controle, requis) {
    var etiquette = el('label', { 'for': id, classe: 'champ-titre' }, [el('span', { texte: titre })]);
    etiquette.appendChild(requis ? el('span', { classe: 'requis', texte: ' (obligatoire)' }) : el('span', { classe: 'facultatif', texte: ' (facultatif)' }));
    var enfants = [etiquette];
    if (aide) { enfants.push(el('p', { classe: 'champ-aide', id: id + '-aide', texte: aide })); controle.setAttribute('aria-describedby', id + '-aide'); }
    controle.id = id;
    enfants.push(controle);
    return el('div', { classe: 'champ' }, enfants);
  }
  function ligne(id, ph) { return el('input', { type: 'text', classe: 'saisie', placeholder: ph || '' }); }
  function zone(rows, ph, mono) { return el('textarea', { classe: 'saisie' + (mono ? ' mono' : ''), rows: String(rows), placeholder: ph || '' }); }
  function liste(vocabulaire, vide) {
    var s = el('select', { classe: 'saisie' });
    if (vide) { s.appendChild(el('option', { value: '', texte: vide })); }
    Object.keys(vocabulaire).forEach(function (k) { s.appendChild(el('option', { value: k, texte: vocabulaire[k] })); });
    return s;
  }
  function section(titre, intro, enfants) {
    return el('fieldset', { classe: 'bloc-form' }, [el('legend', { texte: titre }), intro ? el('p', { classe: 'bloc-intro', texte: intro }) : null].concat(enfants));
  }

  // ---- construction du formulaire -----------------------------------------
  var typeRadios = el('div', { classe: 'choix-type', role: 'radiogroup', 'aria-labelledby': 'type-titre' });
  Object.keys(V.type).forEach(function (k, i) {
    var radio = el('input', { type: 'radio', name: 'type', value: k, id: 'type-' + k });
    if (i === 0) { radio.defaultChecked = true; radio.checked = true; }
    typeRadios.appendChild(el('label', { classe: 'carte-choix', 'for': 'type-' + k }, [radio, el('span', { classe: 'carte-choix-nom', texte: V.type[k] }), el('span', { classe: 'carte-choix-aide', texte: AIDE_TYPE[k] })]));
  });

  var iaBoites = el('div', { classe: 'choix-ia' });
  Object.keys(V.ia).forEach(function (k) {
    iaBoites.appendChild(el('label', { classe: 'case' }, [el('input', { type: 'checkbox', name: 'ia', value: k }), el('span', { texte: V.ia[k] })]));
  });

  var etapesZone = el('div', { id: 'etapes-form' });
  var boutonAjouter = el('button', { type: 'button', classe: 'bouton secondaire', texte: 'Ajouter une étape' });

  var attestations = el('div', { classe: 'attestations' });
  Object.keys(V.controles).forEach(function (k) {
    attestations.appendChild(el('label', { classe: 'case' }, [el('input', { type: 'checkbox', name: 'controles', value: k }), el('span', { texte: V.controles[k] })]));
  });

  var contenuLabel = el('span', { id: 'contenu-titre' });
  var contenuAide = el('p', { classe: 'champ-aide', id: 'contenu-aide' });
  var contenuZone = zone(14, '', true); contenuZone.id = 'contenu'; contenuZone.setAttribute('aria-describedby', 'contenu-aide');

  // Zone de dépôt d'un fichier : le fichier est lu dans ce navigateur et recopié dans le champ « contenu ».
  // Rien n'est envoyé avant le clic sur « Envoyer ».
  var choixFichier = el('input', { type: 'file', id: 'fichier-contenu', classe: 'sr-only', tabindex: '-1', accept: '.md,.txt,.py,.zip,.json,.yaml,.yml,.csv,text/plain,text/markdown' });
  var boutonFichier = el('button', { type: 'button', classe: 'bouton secondaire', id: 'choisir-fichier', texte: 'Choisir un fichier' });
  var depot = el('div', { classe: 'zone-depot', id: 'zone-depot' }, [
    el('p', { classe: 'zone-depot-titre', texte: 'Glissez ici votre fichier de prompt, de skill ou de script' }),
    el('p', { classe: 'zone-depot-aide', texte: 'Prompt ou instructions en .md ou .txt, script en .py, skill en .zip ou SKILL.md. Vous pouvez aussi copier-coller le texte dans le champ ci-dessous.' }),
    boutonFichier, choixFichier
  ]);
  var retourFichier = el('div', { classe: 'retour-fichier', id: 'retour-fichier', role: 'status', 'aria-live': 'polite', hidden: 'hidden' });

  // Pièces jointes : documents Word, Excel, PowerPoint ou PDF liés au projet. Lus dans ce navigateur, contrôlés
  // une première fois ici, puis par la boîte de dépôt, par le validateur (skill) et par le robot de la bibliothèque.
  var choixPj = el('input', { type: 'file', id: 'fichier-pj', classe: 'sr-only', tabindex: '-1', multiple: 'multiple', accept: '.docx,.xlsx,.pptx,.pdf' });
  var boutonPj = el('button', { type: 'button', classe: 'bouton secondaire', id: 'choisir-pj', texte: 'Choisir des fichiers' });
  var depotPj = el('div', { classe: 'zone-depot', id: 'zone-depot-pj' }, [
    el('p', { classe: 'zone-depot-titre', texte: 'Glissez ici vos pièces jointes' }),
    el('p', { classe: 'zone-depot-aide', texte: 'Word (.docx), Excel (.xlsx), PowerPoint (.pptx) ou PDF. 10 fichiers et 15 Mo au maximum en tout. Les macros, objets incorporés, liens vers d\'autres fichiers et mots de passe sont refusés. Si un document ne contient que du texte, collez plutôt ce texte dans le champ du contenu.' }),
    boutonPj, choixPj
  ]);
  var retourPj = el('div', { classe: 'retour-fichier', id: 'retour-pj', role: 'status', 'aria-live': 'polite', hidden: 'hidden' });
  var listePj = el('ul', { classe: 'liste-pj', id: 'liste-pj', hidden: 'hidden' });

  var erreursZone = el('div', { id: 'erreurs', classe: 'erreurs-form', role: 'alert', hidden: 'hidden' });
  var resultat = el('div', { id: 'resultat', classe: 'resultat-form', hidden: 'hidden' });

  var piege = el('input', { type: 'text', id: 'site-web', name: 'site-web', tabindex: '-1', autocomplete: 'off', 'aria-hidden': 'true' });
  piege.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;opacity:0';

  var formulaire = el('form', { novalidate: 'novalidate', classe: 'formulaire' }, [
    section('1. L\'essentiel (obligatoire)', 'Cinq informations suffisent. Tout le reste est facultatif : la personne qui relira votre dépôt le complétera avec l\'aide de l\'IA.', [
      champ('titre', 'Titre', 'Court et parlant. Exemple : Synthèse de conférence.', ligne('titre'), true),
      champ('auteur', 'Pseudo ou prénom', 'Pas de nom complet ni d\'unité (un prénom et un nom seraient retirés).', ligne('auteur'), true),
      champ('resume', 'Résumé', 'Deux ou trois phrases : ce que fait le projet et pour qui.', zone(3), true),
      el('div', { classe: 'champ' }, [el('span', { classe: 'champ-titre', id: 'type-titre', texte: 'Type de projet' }), typeRadios]),
      el('div', { classe: 'champ' }, [el('span', { classe: 'champ-titre', id: 'ia-titre' }, [el('span', { texte: 'Testé avec' }), el('span', { classe: 'requis', texte: ' (obligatoire)' })]), el('p', { classe: 'champ-aide', texte: 'Cochez les IA avec lesquelles vous l\'avez testé. « Toutes les IA » si le projet est générique.' }), iaBoites])
    ]),
    section('2. Le contenu (obligatoire)', 'C\'est le cœur du projet : ce que les camarades vont copier.', [
      el('div', { classe: 'champ' }, [el('label', { 'for': 'contenu', classe: 'champ-titre' }, [contenuLabel, el('span', { classe: 'requis', texte: ' (obligatoire)' })]), contenuAide, depot, retourFichier, contenuZone]),
      el('div', { classe: 'champ' }, [el('span', { classe: 'champ-titre', id: 'pj-titre' }, [el('span', { texte: 'Pièces jointes' }), el('span', { classe: 'facultatif', texte: ' (facultatif)' })]),
        el('p', { classe: 'champ-aide', texte: 'Un document lié à votre projet (modèle, fiche, tableau…). Ces fichiers ne sont pas gardés dans le brouillon : si vous rechargez la page, ajoutez-les de nouveau.' }), depotPj, retourPj, listePj])
    ]),
    section('3. Vos engagements (obligatoire)', 'Vous certifiez avoir vérifié ces quatre points. Ils s\'affichent sur la fiche.', [attestations]),
    section('4. Pour compléter la fiche (facultatif)', 'Vous pouvez tout laisser vide. Ce que vous renseignez ici sera repris tel quel ; le reste sera proposé par la personne qui relit.', [
      el('div', { classe: 'ligne-deux' }, [
        champ('usage', 'Usage principal', '', liste(V.usage, '— à compléter par la relecture —')),
        champ('niveau', 'Niveau demandé à l\'utilisateur', '', liste(V.niveau, '— à compléter par la relecture —'))
      ]),
      el('div', { classe: 'ligne-deux' }, [
        champ('langue', 'Langue des consignes', '', liste(V.langue, '— à compléter par la relecture —')),
        champ('etiquettes', 'Mots-clés', 'Jusqu\'à 5, séparés par des virgules.', ligne('etiquettes'))
      ]),
      champ('probleme', 'Le problème résolu', 'Quelle situation, qu\'est-ce qui prend du temps ou fait des erreurs aujourd\'hui ?', zone(4)),
      champ('donne', 'Ce que l\'utilisateur donne', 'Exemple : ses notes brutes, collées telles quelles.', ligne('donne')),
      champ('recoit', 'Ce que l\'utilisateur reçoit', 'Exemple : une fiche structurée avec les idées clés.', ligne('recoit')),
      champ('limites', 'Limites connues', 'Ce que le projet ne fait pas ou fait mal. Une limite par ligne.', zone(3))
    ]),
    section('5. Comment ça marche, étape par étape (facultatif)', 'Vous pouvez laisser cette partie vide. Si vous la remplissez, comptez au moins 2 étapes (maximum ' + MAX_ETAPES + '). Pour chacune, dites qui agit : l\'utilisateur ou l\'IA. Une étape laissée entièrement vide est ignorée.', [etapesZone, boutonAjouter]),
    section('6. Exemples fictifs (facultatif, mais recommandé)', 'Un exemple d\'entrée et le résultat attendu permettent de tester le projet en deux minutes. Entièrement inventés.', [
      champ('exemple_entree', 'Exemple d\'entrée', '', zone(4, '', true)),
      champ('exemple_sortie', 'Résultat attendu', '', zone(4, '', true))
    ]),
    section('7. Contact (facultatif)', 'Une adresse pour que la personne qui relit puisse vous poser une question. Elle n\'est jamais publiée ni écrite dans la fiche.', [
      champ('contact', 'Votre adresse de messagerie', '', ligne('contact'))
    ]),
    piege,
    erreursZone,
    el('div', { classe: 'actions-form' }, [
      el('button', { type: 'submit', classe: 'bouton', texte: 'Vérifier et préparer ma proposition' }),
      el('button', { type: 'button', classe: 'bouton lien', id: 'effacer', texte: 'Tout effacer' })
    ]),
    resultat
  ]);
  RACINE.appendChild(formulaire);

  // ---- étapes ---------------------------------------------------------------
  var compteurEtapes = 0;
  function ajouterEtape(e) {
    e = e || {};
    compteurEtapes += 1;
    var n = compteurEtapes;
    var nomQui = 'qui-' + n;
    var bloc = el('div', { classe: 'etape-form', 'data-etape': String(n) });
    var radios = el('div', { classe: 'choix-qui', role: 'radiogroup', 'aria-label': 'Qui agit dans cette étape' });
    [['vous', 'L\'utilisateur'], ['ia', 'L\'IA']].forEach(function (p) {
      var r = el('input', { type: 'radio', name: nomQui, value: p[0] });
      if ((e.qui || 'vous') === p[0]) { r.checked = true; }
      radios.appendChild(el('label', { classe: 'case' }, [r, el('span', { texte: p[1] })]));
    });
    var supprimer = el('button', { type: 'button', classe: 'bouton lien', texte: 'Supprimer cette étape' });
    supprimer.addEventListener('click', function () {
      if (etapesZone.children.length > 2) { etapesZone.removeChild(bloc); renumeroter(); sauver(); }
    });
    var t = ligne('', 'Exemple : Tri et plan'); t.setAttribute('data-champ', 'titre'); t.value = e.titre || '';
    var ent = ligne('', 'Ce qui entre dans cette étape'); ent.setAttribute('data-champ', 'entree'); ent.value = e.entree || '';
    var sor = ligne('', 'Ce qui en sort'); sor.setAttribute('data-champ', 'sortie'); sor.value = e.sortie || '';
    var tx = zone(2, 'Une ou deux phrases pour expliquer l\'étape (facultatif)'); tx.setAttribute('data-champ', 'texte'); tx.value = e.texte || '';
    var ex = zone(3, 'Un court exemple fictif de cette étape (facultatif)', true); ex.setAttribute('data-champ', 'exemple'); ex.value = e.exemple || '';
    function sousChamp(titre, c) { return el('label', { classe: 'sous-champ' }, [el('span', { texte: titre }), c]); }
    bloc.appendChild(el('div', { classe: 'etape-entete' }, [el('strong', { classe: 'etape-num' }), supprimer]));
    bloc.appendChild(sousChamp('Titre de l\'étape', t));
    bloc.appendChild(el('div', { classe: 'champ' }, [el('span', { classe: 'sous-titre', texte: 'Qui agit ?' }), radios]));
    bloc.appendChild(el('div', { classe: 'ligne-deux' }, [sousChamp('Entrée', ent), sousChamp('Sortie', sor)]));
    bloc.appendChild(sousChamp('Explication', tx));
    bloc.appendChild(sousChamp('Exemple fictif', ex));
    etapesZone.appendChild(bloc);
    renumeroter();
  }
  function renumeroter() {
    var blocs = etapesZone.children;
    for (var i = 0; i < blocs.length; i++) {
      blocs[i].querySelector('.etape-num').textContent = 'Étape ' + (i + 1);
      blocs[i].querySelector('.bouton.lien').hidden = blocs.length <= 2;
    }
    boutonAjouter.disabled = blocs.length >= MAX_ETAPES;
  }
  boutonAjouter.addEventListener('click', function () {
    if (etapesZone.children.length < MAX_ETAPES) { ajouterEtape(); sauver(); }
  });

  // ---- lecture / écriture de l'état ---------------------------------------
  function typeChoisi() { var r = formulaire.querySelector('input[name=type]:checked'); return r ? r.value : 'prompt'; }
  function coches(nom) {
    return Array.prototype.map.call(formulaire.querySelectorAll('input[name=' + nom + ']:checked'), function (c) { return c.value; });
  }
  function lireEtapes() {
    return Array.prototype.map.call(etapesZone.children, function (b) {
      var r = b.querySelector('input[type=radio]:checked');
      var o = { qui: r ? r.value : '' };
      Array.prototype.forEach.call(b.querySelectorAll('[data-champ]'), function (c) { o[c.getAttribute('data-champ')] = c.value.trim(); });
      return o;
    });
  }
  function etat() {
    return {
      format: 'bibliotheque-ia-terre/proposition', version: 1,
      titre: valeur('titre'), resume: valeur('resume'), type: typeChoisi(),
      usage: valeur('usage'), niveau: valeur('niveau'), langue: valeur('langue'),
      ia_compatibles: coches('ia'), etiquettes: valeur('etiquettes'), auteur: valeur('auteur'),
      probleme: valeur('probleme'), donne: valeur('donne'), recoit: valeur('recoit'), limites: valeur('limites'),
      contenu: contenuZone.value.trim(), etapes: lireEtapes(),
      exemple_entree: valeur('exemple_entree'), exemple_sortie: valeur('exemple_sortie'),
      controles: coches('controles')
    };
  }
  function appliquer(s) {
    ['titre', 'resume', 'usage', 'niveau', 'langue', 'etiquettes', 'auteur', 'probleme', 'donne', 'recoit', 'limites', 'exemple_entree', 'exemple_sortie', 'contact'].forEach(function (id) {
      if (typeof s[id] === 'string' && trouver(id)) { trouver(id).value = s[id]; }
    });
    var r = formulaire.querySelector('input[name=type][value="' + s.type + '"]'); if (r) { r.checked = true; }
    formulaire.querySelectorAll('input[name=ia]').forEach(function (c) { c.checked = (s.ia_compatibles || []).indexOf(c.value) >= 0; });
    formulaire.querySelectorAll('input[name=controles]').forEach(function (c) { c.checked = (s.controles || []).indexOf(c.value) >= 0; });
    if (typeof s.contenu === 'string') { contenuZone.value = s.contenu; }
    etapesZone.textContent = '';
    var etapes = (s.etapes && s.etapes.length) ? s.etapes : [{}, {}];
    etapes.slice(0, MAX_ETAPES).forEach(ajouterEtape);
    while (etapesZone.children.length < 2) { ajouterEtape(); }
  }
  function majContenu() {
    var t = CONTENU[typeChoisi()];
    contenuLabel.textContent = t[0];
    contenuAide.textContent = t[1];
  }

  // ---- brouillon (confort : ce navigateur seulement) ---------------------
  var minuteur = null;
  function sauver() {
    clearTimeout(minuteur);
    minuteur = setTimeout(function () {
      try { localStorage.setItem(CLE_BROUILLON, JSON.stringify(etat())); } catch (e) { /* stockage indisponible : sans importance */ }
    }, 400);
  }
  function restaurer() {
    try {
      var brut = localStorage.getItem(CLE_BROUILLON);
      if (brut) { appliquer(JSON.parse(brut)); return true; }
    } catch (e) { /* ignoré */ }
    return false;
  }

  // ---- contrôles -----------------------------------------------------------
  function etapeRemplie(e) {
    return !!(e.titre || e.entree || e.sortie || e.texte || e.exemple);
  }
  function verifierChamps(s) {
    var p = [];
    [['titre', 'Le titre'], ['auteur', 'Le pseudo ou prénom'], ['resume', 'Le résumé']].forEach(function (c) {
      if (!s[c[0]]) { p.push({ id: c[0], texte: c[1] + ' est à remplir.' }); }
    });
    if (!s.ia_compatibles.length) { p.push({ id: 'ia-titre', texte: 'Cochez au moins une IA.' }); }
    if (!s.contenu) { p.push({ id: 'contenu', texte: CONTENU[s.type][0] + ' est à remplir.' }); }
    // Partie 4 facultative : les étapes entièrement vides ont déjà été écartées.
    // Si l'on en remplit, chacune doit être complète, et il en faut au moins deux.
    s.etapes.forEach(function (e) {
      if (!e.titre || !e.entree || !e.sortie) { p.push({ id: null, texte: 'Étape ' + e.n + ' : le titre, l\'entrée et la sortie sont à remplir (ou videz entièrement l\'étape pour l\'ignorer).' }); }
    });
    if (s.etapes.length === 1) { p.push({ id: null, texte: 'Une seule étape est remplie : il en faut au moins deux pour le schéma. Ajoutez-en une, ou videz celle-ci pour passer cette partie.' }); }
    if (s.controles.length < 4) { p.push({ id: null, texte: 'Les quatre engagements doivent être cochés.' }); }
    if (s.etiquettes.split(',').filter(function (x) { return x.trim(); }).length > 5) { p.push({ id: 'etiquettes', texte: '5 mots-clés au maximum.' }); }
    return p;
  }

  function nomFichier(s) {
    var base = s.titre.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'projet';
    return 'proposition-' + base + '.json';
  }

  function montrerErreurs(liste) {
    erreursZone.textContent = '';
    erreursZone.appendChild(el('p', { classe: 'erreurs-titre', texte: 'À corriger avant de continuer :' }));
    var ul = el('ul');
    liste.forEach(function (e) {
      var li = el('li');
      if (e.id && trouver(e.id)) {
        var a = el('a', { href: '#' + e.id, texte: e.texte });
        a.addEventListener('click', function (ev) { ev.preventDefault(); trouver(e.id).scrollIntoView({ block: 'center' }); if (trouver(e.id).focus) { trouver(e.id).focus(); } });
        li.appendChild(a);
      } else { li.textContent = e.texte; }
      ul.appendChild(li);
    });
    erreursZone.appendChild(ul);
    erreursZone.hidden = false;
    resultat.hidden = true;
    erreursZone.scrollIntoView({ block: 'center' });
  }

  function copier(texte, bouton) {
    function ok() { var avant = bouton.textContent; bouton.textContent = 'Copié'; setTimeout(function () { bouton.textContent = avant; }, 1800); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texte).then(ok, function () { secours(texte, ok); });
    } else { secours(texte, ok); }
  }
  function secours(texte, ok) {
    var t = el('textarea', { 'aria-hidden': 'true' }); t.value = texte; t.style.position = 'fixed'; t.style.opacity = '0';
    document.body.appendChild(t); t.select();
    try { document.execCommand('copy'); ok(); } catch (e) { /* le texte reste affiché pour copie manuelle */ }
    document.body.removeChild(t);
  }

  var LIBELLES_RETRAITS = { marquage: 'mention de protection', nom: 'nom de personne (prénom et nom)', courriel: 'adresse de messagerie', telephone: 'numéro de téléphone', cle: 'clé ou mot de passe', ip: 'adresse IP' };

  function phraseRetraits(retraits) {
    var l = Object.keys(LIBELLES_RETRAITS).filter(function (k) { return retraits[k]; }).map(function (k) { return retraits[k] + ' × ' + LIBELLES_RETRAITS[k]; });
    return l.length ? l : null;
  }

  function telecharger(json, nom) {
    var blob = new Blob([json], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = el('a', { href: url, download: nom });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }

  // ---- page plein écran : chargement, puis réponse claire -----------------------
  var ecran = el('div', { id: 'ecran-envoi', classe: 'ecran-envoi', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'ecran-titre', hidden: 'hidden' });
  document.body.appendChild(ecran);
  var ETAPES_ENVOI = ['Adresse et proposition vérifiées', 'Envoi à l\'équipe de relecture', 'Réception confirmée'];

  function montrerEcran(etat, contenu) {
    ecran.className = 'ecran-envoi ecran-' + etat;
    ecran.textContent = '';
    ecran.appendChild(el('div', { classe: 'ecran-envoi-corps' }, contenu));
    ecran.hidden = false;
    document.body.style.overflow = 'hidden';
    ecran.scrollTop = 0;
    var t = trouver('ecran-titre'); if (t) { t.setAttribute('tabindex', '-1'); t.focus(); }
  }
  function fermerEcran() { ecran.hidden = true; ecran.textContent = ''; document.body.style.overflow = ''; }

  // n = nombre d'étapes terminées ; l'étape n est « en cours » (sauf en cas d'échec).
  function etapesEnvoi(n, echec) {
    var ol = el('ol', { classe: 'etapes-envoi' });
    ETAPES_ENVOI.forEach(function (texte, i) {
      var etat = i < n ? 'fait' : (i === n ? (echec ? 'rate' : 'en-cours') : 'a-venir');
      var signe = { fait: '✓', rate: '✕', 'en-cours': '', 'a-venir': String(i + 1) }[etat];
      var lu = { fait: ' : fait', rate : ' : échec', 'en-cours': ' : en cours', 'a-venir': ' : à venir' }[etat];
      ol.appendChild(el('li', { classe: etat }, [
        el('span', { classe: 'marque-etape', 'aria-hidden': 'true', texte: signe }),
        el('span', { texte: texte }),
        el('span', { classe: 'sr-only', texte: lu })
      ]));
    });
    return ol;
  }

  function surtitre() { return el('p', { classe: 'ecran-surtitre', texte: 'Bibliothèque IA Terre · Proposer un projet' }); }

  function ecranChargement() {
    montrerEcran('chargement', [
      surtitre(),
      el('h1', { id: 'ecran-titre', texte: 'Envoi en cours…' }),
      el('div', { classe: 'barre-envoi', role: 'progressbar', 'aria-label': 'Envoi en cours' }, [el('span')]),
      etapesEnvoi(1),
      el('p', { classe: 'ecran-texte', texte: totalPj() ? 'Ne fermez pas cette page. Envoi de ' + mo(totalPj()) + ' de pièces jointes : cela peut prendre une minute.' : 'Ne fermez pas cette page. Cela prend quelques secondes.' })
    ]);
  }

  function ecranSucces(titre) {
    try { localStorage.removeItem(CLE_BROUILLON); } catch (e) { /* ignoré */ }
    var accueil = el('a', { href: '../index.html', classe: 'bouton bouton-geant', texte: 'Retourner à l\'accueil' });
    var autre = el('button', { type: 'button', classe: 'bouton secondaire bouton-geant', texte: 'Proposer un autre projet' });
    autre.addEventListener('click', function () { reinitialiser(); fermerEcran(); window.scrollTo(0, 0); });
    montrerEcran('succes', [
      surtitre(),
      el('div', { classe: 'pastille pastille-ok', 'aria-hidden': 'true', texte: '✓' }),
      el('h1', { id: 'ecran-titre', texte: 'Proposition envoyée' }),
      el('p', { classe: 'ecran-gros', texte: '« ' + titre + ' » est bien arrivée. Merci !' }),
      el('div', { classe: 'actions-ecran' }, [accueil, autre]),
      el('p', { classe: 'ecran-texte', texte: 'Une personne de l\'équipe va la relire. Rien n\'est publié avant cette relecture. Vous n\'avez plus rien à faire.' }),
      etapesEnvoi(3)
    ]);
  }

  function ecranEchec(message, relancer, fichier) {
    var reessayer = el('button', { type: 'button', classe: 'bouton bouton-geant', texte: 'Réessayer' });
    reessayer.addEventListener('click', relancer);
    var tele = el('button', { type: 'button', classe: 'bouton secondaire bouton-geant', texte: 'Télécharger le fichier' });
    tele.addEventListener('click', fichier);
    var retour = el('button', { type: 'button', classe: 'bouton lien lien-geant', texte: 'Revenir à ma proposition' });
    retour.addEventListener('click', fermerEcran);
    montrerEcran('echec', [
      surtitre(),
      el('div', { classe: 'pastille pastille-ko', 'aria-hidden': 'true', texte: '!' }),
      el('h1', { id: 'ecran-titre', texte: 'L\'envoi n\'a pas abouti' }),
      el('p', { classe: 'ecran-gros', texte: 'Votre proposition n\'est pas considérée comme envoyée.' }),
      el('div', { classe: 'actions-ecran' }, [reessayer, tele]),
      el('p', { classe: 'ecran-texte', texte: message }),
      retour,
      etapesEnvoi(1, true)
    ]);
  }

  var DUREE_MIN_CHARGEMENT = 1500; // ms : la page de chargement reste lisible même si la réponse est immédiate

  // Appel à la boîte de dépôt, avec délai maximal. Renvoie la réponse JSON.
  function appeler(corps, delai) {
    return new Promise(function (ok, ko) {
      var fin = false;
      var t = setTimeout(function () { if (!fin) { fin = true; ko(new Error('delai')); } }, delai);
      fetch(D.boite, { method: 'POST', body: JSON.stringify(corps) })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (!fin) { fin = true; clearTimeout(t); ok(j); } })
        .catch(function (e) { if (!fin) { fin = true; clearTimeout(t); ko(e); } });
    });
  }

  function mo(octets) { return octets >= 1048576 ? (octets / 1048576).toFixed(1).replace('.', ',') + ' Mo' : Math.max(1, Math.round(octets / 1024)) + ' Ko'; }

  // ---- étape 1 : vérification de l'adresse de messagerie (code à 6 chiffres) ----------
  function ecranVerification(s, contact, json, nom, avis) {
    var domaines = (D.domaines || []).join(' ou ');
    var champAdresse = el('input', { type: 'email', id: 'adresse-verif', classe: 'saisie', autocomplete: 'email', placeholder: 'prenom.nom@intradef.gouv.fr', 'aria-describedby': 'verif-aide' });
    if (/^[^@\s]+@[^@\s]+$/.test(contact || '')) { champAdresse.value = contact; }
    var champCode = el('input', { type: 'text', id: 'code-verif', classe: 'saisie saisie-code', inputmode: 'numeric', autocomplete: 'one-time-code', maxlength: '8', placeholder: '000000', 'aria-label': 'Code à 6 chiffres reçu par courriel' });
    var message = el('p', { classe: 'verif-message', role: 'alert', hidden: 'hidden' });
    var etapeCode = el('div', { classe: 'verif-code', hidden: 'hidden' });
    var recevoir = el('button', { type: 'button', classe: 'bouton bouton-geant', texte: 'Recevoir mon code' });
    var valider = el('button', { type: 'button', classe: 'bouton bouton-geant', texte: 'Valider et envoyer' });
    var renvoyer = el('button', { type: 'button', classe: 'bouton lien', texte: 'Renvoyer un code' });
    var annuler = el('button', { type: 'button', classe: 'bouton lien lien-geant', texte: 'Annuler : revenir à ma proposition' });
    function dire(texte, genre) { message.textContent = texte; message.className = 'verif-message ' + (genre || 'erreur'); message.hidden = !texte; }

    function demander() {
      var a = champAdresse.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(a)) { dire('Saisissez une adresse de messagerie valide.'); champAdresse.focus(); return; }
      recevoir.disabled = true; renvoyer.disabled = true; dire('Envoi du code…', 'info');
      appeler({ action: 'code', adresse: a }, 30000).then(function (j) {
        recevoir.disabled = false;
        if (j && j.ok) {
          champAdresse.readOnly = true; recevoir.hidden = true; etapeCode.hidden = false;
          dire('Un code vient d\'être envoyé à ' + a + ' (regardez aussi les courriers indésirables). Il est valable 15 minutes.', 'info');
          champCode.focus();
          setTimeout(function () { renvoyer.disabled = false; }, 30000);
        } else { renvoyer.disabled = false; dire((j && j.erreur) || 'Le code n\'a pas pu être envoyé.'); }
      }).catch(function () { recevoir.disabled = false; renvoyer.disabled = false; dire('La demande n\'a pas pu être envoyée (réseau ou filtrage). Réessayez dans un moment.'); });
    }
    function confirmer() {
      var code = champCode.value.replace(/\s+/g, '');
      if (!/^\d{6}$/.test(code)) { dire('Le code comporte 6 chiffres.'); champCode.focus(); return; }
      valider.disabled = true; dire('Vérification…', 'info');
      appeler({ action: 'verifier', adresse: champAdresse.value.trim(), code: code }, 30000).then(function (j) {
        if (j && j.ok && j.jeton) { envoyer(s, contact, json, nom, champAdresse.value.trim(), j.jeton); }
        else { valider.disabled = false; dire((j && j.erreur) || 'Code refusé.'); champCode.select(); }
      }).catch(function () { valider.disabled = false; dire('La vérification n\'a pas pu aboutir (réseau ou filtrage). Réessayez.'); });
    }
    recevoir.addEventListener('click', demander);
    renvoyer.addEventListener('click', function () { champAdresse.readOnly = false; demander(); });
    valider.addEventListener('click', confirmer);
    champCode.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); confirmer(); } });
    champAdresse.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); if (!champAdresse.readOnly) { demander(); } } });
    annuler.addEventListener('click', fermerEcran);
    renvoyer.disabled = true;
    etapeCode.appendChild(el('label', { 'for': 'code-verif', classe: 'champ-titre', texte: 'Code reçu par courriel' }));
    etapeCode.appendChild(champCode);
    etapeCode.appendChild(el('div', { classe: 'actions-ecran' }, [valider]));
    etapeCode.appendChild(renvoyer);
    montrerEcran('verif', [
      surtitre(),
      el('h1', { id: 'ecran-titre', texte: 'Confirmez votre adresse' }),
      el('p', { classe: 'ecran-gros', texte: 'Les dépôts sont réservés à la communauté.' }),
      el('p', { classe: 'ecran-texte', id: 'verif-aide', texte: 'Saisissez votre adresse professionnelle (' + domaines + '). Nous vous envoyons un code à 6 chiffres : le dépôt n\'est envoyé qu\'une fois ce code saisi. Votre adresse n\'est jamais publiée.' }),
      avis ? el('p', { classe: 'verif-message erreur', role: 'alert', texte: avis }) : null,
      el('div', { classe: 'verif-formulaire' }, [
        el('label', { 'for': 'adresse-verif', classe: 'champ-titre', texte: 'Votre adresse de messagerie' }), champAdresse,
        recevoir, message, etapeCode
      ]),
      annuler
    ]);
    champAdresse.focus();
  }

  // ---- étape 2 : envoi du dépôt (avec l'adresse vérifiée et le jeton obtenu) ------------
  function envoyer(s, contact, json, nom, adresse, jeton) {
    ecranChargement();
    var debut = Date.now();
    var pj = piecesPourEnvoi();
    var termine = false;
    function apres(fn) { setTimeout(fn, Math.max(0, DUREE_MIN_CHARGEMENT - (Date.now() - debut))); }
    function echec(msg) {
      if (termine) { return; } termine = true;
      apres(function () { ecranEchec(msg, function () { envoyer(s, contact, json, nom, adresse, jeton); }, function () { telecharger(jsonComplet(s), nom); }); });
    }
    var corps = { adresse: adresse, jeton: jeton, p: pj.length ? Object.assign({}, s, { pieces_jointes: pj }) : s, contact: contact, piege: valeur('site-web') };
    var delai = 45000 + Math.ceil(totalPj() / 1048576) * 12000;   // plus de temps pour de gros fichiers
    appeler(corps, delai).then(function (j) {
      if (termine) { return; }
      if (j && j.ok) { termine = true; apres(function () { ecranSucces(s.titre); }); }
      else if (j && j.verification) { termine = true; apres(function () { ecranVerification(s, contact, json, nom, 'La vérification de votre adresse a expiré : recommencez-la (votre proposition est conservée).'); }); }
      else { echec((j && j.erreur ? j.erreur + ' ' : '') + 'Réessayez dans un moment, ou téléchargez le fichier. ' + D.contact); }
    }).catch(function (e) {
      echec(e && e.message === 'delai'
        ? 'La réponse met trop de temps à arriver. Réessayez, ou téléchargez le fichier pour l\'envoyer autrement. ' + D.contact
        : 'La réception n\'a pas pu être confirmée (réseau ou filtrage). Réessayez, ou téléchargez le fichier pour l\'envoyer autrement. ' + D.contact);
    });
  }

  function reinitialiser() {
    try { localStorage.removeItem(CLE_BROUILLON); } catch (e) { /* ignoré */ }
    formulaire.reset();
    contenuZone.value = '';
    PJ.length = 0; majListePj(); retourPj.hidden = true;
    etapesZone.textContent = '';
    ajouterEtape(); ajouterEtape();
    majContenu();
    erreursZone.hidden = true; resultat.hidden = true;
  }

  function montrerResultat(s, retraits, alertes, contact) {
    var affichage = PJ.length ? Object.assign({}, s, { pieces_jointes: PJ.map(function (x) { return { nom: nomPj(x.nom), taille: x.taille, sha256: x.sha256, contenu_b64: '(contenu du fichier, envoyé tel quel)' }; }) }) : s;
    var json = JSON.stringify(affichage, null, 2);
    var nom = nomFichier(s);
    resultat.textContent = '';
    resultat.appendChild(el('h2', { texte: 'Votre proposition est prête' }));
    resultat.appendChild(el('p', { texte: 'Rien n\'a encore été envoyé. Voici exactement ce qui partira si vous cliquez sur « Envoyer » :' }));
    resultat.appendChild(el('details', { classe: 'details-json' }, [el('summary', { texte: 'Voir le contenu du fichier' }), el('pre', { classe: 'bloc-code', texte: json })]));

    var r = phraseRetraits(retraits);
    if (r) {
      var ul = el('ul'); r.forEach(function (t) { ul.appendChild(el('li', { texte: t })); });
      resultat.appendChild(el('div', { classe: 'avis-regle' }, [el('p', { texte: 'Pour que le dépôt reste utilisable par tous, ces éléments ont été retirés automatiquement du fichier (votre brouillon, lui, n\'a pas été modifié) :' }), ul]));
    }
    alertes.forEach(function (t) { resultat.appendChild(el('p', { classe: 'avis-regle', texte: 'À savoir : ' + t })); });

    var actions = el('div', { classe: 'actions-form' });
    if (D.boite) {
      var envoi = el('button', { type: 'button', classe: 'bouton', texte: 'Envoyer ma proposition' });
      envoi.addEventListener('click', function () { ecranVerification(s, contact, json, nom); });
      actions.appendChild(envoi);
    }
    var tele = el('button', { type: 'button', classe: 'bouton secondaire', texte: 'Télécharger le fichier ' + nom });
    tele.addEventListener('click', function () { telecharger(jsonComplet(s), nom); });
    var copie = el('button', { type: 'button', classe: 'bouton secondaire', texte: 'Copier le contenu' });
    copie.addEventListener('click', function () { copier(PJ.length ? jsonComplet(s) : json, copie); });
    actions.appendChild(tele); actions.appendChild(copie);
    resultat.appendChild(actions);
    resultat.appendChild(el('p', { classe: 'champ-aide', texte: D.boite ? 'Si l\'envoi échoue : ' + D.contact : D.contact }));
    resultat.hidden = false;
    erreursZone.hidden = true;
    resultat.scrollIntoView({ block: 'start' });
  }

  formulaire.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var brut = etat();
    brut.etapes = brut.etapes.map(function (e, i) { e.n = i + 1; return e; }).filter(etapeRemplie);
    var problemes = verifierChamps(brut);
    if (problemes.length) { montrerErreurs(problemes); return; }
    brut.etapes.forEach(function (e) { delete e.n; });
    var contact = valeur('contact');
    var ep = Epurer.proposition(brut);
    montrerResultat(ep.proposition, ep.retraits, ep.alertes, contact);
  });

  formulaire.addEventListener('input', sauver);
  formulaire.addEventListener('change', function (ev) {
    if (ev.target.name === 'type') { majContenu(); }
    sauver();
  });
  trouver('effacer').addEventListener('click', function () {
    if (!window.confirm('Effacer tout ce que vous avez saisi ?')) { return; }
    reinitialiser();
  });

  // ---- dépôt d'un fichier (glisser-déposer ou bouton) ---------------------
  var EXT_TEXTE = ['md', 'markdown', 'txt', 'py', 'json', 'yaml', 'yml', 'csv'];
  var TAILLE_MAX = 150000;   // caractères : la boîte de dépôt refuse les dépôts de plus de 200 Ko
  var ancienContenu = null;

  function extension(nom) { var m = /\.([^.\/]+)$/.exec(nom || ''); return m ? m[1].toLowerCase() : ''; }
  function lireTexte(f) {
    return new Promise(function (ok, ko) {
      var r = new FileReader(); r.onload = function () { ok(String(r.result).replace(/^\uFEFF/, '')); }; r.onerror = ko; r.readAsText(f, 'utf-8');
    });
  }
  function lireOctets(f) {
    return new Promise(function (ok, ko) {
      var r = new FileReader(); r.onload = function () { ok(r.result); }; r.onerror = ko; r.readAsArrayBuffer(f);
    });
  }

  function message(lignes, genre, annulable) {
    retourFichier.textContent = '';
    retourFichier.className = 'retour-fichier ' + (genre || 'ok');
    lignes.forEach(function (l) { if (l) { retourFichier.appendChild(el('p', { texte: l })); } });
    if (annulable) {
      var b = el('button', { type: 'button', classe: 'bouton lien', texte: 'Annuler : remettre le texte précédent' });
      b.addEventListener('click', function () {
        contenuZone.value = ancienContenu || ''; ancienContenu = null; sauver();
        message(['Le texte précédent est revenu.'], 'ok', false);
      });
      retourFichier.appendChild(b);
    }
    retourFichier.hidden = false;
  }

  function choisirType(t) {
    if (!t || typeChoisi() === t) { return false; }
    var r = formulaire.querySelector('input[name=type][value="' + t + '"]');
    if (!r) { return false; }
    r.checked = true; majContenu(); return true;
  }

  function placer(texte, nom, type, avertissement) {
    if (!texte.trim()) { message(['« ' + nom + ' » est vide : rien n\'a été chargé.'], 'erreur'); return; }
    if (texte.length > TAILLE_MAX) {
      message(['« ' + nom + ' » est trop long (' + texte.length + ' caractères, ' + TAILLE_MAX + ' au maximum). Raccourcissez-le, ou gardez l\'essentiel et signalez le reste dans le résumé.'], 'erreur');
      return;
    }
    var remplace = contenuZone.value.trim() !== '' && contenuZone.value !== texte;
    ancienContenu = remplace ? contenuZone.value : null;
    contenuZone.value = texte;
    var change = choisirType(type);
    sauver();
    message([
      '« ' + nom + ' » est chargé dans le champ ci-dessous (' + texte.length + ' caractères). Relisez-le : c\'est ce texte qui sera envoyé.',
      change ? 'Le type de projet a été réglé sur « ' + V.type[type] + ' ».' : '',
      avertissement || ''
    ], avertissement ? 'attention' : 'ok', remplace);
  }

  // Lecture d'un .zip : on n'en garde que SKILL.md (le formulaire n'envoie que du texte).
  function lireZip(f) {
    if (typeof DecompressionStream === 'undefined') {
      message(['Ce navigateur ne sait pas ouvrir les fichiers .zip. Ouvrez le .zip sur votre ordinateur, puis glissez ici le fichier SKILL.md qu\'il contient.'], 'erreur');
      return;
    }
    lireOctets(f).then(function (tampon) {
      var v = new DataView(tampon), n = tampon.byteLength, fin = -1;
      for (var i = n - 22; i >= Math.max(0, n - 65557); i--) { if (v.getUint32(i, true) === 0x06054b50) { fin = i; break; } }
      if (fin < 0) { throw new Error('zip'); }
      var nb = v.getUint16(fin + 10, true), pos = v.getUint32(fin + 16, true), entrees = [];
      var dec = new TextDecoder('utf-8');
      for (var k = 0; k < nb; k++) {
        if (v.getUint32(pos, true) !== 0x02014b50) { throw new Error('zip'); }
        var lNom = v.getUint16(pos + 28, true), lExtra = v.getUint16(pos + 30, true), lCom = v.getUint16(pos + 32, true);
        entrees.push({
          nom: dec.decode(new Uint8Array(tampon, pos + 46, lNom)), drapeaux: v.getUint16(pos + 8, true),
          methode: v.getUint16(pos + 10, true), taille: v.getUint32(pos + 20, true), brut: v.getUint32(pos + 24, true),
          local: v.getUint32(pos + 42, true)
        });
        pos += 46 + lNom + lExtra + lCom;
      }
      var fichiers = entrees.filter(function (e) { return !/\/$/.test(e.nom) && !/(^|\/)(__MACOSX\/|\.DS_Store$)/.test(e.nom); });
      var skills = fichiers.filter(function (e) { return /(^|\/)SKILL\.md$/i.test(e.nom); })
        .sort(function (a, b) { return a.nom.split('/').length - b.nom.split('/').length; });
      if (!skills.length) {
        message(['Ce .zip ne contient pas de fichier SKILL.md. Glissez plutôt le fichier texte de votre prompt, de vos instructions ou de votre script.'], 'erreur');
        return null;
      }
      var s = skills[0];
      if (s.drapeaux & 1) { message(['Ce .zip est protégé par un mot de passe : il ne peut pas être lu.'], 'erreur'); return null; }
      if (s.brut > TAILLE_MAX) { message(['Le SKILL.md de ce .zip est trop long (' + s.brut + ' octets, ' + TAILLE_MAX + ' au maximum).'], 'erreur'); return null; }
      var debut = s.local + 30 + v.getUint16(s.local + 26, true) + v.getUint16(s.local + 28, true);
      var octets = new Uint8Array(tampon, debut, s.taille);
      var lecture;
      if (s.methode === 0) { lecture = Promise.resolve(octets); }
      else if (s.methode === 8) {
        lecture = new Response(new Blob([octets]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer()
          .then(function (b) { return new Uint8Array(b); });
      } else { throw new Error('zip'); }
      var autres = fichiers.filter(function (e) { return e !== s; }).map(function (e) { return e.nom.split('/').pop(); });
      return lecture.then(function (o) {
        var texte = dec.decode(o).replace(/^\uFEFF/, '');
        var avert = autres.length
          ? 'Ce skill contient aussi ' + autres.length + ' autre' + (autres.length > 1 ? 's fichiers' : ' fichier') + ' (' + autres.slice(0, 5).join(', ') + (autres.length > 5 ? '…' : '') +
            ') : le formulaire n\'envoie que SKILL.md. Indiquez-le dans le résumé et laissez une adresse de contact (partie 7) : la personne qui relit vous demandera le reste.'
          : '';
        placer(texte, s.nom.split('/').pop() + ' (extrait de ' + f.name + ')', 'skill', avert);
      });
    }).catch(function () {
      message(['Ce .zip n\'a pas pu être lu. Ouvrez-le sur votre ordinateur, puis glissez ici le fichier SKILL.md qu\'il contient.'], 'erreur');
    });
  }

  function lireFichier(f) {
    if (!f) { return; }
    var ext = extension(f.name);
    if (ext === 'zip') { lireZip(f); return; }
    if (PJ_EXT.indexOf(ext) >= 0) {
      ajouterPj([f]);
      message(['« ' + f.name + ' » est un document : il a été ajouté aux pièces jointes (plus bas). Pour le contenu du projet, collez le texte ou glissez un fichier .md, .txt, .py ou SKILL.md.'], 'attention');
      return;
    }
    if (EXT_TEXTE.indexOf(ext) < 0 && !/^text\//.test(f.type || '')) {
      message(['Les fichiers .' + (ext || '?') + ' ne peuvent pas être lus ici. Pour un document Word, Excel, PowerPoint ou PDF, utilisez le cadre « Pièces jointes » plus bas ; sinon copiez-collez son texte dans le champ ci-dessous.'], 'erreur');
      return;
    }
    if (f.size > TAILLE_MAX * 4) { message(['« ' + f.name + ' » est trop lourd pour le formulaire.'], 'erreur'); return; }
    lireTexte(f).then(function (texte) {
      var type = ext === 'py' ? 'script' : (/^SKILL\.md$/i.test(f.name) ? 'skill' : '');
      placer(texte, f.name, type, '');
    }).catch(function () { message(['« ' + f.name + ' » n\'a pas pu être lu.'], 'erreur'); });
  }

  function aDesFichiers(ev) {
    var types = ev.dataTransfer && ev.dataTransfer.types;
    return !!types && Array.prototype.indexOf.call(types, 'Files') >= 0;
  }
  [depot, contenuZone].forEach(function (cible) {
    cible.addEventListener('dragover', function (ev) {
      if (!aDesFichiers(ev)) { return; }
      ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; depot.classList.add('survol');
    });
    cible.addEventListener('dragleave', function () { depot.classList.remove('survol'); });
    cible.addEventListener('drop', function (ev) {
      if (!aDesFichiers(ev)) { return; }
      ev.preventDefault(); ev.stopPropagation(); depot.classList.remove('survol');
      var fs = ev.dataTransfer.files;
      if (fs.length > 1) { message(['Un seul fichier à la fois : seul « ' + fs[0].name + ' » a été pris.'], 'attention'); }
      lireFichier(fs[0]);
    });
  });
  // Un fichier lâché à côté de la zone ne doit pas faire quitter la page (le navigateur l'ouvrirait).
  window.addEventListener('dragover', function (ev) { if (aDesFichiers(ev)) { ev.preventDefault(); } });
  window.addEventListener('drop', function (ev) {
    if (!aDesFichiers(ev)) { return; }
    ev.preventDefault();
    message(['Lâchez le fichier dans le cadre « Glissez ici votre fichier », dans la partie 2.'], 'attention');
    depot.scrollIntoView({ block: 'center' });
  });
  boutonFichier.addEventListener('click', function () { choixFichier.click(); });
  choixFichier.addEventListener('change', function () { lireFichier(choixFichier.files[0]); choixFichier.value = ''; });


  // ---- pièces jointes ----------------------------------------------------------------
  var PJ_EXT = ['docx', 'xlsx', 'pptx', 'pdf'];
  var PJ_ANCIENS = { doc: 'Word', xls: 'Excel', ppt: 'PowerPoint', dot: 'Word', xlt: 'Excel', pps: 'PowerPoint' };
  var PJ_MACROS = ['docm', 'xlsm', 'pptm', 'dotm', 'xltm', 'potm', 'ppsm', 'xlam', 'ppam', 'sldm'];
  var PJ_MAX_TOTAL = 15 * 1024 * 1024, PJ_MAX_NB = 10;
  var PJ = [];   // { nom, taille, octets (ArrayBuffer), sha256 }

  function totalPj() { return PJ.reduce(function (t, x) { return t + x.taille; }, 0); }
  function nomPj(n) {
    var m = /^(.*?)(\.[A-Za-z0-9]+)$/.exec(n);
    return (m ? Epurer.texte(m[1]).texte + m[2] : Epurer.texte(n).texte).slice(0, 120);
  }
  function enBase64(tampon) {
    var o = new Uint8Array(tampon), morceaux = [];
    for (var i = 0; i < o.length; i += 0x8000) { morceaux.push(String.fromCharCode.apply(null, o.subarray(i, i + 0x8000))); }
    return btoa(morceaux.join(''));
  }
  function piecesPourEnvoi() {
    return PJ.map(function (x) { return { nom: nomPj(x.nom), taille: x.taille, sha256: x.sha256, contenu_b64: enBase64(x.octets) }; });
  }
  function jsonComplet(s) {
    return JSON.stringify(PJ.length ? Object.assign({}, s, { pieces_jointes: piecesPourEnvoi() }) : s, null, 2);
  }
  function hexa(tampon) { return Array.prototype.map.call(new Uint8Array(tampon), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }

  // Premier contrôle, dans le navigateur : rapide, pour éviter d'attendre un refus. Le vrai contrôle est fait à la réception et à la validation.
  function controlePj(nom, tampon) {
    var ext = extension(nom), o = new Uint8Array(tampon);
    if (PJ_ANCIENS[ext]) { return 'ancien format ' + PJ_ANCIENS[ext] + ' : il ne peut pas être contrôlé. Ouvrez-le, puis « Enregistrer sous » au format ' + { Word: '.docx', Excel: '.xlsx', PowerPoint: '.pptx' }[PJ_ANCIENS[ext]] + '.'; }
    if (PJ_MACROS.indexOf(ext) >= 0) { return 'format à macros : refusé. Enregistrez-le sans macros.'; }
    if (PJ_EXT.indexOf(ext) < 0) { return 'type non accepté (.' + (ext || '?') + '). Acceptés : .docx, .xlsx, .pptx, .pdf.'; }
    if (!o.length) { return 'fichier vide.'; }
    var brut = new TextDecoder('latin1').decode(o);
    if (ext === 'pdf') {
      if (brut.slice(0, 1024).indexOf('%PDF-') < 0) { return 'ce n\'est pas un vrai PDF.'; }
      if (/\/(JavaScript|JS|Launch|EmbeddedFiles?|RichMedia|XFA)\b/.test(brut)) { return 'ce PDF contient un élément actif (JavaScript, fichier incorporé…) : refusé.'; }
      if (/\/Encrypt\b/.test(brut)) { return 'PDF protégé par mot de passe : il ne peut pas être contrôlé.'; }
      return null;
    }
    if (o[0] === 0xD0 && o[1] === 0xCF) { return 'ancien format Office sous une extension récente : refusé.'; }
    if (o[0] !== 0x50 || o[1] !== 0x4B) { return 'ce n\'est pas un vrai document ' + ext.toUpperCase() + '.'; }
    if (/vbaProject|macrosheets\/|activeX\/|\/embeddings\/|customUI\//i.test(brut)) { return 'ce document contient des macros ou des objets incorporés : refusé.'; }
    return null;
  }

  function messagePj(lignes, genre) {
    retourPj.textContent = '';
    retourPj.className = 'retour-fichier ' + (genre || 'ok');
    lignes.forEach(function (l) { if (l) { retourPj.appendChild(el('p', { texte: l })); } });
    retourPj.hidden = !lignes.length;
  }
  function majListePj() {
    listePj.textContent = '';
    PJ.forEach(function (x, i) {
      var retirer = el('button', { type: 'button', classe: 'bouton lien', texte: 'Retirer', 'aria-label': 'Retirer ' + x.nom });
      retirer.addEventListener('click', function () { PJ.splice(i, 1); majListePj(); messagePj(['« ' + x.nom + ' » a été retiré.'], 'ok'); });
      listePj.appendChild(el('li', {}, [el('span', { classe: 'pj-nom', texte: x.nom }), el('span', { classe: 'pj-taille', texte: mo(x.taille) }), retirer]));
    });
    if (PJ.length) { listePj.appendChild(el('li', { classe: 'pj-total' }, [el('span', { texte: PJ.length + ' fichier' + (PJ.length > 1 ? 's' : '') + ' · ' + mo(totalPj()) + ' sur 15 Mo' })])); }
    listePj.hidden = !PJ.length;
  }
  function ajouterPj(fichiers) {
    var liste = Array.prototype.slice.call(fichiers), refus = [], ajoutes = [], suite = Promise.resolve();
    liste.forEach(function (f) {
      suite = suite.then(function () {
        if (PJ.length >= PJ_MAX_NB) { refus.push('« ' + f.name + ' » : 10 fichiers au maximum.'); return; }
        if (totalPj() + f.size > PJ_MAX_TOTAL) { refus.push('« ' + f.name + ' » : il dépasserait 15 Mo au total.'); return; }
        return lireOctets(f).then(function (tampon) {
          var motif = controlePj(f.name, tampon);
          if (motif) { refus.push('« ' + f.name + ' » : ' + motif); return; }
          if (!(window.crypto && window.crypto.subtle)) { refus.push('« ' + f.name + ' » : ce navigateur ne permet pas de contrôler l\'intégrité du fichier. Utilisez une version récente de Chrome, Edge ou Firefox.'); return; }
          return crypto.subtle.digest('SHA-256', tampon).then(function (h) {
            var nom = f.name, n = 2;
            while (PJ.some(function (x) { return x.nom.toLowerCase() === nom.toLowerCase(); })) { nom = f.name.replace(/(\.[^.]+)$/, ' (' + n++ + ')$1'); }
            PJ.push({ nom: nom, taille: tampon.byteLength, octets: tampon, sha256: hexa(h) });
            ajoutes.push(nom);
          });
        });
      }).catch(function () { refus.push('« ' + f.name + ' » n\'a pas pu être lu.'); });
    });
    suite.then(function () {
      majListePj();
      var lignes = [];
      if (ajoutes.length) { lignes.push(ajoutes.length + ' pièce' + (ajoutes.length > 1 ? 's jointes ajoutées' : ' jointe ajoutée') + '. Elles seront contrôlées à nouveau avant toute publication.'); }
      messagePj(lignes.concat(refus), refus.length ? (ajoutes.length ? 'attention' : 'erreur') : 'ok');
    });
  }
  [depotPj].forEach(function (cible) {
    cible.addEventListener('dragover', function (ev) { if (!aDesFichiers(ev)) { return; } ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; cible.classList.add('survol'); });
    cible.addEventListener('dragleave', function () { cible.classList.remove('survol'); });
    cible.addEventListener('drop', function (ev) {
      if (!aDesFichiers(ev)) { return; }
      ev.preventDefault(); ev.stopPropagation(); cible.classList.remove('survol');
      ajouterPj(ev.dataTransfer.files);
    });
  });
  boutonPj.addEventListener('click', function () { choixPj.click(); });
  choixPj.addEventListener('change', function () { ajouterPj(choixPj.files); choixPj.value = ''; });

  // ---- démarrage -------------------------------------------------------
  if (!restaurer()) { ajouterEtape(); ajouterEtape(); }
  majContenu();
})();
