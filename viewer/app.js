const $ = id => document.getElementById(id);
let kind = 'acrostic', page = 0, version = 0, selectedVersion = 0;
const fmt = n => Number(n).toLocaleString('en-US');
function el(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
async function api(path, args = {}) { const r = await fetch(path + '?' + new URLSearchParams(args)); if (!r.ok) throw Error('Could not load results. Check the local server.'); return r.json(); }
async function load() {
  const current = ++version; ++selectedVersion;
  const args = {kind, page, q: $('q').value};
  for (const id of kind === 'acrostic' ? ['direction','position','sort'] : ['group_size']) args[id] = $(id).value;
  try {
    const data = await api('/api/results', args); if (current !== version) return;
    $('rows').replaceChildren(); $('result-count').textContent = `${fmt(data.count)} results`;
    $('page').textContent = data.count ? `${page+1} / ${Math.ceil(data.count/50)}` : '0 results';
    $('previous').disabled = page === 0; $('next').disabled = (page+1)*50 >= data.count;
    if (!data.rows.length) $('rows').append(el('p','No matches. Try a shorter word or change the filters.','no-results'));
    for (const row of data.rows) {
      const button = el('button', undefined, 'row'); button.type = 'button';
      const top = el('div',undefined,'row-top');
      top.append(el('span',kind === 'acrostic' ? row.word : `Poem ${row.citation}`,'word'));
      top.append(el('span',kind === 'acrostic' ? `${row.direction === 'forward' ? '↓' : '↑'} Position ${row.position}` : `${row.group_size === 1 ? 'Lines' : `Groups of ${row.group_size}`} · ${row.convention.replace('_only',' only')}`,'badge'));
      button.append(top,el('p',`${row.author} · ${row.title}`,'row-source'));
      const loc = el('div',kind === 'acrostic' ? `${row.start_citation}–${row.end_citation}` : `Omit ${JSON.parse(row.omit_totals).map(fmt).join(' / ')} · Count ${JSON.parse(row.count_totals).map(fmt).join(' / ')}`,'row-location');
      if (kind === 'acrostic') loc.append(el('small',`${row.log2_score.toFixed(2)} bits`));
      button.append(loc); button.onclick = () => detail(row,button); $('rows').append(button);
    }
  } catch(e) { $('result-count').textContent = e.message; }
}
async function detail(row,button) {
  const current = ++selectedVersion, selectedKind = kind;
  document.querySelectorAll('.row.selected').forEach(n => n.classList.remove('selected')); button.classList.add('selected');
  const args = {edition_id: row.edition_id};
  if (kind === 'acrostic') Object.assign(args,{start:row.start_sequence,end:row.end_sequence}); else args.poem=row.poem;
  try {
    const lines = await api('/api/passage',args); if(current !== selectedVersion) return;
    const box = $('detail'); box.replaceChildren();
    box.append(el('div',selectedKind === 'acrostic' ? 'LETTER PATTERN' : 'WHOLE-POEM EQUALITY','eyebrow'));
    box.append(el('h2',selectedKind === 'acrostic' ? row.word : row.citation,'detail-word'));
    box.append(el('p',`${row.author} · ${row.title}`,'detail-meta'));
    if(selectedKind === 'acrostic') {
      box.append(el('p',`${row.log2_score.toFixed(4)} bits · Word occurs ${fmt(row.word_frequency)} times in ${fmt(row.edition_count)} editions.`,'detail-meta'));
      box.append(el('p',`Read ${row.direction === 'forward' ? 'top to bottom ↓' : 'bottom to top ↑'}, letter ${row.position} of each normalized line. The marked letters retain this reading path.`,'reading-note'));
    } else {
      const sums=el('div',undefined,'sums');
      for(const [label,key] of [['Omit subscript iota','omit_totals'],['Count subscript iota','count_totals']]) {const s=el('div',label,'sum');s.append(el('b',JSON.parse(row[key]).map(fmt).join(' / ')));sums.append(s);}
      box.append(sums,el('p',`Every successive group of ${row.group_size} ${row.group_size===1?'line':'lines'} is compared across the whole encoded poem. Equality: ${row.convention.replace('_only',' only')}.`,'reading-note'));
    }
    lines.forEach((line,i)=>{
      const verse=el('div',undefined,'verse'),content=el('div');verse.append(el('div',line.citation,'citation'));
      content.append(el('p',line.text,'greek'));
      if(selectedKind==='acrostic') {
        const normal=el('p',undefined,'normalized'); Array.from(line.letters).forEach((c,j)=>normal.append(j===row.position-1?el('mark',c):document.createTextNode(c)));content.append(normal);
      } else content.append(el('p',`Line sum · omit ${fmt(JSON.parse(row.omit_lines)[i])} / count ${fmt(JSON.parse(row.count_lines)[i])}`,'line-total'));
      if(line.damaged) content.append(el('p','This line contains marked textual uncertainty.','warning'));
      verse.append(content);box.append(verse);
    });
    box.append(el('p',row.urn,'detail-meta'),el('p',row.source_path,'detail-meta'));
    if(innerWidth<850) box.scrollIntoView({behavior:'smooth',block:'start'});
  } catch(e) {$('detail').replaceChildren(el('p',e.message));}
}
let timer;
$('q').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{page=0;load();},180);});
$('filters').onsubmit=e=>{e.preventDefault();page=0;load();};
for(const id of ['direction','position','sort','group_size']) $(id).onchange=()=>{page=0;load();};
$('previous').onclick=()=>{page--;load();};$('next').onclick=()=>{page++;load();};
for(const tab of document.querySelectorAll('.tab')) tab.onclick=()=>{
  kind=tab.dataset.kind;page=0;document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===tab));
  document.querySelectorAll('.acro').forEach(n=>n.hidden=kind!=='acrostic');document.querySelectorAll('.iso').forEach(n=>n.hidden=kind!=='isopsephy');
  $('explanation').textContent=kind==='acrostic'?'Rarity = log₂ of the reciprocal letter-frequency product. Higher values favor longer strings and rarer letters; they do not measure intention.':'Only explicitly encoded whole poems and epigrams are searched. Both iota conventions are shown; numerical equality alone does not establish intention.';
  $('detail').replaceChildren(el('p','Select a result to read its passage.','empty'));load();
};
api('/api/stats').then(data=>{$('acount').textContent=fmt(data.acrostics);$('icount').textContent=fmt(data.isopsephy);for(const p of data.positions){const option=el('option',`Position ${p}`);option.value=p;$('position').append(option);}load();}).catch(e=>$('result-count').textContent=e.message);
