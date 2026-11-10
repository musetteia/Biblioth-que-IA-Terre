// Simulation des services Google pour exécuter Code.gs hors de Google (tests uniquement).
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const src = fs.readFileSync(path.join(__dirname, '..', 'Code.gs'), 'utf8');

function monde(props) {
  const cache = {}, mails = [], fichiers = [];
  const horloge = { t: Date.now() };
  const sandbox = {
    console, Date: class extends Date { constructor(...a) { super(...(a.length ? a : [horloge.t])); } static now() { return horloge.t; } },
    CacheService: { getScriptCache: () => ({
      get: k => (cache[k] && cache[k].exp > horloge.t) ? cache[k].v : null,
      put: (k, v, s) => { cache[k] = { v: String(v), exp: horloge.t + s * 1000 }; },
      remove: k => { delete cache[k]; } }) },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] || null, setProperty: (k, v) => { props[k] = v; }, deleteProperty: k => { delete props[k]; } }) },
    Logger: { log() {} },
    MailApp: { sendEmail: m => mails.push(m), getRemainingDailyQuota: () => 100 - mails.length },
    DriveApp: { getFolderById: () => ({ createFile: (n, c) => fichiers.push({ n, c }) }) },
    ContentService: { createTextOutput: t => ({ t, setMimeType() { return this; }, getContent() { return this.t; } }), MimeType: { JSON: 'json' } },
    Session: {},
    Utilities: {
      getUuid: () => crypto.randomUUID(),
      computeDigest: (algo, v) => Array.from(crypto.createHash('sha256').update(typeof v === 'string' ? Buffer.from(v, 'utf8') : Buffer.from(v.map(b => b & 255))).digest()).map(b => b > 127 ? b - 256 : b),
      DigestAlgorithm: { SHA_256: 'sha256' }, Charset: { UTF_8: 'utf8' },
      base64Decode: s => Array.from(Buffer.from(s, 'base64')).map(b => b > 127 ? b - 256 : b),
      formatDate: (d, tz, f) => { const x = new Date(d.getTime()); const p = n => String(n).padStart(2, '0'); const Y = x.getUTCFullYear(), M = p(x.getUTCMonth() + 1), D = p(x.getUTCDate()), H = p(x.getUTCHours());
        if (f === 'yyyyMMddHH') return `${Y}${M}${D}${H}`; if (f === 'yyyyMMdd') return `${Y}${M}${D}`; if (f.startsWith('yyyyMMdd-')) return `${Y}${M}${D}-${H}${p(x.getUTCMinutes())}${p(x.getUTCSeconds())}`; return x.toISOString(); },
      newBlob: (c, t, n) => ({ c, t, n }) }
  };
  const ctx = require('vm').createContext(sandbox);
  require('vm').runInContext(src, ctx);
  const post = (obj) => JSON.parse(ctx.doPost({ postData: { contents: typeof obj === 'string' ? obj : JSON.stringify(obj) } }).getContent());
  return { post, mails, fichiers, horloge, props, cache, revoquer: () => ctx.revoquer() };
}

module.exports = { monde };
