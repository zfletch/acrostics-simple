const {positionLabel, shapeLabel, sourceLine} = globalThis.GreekLetters;
// MIT. Presentation follows the local viewer; data access is entirely static.
import {createStore} from './data.js';
const store = createStore();
const $ = id => document.getElementById(id);
let kind = 'acrostic', page = 0, version = 0, selectedVersion = 0, timer;
const fmt = n => Number(n).toLocaleString('en-US');
function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function clearDetail() { $('detail').replaceChildren(el('p','Select a result to read its passage.','empty')); }
function reloadButton() {
  const button = el('button','Reload viewer','retry-passage');
  button.type = 'button'; button.onclick = () => location.reload(); return button;
}
async function load() {
  const current = ++version;
  ++selectedVersion;
  clearTimeout(timer);
  clearDetail();
  $('rows').setAttribute('aria-busy','true');
  $('rows').replaceChildren();
  $('result-count').textContent = 'Loading results…';
  $('previous').disabled = $('next').disabled = true;
  $('page').textContent = '';
  $('result-error').hidden = $('retry').hidden = true;
  const args = {kind,page,q:$('q').value};
  for (const id of kind === 'acrostic' ? ['direction','position','sort','shape','gamma_match'] : ['group_size']) args[id] = $(id).value;
  try {
    const data = await store.results(args);
    if (current !== version) return;
    $('result-count').textContent = `${fmt(data.count)} results`;
    $('page').textContent = data.count ? `${page+1} / ${Math.ceil(data.count/50)}` : '0 results';
    $('previous').disabled = page === 0;
    $('next').disabled = (page+1)*50 >= data.count;
    if (!data.rows.length) $('rows').append(el('p','No matches. Try a shorter word or change the filters.','no-results'));
    for (const row of data.rows) {
      const button = el('button',undefined,'row');
      button.type = 'button';
      button.setAttribute('aria-pressed','false');
      const top = el('div',undefined,'row-top');
      top.append(el('span',kind === 'acrostic' ? row.word : `Poem ${row.citation}`,'word'));
      top.append(el('span',kind === 'acrostic' ? `${row.direction === 'forward' ? '↓' : '↑'} ${positionLabel(row.position)}` :
        `${row.group_size === 1 ? 'Lines' : `Groups of ${row.group_size}`} · ${row.convention.replace('_only',' only')}`,'badge'));
      if (kind === 'acrostic' && $('shape').value === 'gamma') top.append(el('span', shapeLabel(row),'badge'));
      button.append(top,el('p',`${row.author} · ${row.title}`,'row-source'));
      const loc = el('div',kind === 'acrostic' ? `${row.start_citation}–${row.end_citation}` :
        `Omit ${JSON.parse(row.omit_totals).map(fmt).join(' / ')} · Count ${JSON.parse(row.count_totals).map(fmt).join(' / ')}`,'row-location');
      if (kind === 'acrostic') loc.append(el('small',`${row.log2_score.toFixed(2)} bits`));
      button.append(loc);
      button.onclick = () => detail(row,button);
      $('rows').append(button);
    }
  } catch (e) {
    if (current !== version) return;
    $('result-count').textContent = 'Results unavailable';
    $('result-error').replaceChildren(el('p',e.message),reloadButton());
    $('result-error').hidden = $('retry').hidden = false;
  } finally {
    if (current === version) $('rows').setAttribute('aria-busy','false');
  }
}
async function detail(row,button) {
  const current = ++selectedVersion, selectedKind = kind;
  document.querySelectorAll('.row').forEach(n => n.setAttribute('aria-pressed',String(n === button)));
  const box = $('detail');
  box.replaceChildren(el('p','Loading passage…','empty'));
  const args = {edition_id:row.edition_id};
  if (selectedKind === 'acrostic') Object.assign(args,{start:row.start_sequence,end:row.end_sequence});
  else args.poem = row.poem;
  try {
    const lines = await store.passage(args);
    if (current !== selectedVersion) return;
    if (!lines.length) throw Error('This passage is unavailable in the published snapshot.');
    box.replaceChildren();
    box.append(el('div',selectedKind === 'acrostic' ? 'LETTER PATTERN' : 'WHOLE-POEM EQUALITY','eyebrow'));
    box.append(el('h2',selectedKind === 'acrostic' ? row.word : row.citation,'detail-word'));
    box.append(el('p',`${row.author} · ${row.title}`,'detail-meta'));
    if (selectedKind === 'acrostic') {
      box.append(el('p',`${row.log2_score.toFixed(4)} bits · Word occurs ${fmt(row.word_frequency)} times in ${fmt(row.edition_count)} editions.`,'detail-meta'));
      box.append(el('p',`Read ${row.direction === 'forward' ? 'top to bottom ↓' : 'bottom to top ↑'}, ${row.position === -1 ? 'the final Greek letter' : `Greek letter ${row.position}`} of each line.`,'reading-note'));
    } else {
      const sums = el('div',undefined,'sums');
      for (const [label,key] of [['Omit subscript iota','omit_totals'],['Count subscript iota','count_totals']]) {
        const s = el('div',label,'sum');
        s.append(el('b',JSON.parse(row[key]).map(fmt).join(' / ')));
        sums.append(s);
      }
      box.append(sums,el('p',`Every successive group of ${row.group_size} ${row.group_size === 1 ? 'line' : 'lines'} is compared across the whole encoded poem. Equality: ${row.convention.replace('_only',' only')}.`,'reading-note'));
    }
    lines.forEach((line,i) => {
      const verse = el('div',undefined,'verse'), content = el('div');
      verse.append(el('div',line.citation,'citation'));
      content.append(sourceLine(line, selectedKind === 'acrostic' ? row : null,
        row.direction === 'reverse' ? lines.length - 1 - i : i,
        $('shape').value === 'gamma' ? $('gamma_match').value : null));
      if (selectedKind !== 'acrostic') content.append(el('p',`Line sum · omit ${fmt(JSON.parse(row.omit_lines)[i])} / count ${fmt(JSON.parse(row.count_lines)[i])}`,'line-total'));
      if (line.damaged) content.append(el('p','This line contains marked textual uncertainty.','warning'));
      verse.append(content);
      box.append(verse);
    });
    const source = el('a','Read the pinned source edition','source-link');
    source.href = row.source_url;
    box.append(source,el('p',row.urn,'detail-meta'),el('p',row.source_path,'detail-meta'));
    if (innerWidth < 850) box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});
  } catch (e) {
    if (current !== selectedVersion) return;
    const retry = el('button','Retry passage','retry-passage');
    retry.type = 'button';
    retry.onclick = () => detail(row,button);
    box.replaceChildren(el('p',e.message),retry,reloadButton());
  }
}
async function initialize() {
  $('retry').hidden = $('result-error').hidden = true;
  $('result-count').textContent = 'Loading results…';
  try {
    const stats = await store.stats();
    $('acount').textContent = fmt(stats.acrostics);
    $('icount').textContent = fmt(stats.isopsephy);
    if ($('position').options.length === 1) for (const p of stats.positions) {
      const option = el('option',positionLabel(p)); option.value = p; $('position').append(option);
    }
    await load();
  } catch (e) {
    $('result-count').textContent = 'Results unavailable';
    $('result-error').replaceChildren(el('p',e.message),reloadButton());
    $('retry').hidden = $('result-error').hidden = false;
    $('rows').setAttribute('aria-busy','false');
  }
}
$('q').addEventListener('input',() => {
  clearTimeout(timer);
  // Invalidate old requests and selection immediately, including during the debounce.
  ++version; ++selectedVersion; page = 0;
  clearDetail(); $('rows').replaceChildren(); $('rows').setAttribute('aria-busy','true');
  $('result-count').textContent = 'Searching…'; $('page').textContent = '';
  $('previous').disabled = $('next').disabled = true;
  $('result-error').hidden = $('retry').hidden = true;
  timer = setTimeout(load,180);
});
$('filters').onsubmit = e => {e.preventDefault(); page=0; load();};
function syncShape() {
  const active = kind === 'acrostic' && $('shape').value === 'gamma';
  document.querySelectorAll('.gamma-mode').forEach(n => n.hidden = !active);
  for (const option of $('position').options) option.disabled = active && !['','1','-1'].includes(option.value);
  if (active && !['','1','-1'].includes($('position').value)) $('position').value = '';
  $('gamma_match').options[0].textContent = $('position').value === '-1' ? 'Final three letters' :
    $('position').value === '1' ? 'First three letters' : 'Three corner letters';
}
for (const id of ['direction','position','sort','group_size','gamma_match']) $(id).onchange = () => {syncShape(); page=0; load();};
$('shape').onchange = () => {
  syncShape(); page=0; load();
};
$('previous').onclick = () => {page--; load();};
$('next').onclick = () => {page++; load();};
$('retry').onclick = initialize;
for (const tab of document.querySelectorAll('.tab')) tab.onclick = () => {
  kind = tab.dataset.kind; page = 0;
  document.querySelectorAll('.tab').forEach(t => {t.classList.toggle('active',t === tab); t.setAttribute('aria-pressed',String(t === tab));});
  document.querySelectorAll('.acro').forEach(n => n.hidden = kind !== 'acrostic');
  document.querySelectorAll('.iso').forEach(n => n.hidden = kind !== 'isopsephy');
  syncShape();
  $('explanation').textContent = kind === 'acrostic' ? 'Rarity = log₂ of the reciprocal letter-frequency product. Higher values favor longer strings and rarer letters; they do not measure intention.' :
    'Only explicitly encoded whole poems and epigrams are searched. Both iota conventions are shown; numerical equality alone does not establish intention.';
  load();
};
syncShape();
initialize();
