// Source-preserving Greek letter maps shared by both viewers and Node tests.
(function(root) {
  const LETTERS = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ';
  const FOLD = {'ϲ':'Σ','Ϲ':'Σ','Ͻ':'Σ','ϐ':'Β','ϑ':'Θ','ϰ':'Κ','ϱ':'Ρ','ϕ':'Φ','ϖ':'Π'};
  function normalized(text) {
    let result = '';
    for (const raw of text) for (const c of (raw === '\u1fbe' ? '\u0345' : raw.normalize('NFD'))) {
      if (c === '\u0345' || /\p{M}/u.test(c) || ['ʼ','ʹ','ʹ'].includes(c)) continue;
      const letter = FOLD[c] || c.toUpperCase();
      if (LETTERS.includes(letter)) result += letter;
    }
    return result;
  }
  function sourceMap(text) {
    const units = [];
    for (const c of text) {
      if (/\p{M}/u.test(c) && units.length) units.at(-1).text += c;
      else units.push({text:c});
    }
    const letters = [], words = [];
    let word = [];
    for (const unit of units) {
      unit.letter = normalized(unit.text);
      if (unit.letter) {
        unit.index = letters.length; letters.push(unit); word.push(unit);
      } else if (![...unit.text].every(c => /\p{M}/u.test(c) || c === '\u1fbe')) {
        if (word.length) words.push(word);
        word = [];
      }
    }
    if (word.length) words.push(word);
    return {units, letters, words};
  }
  const positionLabel = p => p === -1 ? 'Telestic · final letter' : `Position ${p}`;
  const shapeLabel = row => (row.direction === 'forward') === (row.position === 1) ? 'Γ' : 'L';
  function highlightPlan(text, row, sequence, readingIndex, mode) {
    const map = sourceMap(text);
    const vertical = row.position === -1 ? map.letters.length - 1 : row.position - 1;
    const telestic = row.position === -1;
    const eligible = mode && [1,-1].includes(row.position);
    const edge = (row.direction === 'forward') === !telestic ? row.start_sequence : row.end_sequence;
    const horizontal = map.words[telestic ? map.words.length - 1 : 0] || [];
    const corner = new Set();
    if (eligible && sequence === edge) {
      const chosen = mode === 'whole' ? horizontal : telestic ? horizontal.slice(-3) : horizontal.slice(0,3);
      for (const unit of chosen) corner.add(unit.index);
    }
    const verticalCorner = eligible && (mode === 'whole' || (telestic ? readingIndex >= row.word.length - 3 : readingIndex < 3));
    return map.units.map(unit => ({text:unit.text, letter:unit.letter,
      vertical:unit.index === vertical,
      corner:corner.has(unit.index) || (unit.index === vertical && verticalCorner)}));
  }
  function sourceLine(line, row, readingIndex, mode) {
    const p = document.createElement('p'); p.className = 'greek';
    const plan = row ? highlightPlan(line.text,row,line.sequence,readingIndex,mode) : [{text:line.text}];
    for (const part of plan) {
      if (!part.vertical && !part.corner) {p.append(document.createTextNode(part.text)); continue;}
      const mark = document.createElement('mark'); mark.textContent = part.text;
      mark.className = [part.vertical ? 'letter-path' : '', part.corner ? 'corner-match' : ''].filter(Boolean).join(' ');
      mark.title = [part.vertical ? `Pattern letter ${part.letter}` : '', part.corner ? 'Γ/L word match' : ''].filter(Boolean).join(' · ');
      // Describe the highlight without replacing the original Greek text.
      mark.setAttribute('aria-description', mark.title);
      p.append(mark);
    }
    return p;
  }
  const api = {normalized, sourceMap, positionLabel, shapeLabel, highlightPlan, sourceLine};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GreekLetters = api;
})(globalThis);
