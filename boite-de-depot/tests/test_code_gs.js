// Test local de Code.gs : les services Google sont simulés. Lancer : node boite-de-depot/tests/test_code_gs.js
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { monde } = require('./monde_gs');

let echecs = 0;
const ok = (nom, c, d) => { console.log((c ? '  ok   ' : '  ECHEC ') + nom + (!c && d !== undefined ? ' -> ' + JSON.stringify(d).slice(0, 300) : '')); if (!c) echecs++; };
const codeDuMail = m => /: (\d{6})\n/.exec(m.subject + '\n')[1];
const FORMAT = 'bibliotheque-ia-terre/proposition';
const depot = (extra) => Object.assign({ format: FORMAT, titre: 'Fiche test', resume: 'r', type: 'skill', auteur: 'Pseudo', contenu: 'x', ia_compatibles: ['claude'], controles: [] }, extra || {});
const pj = (nom, buf) => ({ nom, sha256: crypto.createHash('sha256').update(buf).digest('hex'), contenu_b64: buf.toString('base64') });
const PROPS = () => ({ DOSSIER_ID: 'd', VALIDATEURS: 'val1@gmail.com, Val2@gmail.com', EXEMPTES: 'test@gmail.com' });

console.log('Adresses');
let w = monde(PROPS());
ok('domaine exact intradef accepté', w.post({ action: 'code', adresse: 'prenom.nom@intradef.gouv.fr' }).ok === true);
ok('un code a été envoyé à l\'adresse', w.mails.length === 1 && w.mails[0].to === 'prenom.nom@intradef.gouv.fr' && /^\d{6}$/.test(codeDuMail(w.mails[0])), w.mails);
ok('academie.def.gouv.fr accepté', w.post({ action: 'code', adresse: 'a@academie.def.gouv.fr' }).ok === true);
for (const a of ['x@gmail.com', 'x@evil.intradef.gouv.fr', 'x@evil.academie.def.gouv.fr', 'x@academs.fr', 'x@academie.def.gouv.fr.evil.com', 'x@xacademie.def.gouv.fr', 'x@intradef.gouv.fr.evil.com', 'x@xintradef.gouv.fr', 'x@def.gouv.fr', 'a@intradef.gouv.fr,b@gmail.com', 'a@intradef.gouv.fr\nbcc:b@x.fr', 'x@INTRADEF.GOUV.FR.', '', 'pas une adresse'])
  { const n = w.mails.length; const r = w.post({ action: 'code', adresse: a }); ok('refusé : ' + JSON.stringify(a), r.ok === false && w.mails.length === n, r); }
ok('adresse perso sans adresse sécurisée : demande l\'adresse sécurisée, aucun mail', (() => { const x = monde(PROPS()); const r = x.post({ action: 'code', adresse: 'perso@gmail.com' }); return r.ok === false && r.besoin_securisee === true && x.mails.length === 0; })());
ok('majuscules acceptées (normalisées)', monde(PROPS()).post({ action: 'code', adresse: 'A.B@INTRADEF.GOUV.FR' }).ok === true);
ok('validateur dispensé de la règle de domaine', monde(PROPS()).post({ action: 'code', adresse: 'val2@gmail.com' }).ok === true);
ok('adresse EXEMPTES dispensée', monde(PROPS()).post({ action: 'code', adresse: 'test@gmail.com' }).ok === true);

