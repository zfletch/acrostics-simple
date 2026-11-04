// End-to-end checks of the actual public/local passage renderers at desktop/mobile widths.
const {chromium} = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const {normalized,sourceMap} = require('../viewer/letters.js');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const publicURL = process.env.PAGES_URL || 'http://127.0.0.1:8877/';
const localURL = process.env.VIEWER_URL || 'http://127.0.0.1:8766/';
const out = process.env.HEADLESS_OUTPUT || path.join(__dirname,'../output/pages-browser/telestics');
fs.mkdirSync(out,{recursive:true});
(async () => {
 const browser = await chromium.launch({headless:true,chromiumSandbox:true});
 const errors=[],checks=[],layouts=[];
 try {
  for (const [surface,url] of [['public',publicURL],['local',localURL]]) {
   const page = await browser.newPage({viewport:{width:1365,height:1000},reducedMotion:'reduce'});
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(url);
   await page.waitForFunction(()=>document.querySelector('#result-count').textContent==='54,564 results');
   assert.deepEqual(await page.locator('#position option').evaluateAll(ns=>ns.map(n=>n.value)),['','-1','1','2']);
   const modes = surface==='public' ? [null,'first3','whole'] : [null];
   for (const width of [1365,390]) {
    await page.setViewportSize({width,height:width===390?844:1000});
    for (const direction of ['forward','reverse']) for (const mode of modes) {
     await page.selectOption('#position','-1');
     await page.selectOption('#direction',direction);
     if (surface==='public') {
      await page.selectOption('#shape',mode?'gamma':'');
      if(mode) await page.selectOption('#gamma_match',mode);
     }
     const args={position:-1,direction,shape:mode?'gamma':'',gamma_match:mode};
     const expected = await page.evaluate(async ({surface,args})=>surface==='public' ?
       (await import('./data.js')).createStore().results(args) :
       (await fetch('/api/results?'+new URLSearchParams(args))).json(),{surface,args});
     assert(expected.count>0);
     await page.waitForFunction(n=>document.querySelector('#result-count').textContent===`${n.toLocaleString('en-US')} results`,expected.count);
     const row=expected.rows[0];
     await page.locator('.row').first().click();
     await page.waitForFunction(w=>document.querySelector('#detail h2')?.textContent===w,row.word);
     const argsPassage={edition_id:row.edition_id,start:row.start_sequence,end:row.end_sequence};
     const lines=await page.evaluate(async ({surface,args})=>surface==='public' ?
       (await import('./data.js')).createStore().passage(args) :
       (await fetch('/api/passage?'+new URLSearchParams(args))).json(),{surface,args:argsPassage});
     assert.equal(await page.locator('.normalized').count(),0,'duplicate normalized row removed');
     assert.deepEqual(await page.locator('#detail .greek').allTextContents(),lines.map(l=>l.text),'source text preserved');
     const letters=(await page.locator('#detail .letter-path').allTextContents()).map(normalized);
     assert.equal(letters.length,lines.length);
     assert.equal((direction==='reverse'?letters.slice().reverse():letters).join(''),row.word);
     const marks=await page.locator('#detail .letter-path').evaluateAll(ns=>ns.map(n=>({title:n.title,description:n.getAttribute('aria-description'),hasLabel:n.hasAttribute('aria-label'),tag:n.tagName,underline:getComputedStyle(n).textDecorationLine})));
     assert(marks.every(m=>m.title.startsWith('Pattern letter ')&&m.tag==='MARK'&&m.description===m.title&&!m.hasLabel&&m.underline.includes('underline')));
     if(mode) {
      const edge=direction==='forward'?lines.length-1:0;
      const cornerWord=sourceMap(lines[edge].text).words.at(-1).map(u=>u.letter).join('');
      const corner=normalized((await page.locator('#detail .greek').nth(edge).locator('.corner-match').allTextContents()).join(''));
      assert.equal(corner,mode==='whole'?cornerWord:cornerWord.slice(-3));
      assert.equal(corner,mode==='whole'?row.word:row.word.slice(-3));
      assert.equal(await page.locator('#detail .letter-path.corner-match').count(),mode==='whole'?row.word.length:3);
     }
     const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
     assert(layout.scrollWidth<=layout.width,JSON.stringify(layout));
     layouts.push({surface,direction,mode,width,...layout});
     if(surface==='public'&&((width===1365&&direction==='forward'&&mode==='whole')||(width===390&&direction==='reverse'&&mode==='first3'))) {
      await page.locator('#detail').scrollIntoViewIfNeeded();
      await page.locator('#detail').screenshot({path:path.join(out,`${width}-${direction}-${mode}.png`)});
     }
     checks.push({surface,width,direction,mode:mode||'all telestics',count:expected.count,word:row.word});
    }
   }
   await page.close();
  }
  assert.deepEqual(errors,[]);
  const result={browser:await browser.version(),checks,layouts,pageErrors:errors};
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
 } finally {await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
