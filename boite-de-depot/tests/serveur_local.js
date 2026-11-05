// Serveur de test : exécute Code.gs (services Google simulés) sur http://127.0.0.1:PORT
// POST /boite = la boîte de dépôt ; GET /_etat = courriels et fichiers reçus. Lancer : node serveur_local.js [port]
const http = require('http');
const { monde } = require('./monde_gs');
const w = monde({ DOSSIER_ID: 'd', VALIDATEURS: 'validateur@example.org', EXEMPTES: 'adrian.test@gmail.com' });
const port = +process.argv[2] || 8765;
http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'GET' && req.url === '/_etat') {
    res.setHeader('Content-Type', 'application/json');
    return res.end(JSON.stringify({ mails: w.mails.map(m => ({ to: m.to, subject: m.subject, body: m.body, pj: (m.attachments || []).map(a => a.n) })), fichiers: w.fichiers }));
  }
  if (req.method === 'POST' && req.url === '/boite') {
    const morceaux = []; req.on('data', c => morceaux.push(c));
    req.on('end', () => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(w.post(Buffer.concat(morceaux).toString('utf8')))); });
    return;
  }
  res.statusCode = 404; res.end();
}).listen(port, '127.0.0.1', () => console.log('boite locale sur ' + port));
