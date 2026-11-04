// MIT. Static equivalent of viewer.py's read-only queries; no research is recomputed.
const LETTERS = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ';
const FOLD = {'ϲ':'Σ','Ϲ':'Σ','Ͻ':'Σ','ϐ':'Β','ϑ':'Θ','ϰ':'Κ','ϱ':'Ρ','ϕ':'Φ','ϖ':'Π'};
export function normalized(text) {
  let result = '';
  for (const raw of text) for (const c of (raw === '\u1fbe' ? '\u0345' : raw.normalize('NFD'))) {
    if (c === '\u0345' || /\p{M}/u.test(c) || ['ʼ','ʹ','ʹ'].includes(c)) continue;
    const letter = FOLD[c] || c.toUpperCase();
    if (LETTERS.includes(letter)) result += letter;
  }
  return result;
}
// SQLite LIKE folds ASCII case only. Unicode Greek word searches use normalized().
const foldASCII = s => String(s ?? '').replace(/[A-Z]/g, c => c.toLowerCase());
const unpack = packed => packed.rows.map(values => Object.fromEntries(packed.columns.map((k,i) => [k,values[i]])));
function compare(a,b) { return a < b ? -1 : a > b ? 1 : 0; }
const orders = {
  score: [['log2_score',-1],['word',1],['edition_id',1],['start_sequence',1]],
  word: [['word',1],['log2_score',-1],['edition_id',1],['start_sequence',1]],
  author: [['author',1],['title',1],['edition_id',1],['start_sequence',1]],
  location: [['urn',1],['start_sequence',1],['word',1]],
  isopsephy: [['urn',1],['citation',1],['group_size',1]],
};

export function createStore(base = './', fetcher = (...args) => fetch(...args)) {
  let manifestPromise, indexPromise;
  const passagePromises = new Map();
  async function read(path) {
    const r = await fetcher(base + path, {cache:'no-cache'});
    if (!r.ok) throw Error('Could not load the published data. Check your connection and retry, or reload the viewer if the site has been updated.');
    try { return await r.json(); } catch { throw Error('The published data could not be read. Please retry.'); }
  }
  function stats() {
    if (!manifestPromise) manifestPromise = read('data/manifest.json').then(m => {
      if (m.schema_version !== 1 || !/^v1-[0-9a-f]{16}$/.test(m.dataset)) throw Error('This data version is unsupported. Reload the page.');
      return m;
    }).catch(e => {manifestPromise = null; throw e;});
    return manifestPromise;
  }
  function index() {
    if (!indexPromise) indexPromise = stats().then(m => read(`data/${m.dataset}/index.json`)).then(data => {
      for (const name of ['acrostics','isopsephy']) data[name] = unpack(data[name]).map(row => {
        const e = data.editions[row.edition_id];
        return {urn:e.urn, author:e.author, title:e.title, source_path:e.source_path, source_url:e.source_url, ...row};
      });
      const matches = data.gamma_matches;
      if (!matches || !['first3','whole'].every(mode => Array.isArray(matches[mode]) &&
          matches[mode].every(i => Number.isInteger(i) && data.acrostics[i]))) {
        throw Error('The published Γ/L match data is unavailable. Reload the viewer.');
      }
      data.gammaSets = Object.fromEntries(['first3','whole'].map(mode =>
        [mode, new Set(matches[mode].map(i => data.acrostics[i]))]));
      delete data.gamma_matches;
      return data;
    }).catch(e => {indexPromise = null; throw e;});
    return indexPromise;
  }
  async function results(args = {}) {
    const kind = args.kind || 'acrostic';
    if (!['acrostic','isopsephy'].includes(kind)) throw Error('Unknown result kind');
    const data = await index();
    let rows = data[kind === 'acrostic' ? 'acrostics' : 'isopsephy'];
    const query = Array.from((args.q || '').trim()).slice(0,200).join('');
    if (query) {
      const literal = foldASCII(query), greek = normalized(query);
      const fields = ['author','title', ...(kind === 'acrostic' ? ['start_citation','end_citation'] : ['citation'])];
      rows = rows.filter(r => fields.some(f => foldASCII(r[f]).includes(literal)) ||
        (kind === 'acrostic' && greek && r.word.includes(greek)));
    }
    for (const field of kind === 'acrostic' ? ['direction','position'] : ['group_size']) {
      if (args[field]) rows = rows.filter(r => String(r[field]) === String(args[field]));
    }
    if (kind === 'acrostic' && args.shape === 'gamma') {
      const matches = data.gammaSets[args.gamma_match === 'whole' ? 'whole' : 'first3'];
      rows = rows.filter(r => [1,-1].includes(r.position) && matches.has(r));
    }
    const order = kind === 'isopsephy' ? orders.isopsephy : orders[args.sort] || orders.score;
    rows = rows.slice().sort((a,b) => {
      for (const [key,dir] of order) { const value = compare(a[key],b[key]); if (value) return value*dir; }
      // viewer.py reads acrostic_rank when filtering direction; preserve its tie order.
      // Otherwise stable sorting keeps the snapshot's original table order.
      return kind === 'acrostic' && args.direction ? compare(a.position,b.position) || compare(b.log2_score,a.log2_score) : 0;
    });
    const page = Math.max(0, Number.parseInt(args.page || 0,10) || 0);
    return {count:rows.length, page, rows:rows.slice(page*50,(page+1)*50)};
  }
  async function passage(args) {
    const eid = Number(args.edition_id);
    if (!Number.isInteger(eid) || eid < 1) throw Error('Unknown edition');
    const data = await index();
    if (!data.editions[eid]) throw Error('Unknown edition');
    if (!passagePromises.has(eid)) {
      passagePromises.set(eid, stats().then(m => read(`data/${m.dataset}/passages/${eid}.json`))
        .then(p => unpack(p).map(r => ({edition_id:eid,...r})))
        .catch(e => {passagePromises.delete(eid); throw e;}));
    }
    const lines = await passagePromises.get(eid);
    return lines.filter(r => args.poem !== undefined ? r.poem === Number(args.poem) :
      r.sequence >= Number(args.start) && r.sequence <= Number(args.end)).slice(0,1000);
  }
  return {stats, results, passage};
}