console.log('Adresse personnelle enrôlée via une adresse sécurisée');
const P = 'perso.test@gmail.com', S = 'prenom.nom@intradef.gouv.fr';
w = monde(PROPS());
for (const sec of ['x@gmail.com', 'x@academs.fr', 'x@evil.intradef.gouv.fr', 'x@intradef.gouv.fr.evil.com', 'pas une adresse']) {
  const n = w.mails.length; const r = w.post({ action: 'code', adresse: P, securisee: sec }); ok('adresse sécurisée refusée : ' + sec, r.ok === false && r.besoin_securisee === true && w.mails.length === n, r);
}
let r1 = w.post({ action: 'code', adresse: P, securisee: S });
ok('1re fois : le code part vers l\'adresse sécurisée', r1.ok === true && r1.envoye_a === 'securisee' && w.mails.length === 1 && w.mails[0].to === S, [r1, w.mails]);
ok('le courriel nomme l\'adresse perso, la réponse la masque', w.mails[0].body.includes(P) && r1.masque === 'p***@intradef.gouv.fr' && JSON.stringify(r1).indexOf(S) < 0, r1);
const cE = codeDuMail(w.mails[0]);
ok('rien n\'est enrôlé avant la saisie du code', w.post({ action: 'code', adresse: P }).besoin_securisee === true && w.mails.length === 1);
w.post({ action: 'code', adresse: P, securisee: S }); const cE2 = codeDuMail(w.mails[w.mails.length - 1]);
ok('le code ne valide pas une autre adresse perso', w.post({ action: 'verifier', adresse: 'autre@gmail.com', code: cE2 }).ok === false);
const vE = w.post({ action: 'verifier', adresse: P, code: cE2 });
ok('bon code : jeton rendu pour l\'adresse perso', vE.ok === true && vE.jeton, vE);
const n0 = w.mails.length;
let rS = w.post({ action: 'code', adresse: P });
ok('adresses suivantes : code envoyé directement à l\'adresse perso', rS.ok === true && rS.envoye_a === 'adresse' && w.mails.length === n0 + 1 && w.mails[n0].to === P, [rS, w.mails[n0]]);
ok('empreinte seulement dans les propriétés (pas d\'adresse perso en clair)', !Object.keys(w.props).some(k => k.indexOf(P) >= 0) && !Object.values(w.props).some(v => String(v).indexOf(P) >= 0));
let tD = (() => { const c = codeDuMail(w.mails[n0]); return w.post({ action: 'verifier', adresse: P, code: c }).jeton; })();
let rD = w.post({ adresse: P, jeton: tD, p: depot() });
ok('dépôt accepté avec l\'adresse perso', rD.ok === true, rD);
let fD = JSON.parse(w.fichiers[0].c);
ok('reception et mail validateurs : les deux adresses', fD.reception.adresse_verifiee === P && fD.reception.adresse_securisee === S && w.mails[w.mails.length - 1].body.includes(P) && w.mails[w.mails.length - 1].body.includes(S), fD.reception);
ok('jeton de l\'adresse perso inutilisable pour une autre adresse', (() => { const x = monde(PROPS()); x.post({ action: 'code', adresse: P, securisee: S }); const cc = codeDuMail(x.mails[0]); const tt = x.post({ action: 'verifier', adresse: P, code: cc }).jeton; return x.post({ adresse: S, jeton: tt, p: depot() }).ok === false && x.post({ adresse: 'val1@gmail.com', jeton: tt, p: depot() }).ok === false; })());
ok('enrôlement expiré après un an : adresse sécurisée redemandée', (() => { const x = monde(PROPS()); x.post({ action: 'code', adresse: P, securisee: S }); x.post({ action: 'verifier', adresse: P, code: codeDuMail(x.mails[0]) }); x.horloge.t += 366 * 86400000; return x.post({ action: 'code', adresse: P }).besoin_securisee === true; })());
ok('l\'usage renouvelle l\'enrôlement', (() => { const x = monde(PROPS()); x.post({ action: 'code', adresse: P, securisee: S }); x.post({ action: 'verifier', adresse: P, code: codeDuMail(x.mails[0]) }); x.horloge.t += 300 * 86400000; x.post({ action: 'code', adresse: P }); x.post({ action: 'verifier', adresse: P, code: codeDuMail(x.mails[x.mails.length - 1]) }); x.horloge.t += 300 * 86400000; return x.post({ action: 'code', adresse: P }).ok === true; })());
ok('révocation : l\'adresse doit se ré-enrôler', (() => { const x = monde(PROPS()); x.post({ action: 'code', adresse: P, securisee: S }); x.post({ action: 'verifier', adresse: P, code: codeDuMail(x.mails[0]) }); x.props.REVOQUER = P; x.revoquer(); return x.post({ action: 'code', adresse: P }).besoin_securisee === true && !x.props.REVOQUER; })());
ok('adresse sécurisée ignorée si l\'adresse est déjà sécurisée', (() => { const x = monde(PROPS()); const r = x.post({ action: 'code', adresse: 'a@intradef.gouv.fr', securisee: 'b@intradef.gouv.fr' }); return r.ok === true && x.mails[0].to === 'a@intradef.gouv.fr'; })());
ok('quotas : 4e code pour la même adresse perso refusé même avec d\'autres adresses sécurisées', (() => { const x = monde(PROPS()); for (let i = 0; i < 3; i++) x.post({ action: 'code', adresse: P, securisee: 's' + i + '@intradef.gouv.fr' }); return x.post({ action: 'code', adresse: P, securisee: 's9@intradef.gouv.fr' }).ok === false; })());
ok('plafond par adresse sécurisée (pas de bombardement d\'une boîte)', (() => { const x = monde(PROPS()); for (let i = 0; i < 3; i++) x.post({ action: 'code', adresse: 'p' + i + '@gmail.com', securisee: S }); return x.post({ action: 'code', adresse: 'p9@gmail.com', securisee: S }).ok === false; })());

