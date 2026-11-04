const assert = require('node:assert/strict');
const {normalized,sourceMap,highlightPlan} = require('../viewer/letters.js');
let input = '';
process.stdin.on('data',c => input += c);
process.stdin.on('end',() => {
  const {passages} = JSON.parse(input);
  for (const line of passages) {
    const map = sourceMap(line.text);
    assert.equal(map.units.map(u => u.text).join(''),line.text);
    assert.equal(map.letters.map(u => u.letter).join(''),line.letters);
    for (const position of [1,2,-1]) {
      if (line.letters.length < Math.abs(position)) continue;
      const plan = highlightPlan(line.text,{position,word:'',direction:'forward'},0,0,null);
      const marked = plan.filter(p => p.vertical);
      assert.equal(marked.length,1);
      assert.equal(normalized(marked[0].text),line.letters.at(position === -1 ? -1 : position-1));
    }
  }
  for (const text of ['« ᾧ, ϲ!','« ω\u0345, ς\u0301!','😀 α\u1fbeβ·','ι Ἄλφα, ὦ·']) {
    const plan = highlightPlan(text,{position:-1,word:'',direction:'forward'},0,0,null);
    assert.equal(plan.map(p => p.text).join(''),text);
    assert.equal(normalized(plan.filter(p => p.vertical).map(p => p.text).join('')),normalized(text).at(-1));
  }
  for (const position of [1,-1]) for (const direction of ['forward','reverse']) {
    const row = {position,direction,word:'ΑΒΓΔ',start_sequence:10,end_sequence:13};
    const edge = position === 1 ? (direction === 'forward' ? 10 : 13) : (direction === 'forward' ? 13 : 10);
    const text = position === 1 ? 'ἀβγδ λέξις!' : 'λέξις ἀβγδ!';
    for (const mode of ['first3','whole']) {
      const pathIndex = position === 1 ? 0 : 3;
      const plan = highlightPlan(text,row,edge,pathIndex,mode);
      const corner = normalized(plan.filter(p => p.corner).map(p => p.text).join(''));
      assert.equal(corner,mode === 'whole' ? 'ΑΒΓΔ' : position === 1 ? 'ΑΒΓ' : 'ΒΓΔ');
      assert.equal(plan.filter(p => p.vertical).length,1);
      assert.equal(plan.map(p => p.text).join(''),text);
      const other = highlightPlan('ἐν ᾧ',row,edge === 10 ? 13 : 10,position === 1 ? 3 : 0,mode);
      assert.equal(other.filter(p => p.corner).length,mode === 'whole' ? 1 : 0);
    }
  }
  console.log(JSON.stringify({passagesChecked:passages.length,positions:[1,2,-1],sourcePreserved:true,corners:'both edges and directions, three-letter and whole-word'}));
});