console.log('Code et jeton');
w = monde(PROPS());
const A = 'test@gmail.com';
w.post({ action: 'code', adresse: A });
const code = codeDuMail(w.mails[0]);
ok('mauvais code refusé', w.post({ action: 'verifier', adresse: A, code: code === '000000' ? '111111' : '000000' }).ok === false);
const v = w.post({ action: 'verifier', adresse: A, code });
ok('bon code accepté, jeton rendu', v.ok === true && v.jeton && v.jeton.length >= 64, v);
ok('code à usage unique', w.post({ action: 'verifier', adresse: A, code }).ok === false);
ok('le code n\'est pas dans la réponse de la demande', JSON.stringify(monde(PROPS()).post({ action: 'code', adresse: A })).indexOf('"code"') < 0);
w = monde(PROPS()); w.post({ action: 'code', adresse: A }); const c2 = codeDuMail(w.mails[0]);
let bloque = false; for (let i = 0; i < 6; i++) { w.post({ action: 'verifier', adresse: A, code: '999999' === c2 ? '888888' : '999999' }); }
ok('5 essais faux : le bon code ne marche plus', w.post({ action: 'verifier', adresse: A, code: c2 }).ok === false);
w = monde(PROPS()); w.post({ action: 'code', adresse: A }); const c3 = codeDuMail(w.mails[0]); w.horloge.t += 16 * 60 * 1000;
ok('code expiré après 15 min', w.post({ action: 'verifier', adresse: A, code: c3 }).ok === false);
w = monde(PROPS()); w.post({ action: 'code', adresse: A }); w.post({ action: 'code', adresse: A }); w.post({ action: 'code', adresse: A });
ok('4e code en une heure refusé', w.post({ action: 'code', adresse: A }).ok === false);
ok('code d\'une autre adresse inutilisable', (() => { const x = monde(PROPS()); x.post({ action: 'code', adresse: 'a@intradef.gouv.fr' }); const cc = codeDuMail(x.mails[0]); return x.post({ action: 'verifier', adresse: 'b@intradef.gouv.fr', code: cc }).ok === false; })());
w = monde(PROPS()); for (let i = 0; i < 40; i++) w.post({ action: 'code', adresse: `u${i}@intradef.gouv.fr` });
ok('plafond global de codes par heure', w.mails.length === 40 && w.post({ action: 'code', adresse: 'z@intradef.gouv.fr' }).ok === false);

console.log('Dépôt');
function jeton(w, a) { w.post({ action: 'code', adresse: a }); const c = codeDuMail(w.mails[w.mails.length - 1]); return w.post({ action: 'verifier', adresse: a, code: c }).jeton; }
w = monde(PROPS());
ok('dépôt sans jeton refusé', w.post({ adresse: A, p: depot() }).ok === false && w.fichiers.length === 0);
ok('faux jeton refusé', w.post({ adresse: A, jeton: 'x'.repeat(72), p: depot() }).ok === false);
let t = jeton(w, A); const avant = w.mails.length;
ok('jeton d\'une autre adresse refusé', w.post({ adresse: 'val1@gmail.com', jeton: t, p: depot() }).ok === false);
let r = w.post({ adresse: A, jeton: t, p: depot({ resume: 'Contact Jean Dupont 06 12 34 56 78' }) });
ok('dépôt accepté avec jeton', r.ok === true && r.prevenu === true, r);
ok('un fichier enregistré', w.fichiers.length === 1);
const m = w.mails[w.mails.length - 1];
ok('mail aux deux validateurs (en minuscules)', m.to === 'val1@gmail.com,val2@gmail.com', m.to);
ok('adresse vérifiée indiquée au validateur et dans reception', m.body.includes(A) && JSON.parse(w.fichiers[0].c).reception.adresse_verifiee === A);
ok('texte épuré', !w.fichiers[0].c.includes('Jean Dupont') && !w.fichiers[0].c.includes('06 12 34'));
ok('jeton à usage unique', w.post({ adresse: A, jeton: t, p: depot() }).ok === false);
ok('piège (honeypot) : fait semblant sans rien enregistrer', (() => { const n = w.fichiers.length; const x = w.post({ piege: 'x', p: depot() }); return x.ok === true && w.fichiers.length === n; })());

console.log('Pièces jointes');
const zip = Buffer.concat([Buffer.from('PK\x03\x04'), crypto.randomBytes(5000)]);
const pdf = Buffer.concat([Buffer.from('%PDF-1.4\n'), crypto.randomBytes(5000)]);
w = monde(PROPS()); t = jeton(w, A);
r = w.post({ adresse: A, jeton: t, p: depot({ pieces_jointes: [pj('note.docx', zip), pj('fiche.pdf', pdf)] }) });
ok('dépôt avec 2 pièces jointes accepté', r.ok === true, r);
let f = JSON.parse(w.fichiers[0].c);
ok('pièces jointes intactes (octets identiques)', f.pieces_jointes.length === 2 && Buffer.from(f.pieces_jointes[0].contenu_b64, 'base64').equals(zip) && Buffer.from(f.pieces_jointes[1].contenu_b64, 'base64').equals(pdf));
ok('mail : pièces jointes listées', /Pièces jointes \(2/.test(w.mails[w.mails.length - 1].body));
// base64 contenant des suites de chiffres qui ressembleraient à un téléphone : ne doit pas être touché
const piege = Buffer.from('PK\x03\x04' + '0612345678 06 12 34 56 78 192.168.1.1 sk-abcdefghijklmnopqrstuvwxyz'.repeat(3));
w = monde(PROPS()); t = jeton(w, A);
w.post({ adresse: A, jeton: t, p: depot({ pieces_jointes: [pj('a.docx', piege)] }) });
ok('épuration de texte ne touche pas aux pièces jointes', Buffer.from(JSON.parse(w.fichiers[0].c).pieces_jointes[0].contenu_b64, 'base64').equals(piege));
w = monde(PROPS());
const essais = [
  ['extension .exe', [pj('a.exe', zip)]], ['extension .docm', [pj('a.docm', zip)]], ['ancien format .doc', [pj('a.doc', zip)]],
  ['contenu qui ne correspond pas', [pj('a.pdf', zip)]], ['contenu qui ne correspond pas (docx)', [pj('a.docx', pdf)]],
  ['11 pièces jointes', Array.from({ length: 11 }, (_, i) => pj('f' + i + '.pdf', pdf))],
  ['empreinte fausse', [Object.assign(pj('a.pdf', pdf), { sha256: '0'.repeat(64) })]],
  ['base64 invalide', [{ nom: 'a.pdf', sha256: 'x', contenu_b64: '@@@@' }]],
  ['plus de 15 Mo', [pj('a.pdf', Buffer.concat([Buffer.from('%PDF-'), Buffer.alloc(16 * 1024 * 1024)]))]],
];
for (const [nom, liste] of essais) { const tt = jeton(w, A); const n = w.fichiers.length; const x = w.post({ adresse: A, jeton: tt, p: depot({ pieces_jointes: liste }) }); ok('refusé : ' + nom, x.ok === false && w.fichiers.length === n, x); }
ok('15 Mo juste acceptés', (() => { const gros = Buffer.concat([Buffer.from('%PDF-'), crypto.randomBytes(14 * 1024 * 1024)]); const x = monde(PROPS()); const tt = jeton(x, A); const rr = x.post({ adresse: A, jeton: tt, p: depot({ pieces_jointes: [pj('g.pdf', gros)] }) }); return rr.ok === true; })());
ok('nom de fichier épuré (nom de personne)', (() => { const x = monde(PROPS()); const tt = jeton(x, A); x.post({ adresse: A, jeton: tt, p: depot({ pieces_jointes: [pj('CV Jean Dupont.pdf', pdf)] }) }); return !x.fichiers[0].c.includes('Jean Dupont'); })());
ok('plafond de dépôts par adresse et par jour', (() => { const x = monde(PROPS()); x.horloge.t = Date.UTC(2026, 10, 5, 1, 0, 0); let der; for (let i = 0; i < 7; i++) { const tt = jeton(x, A); der = x.post({ adresse: A, jeton: tt, p: depot() }); x.horloge.t += 61 * 60 * 1000; if (i < 6 && !der.ok) return false; } return der.ok === false; })());
ok('jeton expiré après 30 min', (() => { const x = monde(PROPS()); const tt = jeton(x, A); x.horloge.t += 31 * 60 * 1000; return x.post({ adresse: A, jeton: tt, p: depot() }).ok === false; })());
ok('requête trop grosse refusée', monde(PROPS()).post('x'.repeat(23 * 1024 * 1024)).ok === false);
ok('JSON illisible refusé', monde(PROPS()).post('{pas du json').ok === false);

console.log(echecs ? '\n' + echecs + ' ECHEC(S)' : '\nTous les tests passent.');
process.exit(echecs ? 1 : 0);
