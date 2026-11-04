// Exercise the actual static site under its project path, or a deployed URL.
const {chromium} = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const {normalized} = require('../viewer/letters.js');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const base = process.env.PAGES_URL || 'http://127.0.0.1:8877/acrostics-simple/';
const out = process.env.HEADLESS_OUTPUT || path.join(__dirname,'../output/pages-browser');
fs.mkdirSync(out,{recursive:true});
(async () => {
  const browser = await chromium.launch({headless:true,chromiumSandbox:true});
  try {
    const context = await browser.newContext({viewport:{width:1365,height:1000},reducedMotion:'reduce'});
    const page = await context.newPage();
    const errors=[], requests=[];
    page.on('pageerror',e => errors.push(e.message));
    page.on('request',r => requests.push(r.url()));
    const count = text => page.waitForFunction(t => document.getElementById('result-count').textContent === t,text);
    const marks = n => page.waitForFunction(n => document.querySelectorAll('#detail mark').length === n,n);
    const overflow = () => page.evaluate(() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
    await page.goto(base,{waitUntil:'networkidle'});
    await count('54,564 results');
    assert.equal(await page.locator('.row').count(),50);
    assert.equal(await page.locator('#icount').innerText(),'27');
    assert(!requests.some(u => u.includes('/passages/')),'passages must load only on selection');
    await page.locator('#shape').selectOption('gamma');
    assert(!(await page.locator('#position').isDisabled()));
    assert(await page.locator('#position option[value="2"]').evaluate(n => n.disabled));
    assert.equal(await page.locator('#position').inputValue(),'');
    assert(await page.locator('.gamma-mode').isVisible());
    await page.waitForFunction(() => document.querySelector('#result-count').textContent.endsWith('results'));
    const first3Count = parseInt((await page.locator('#result-count').innerText()).replaceAll(',',''),10);
    await page.locator('#gamma_match').selectOption('whole');
    await page.waitForFunction(() => document.querySelector('#result-count').textContent.endsWith('results'));
    const wholeCount = parseInt((await page.locator('#result-count').innerText()).replaceAll(',',''),10);
    assert(wholeCount <= first3Count,'whole-word matches must be a subset of prefix matches');
    assert(first3Count < 54564);
    await page.locator('#shape').selectOption('');
    await count('54,564 results');
    assert(!(await page.locator('#position').isDisabled()));
    assert(!(await page.locator('.gamma-mode').isVisible()));
    const first = await page.locator('.row').first().innerText();
    await page.locator('#next').click();
    await page.waitForFunction(() => document.getElementById('page').textContent.startsWith('2 /'));
    assert.notEqual(await page.locator('.row').first().innerText(),first);
    await page.locator('#previous').click();
    await page.waitForFunction(() => document.getElementById('page').textContent.startsWith('1 /'));
    assert.equal(await page.locator('.row').first().innerText(),first);
    for (const sort of ['word','author','location','score']) {
      await page.locator('#sort').selectOption(sort); await count('54,564 results');
    }
    const scores = (await page.locator('.row small').allTextContents()).map(parseFloat);
    assert(scores.every((s,i) => i === 0 || scores[i-1] >= s));
    await page.locator('#direction').selectOption('reverse');
    await page.locator('#position').selectOption('1');
    await page.locator('#q').fill('Homer');
    await count('785 results');
    assert.equal(await page.locator('.row').count(),50);
    assert((await page.locator('.row-source').allTextContents()).every(s => /homer/i.test(s)));
    await page.locator('#next').click();
    await page.waitForFunction(() => document.getElementById('page').textContent.startsWith('2 /'));
    await page.locator('#q').fill('Ἕκτωρ'); await count('1 results');
    assert.match(await page.locator('#page').innerText(),/^1 \/ 1$/);
    const row = page.locator('.row').first();
    await row.focus(); await page.keyboard.press('Enter'); await marks(5);
    assert.equal(normalized((await page.locator('#detail .letter-path').allTextContents()).reverse().join('')),'ΕΚΤΩΡ');
    assert.deepEqual(await page.locator('#detail .citation').allTextContents(),['6.511','6.512','6.513','6.514','6.515']);
    assert.match(await page.locator('.source-link').getAttribute('href'),/^https:\/\/github\.com\/PerseusDL\/canonical-greekLit\/blob\/790c842/);
    await page.screenshot({path:path.join(out,'desktop-hektor.png'),fullPage:true});
    await page.locator('#direction').selectOption('forward');
    await page.locator('#position').selectOption('2');
    await page.locator('#q').fill('Ἕλληνες'); await count('1 results');
    await page.locator('.row').click(); await marks(7);
    assert.equal(normalized((await page.locator('#detail .letter-path').allTextContents()).join('')),'ΕΛΛΗΝΕΣ');
    assert.deepEqual(await page.locator('#detail .citation').allTextContents(),['7.502','7.503','7.504','7.505','7.506','7.507','7.508']);
    await page.locator('#q').fill('ἐράσαι'); await count('1 results');
    await page.locator('.row').click(); await marks(6);
    assert.equal(normalized((await page.locator('#detail .letter-path').allTextContents()).join('')),'ΕΡΑΣΑΙ');
    await page.locator('#q').fill('7.548'); await count('1 results');
    await page.locator('.row').click(); await marks(4);
    assert.equal(normalized((await page.locator('#detail .letter-path').allTextContents()).join('')),'ΙΣΧΕ');
    assert.deepEqual(await page.locator('#detail .citation').allTextContents(),['7.548.2','7.548.3','7.548.5','7.548.6']);
    await page.locator('#q').fill('%'); await count('0 results');
    assert(await page.locator('#next').isDisabled());
    await page.locator('[data-kind=isopsephy]').click();
    await page.locator('#q').fill('8.39');
    await page.locator('#group_size').selectOption('2'); await count('1 results');
    await page.locator('.row').click();
    await page.waitForFunction(() => document.querySelectorAll('.sum b').length === 2);
    assert.deepEqual(await page.locator('.sum b').allTextContents(),['6,903 / 6,903','6,903 / 6,913']);
    assert.equal(await page.locator('.line-total').count(),4);
    const desktop = await overflow(); assert(desktop.scrollWidth <= desktop.width);
    await page.screenshot({path:path.join(out,'desktop-ap8-39.png'),fullPage:true});
    const recovered = [
      ['6.321','2','5,699 / 5,689','5,699 / 5,699','count only',4],
      ['6.324','2','9,097 / 9,117','9,117 / 9,117','count only',4],
      ['6.325','2','5,953 / 5,953','5,953 / 5,953','both',4],
      ['6.326','2','5,982 / 5,982','5,982 / 5,982','both',4],
      ['6.327','1','4,111 / 4,111','4,111 / 4,111','both',2],
      ['6.329','2','7,579 / 7,569','7,579 / 7,579','count only',4],
      ['7.547','2','7,247 / 7,237','7,267 / 7,267','count only',4],
      ['7.548','2','7,150 / 7,150','7,160 / 7,150','omit only',4]
    ];
    for (const [citation,group,omit,counted,policy,n] of recovered) {
      await page.locator('#group_size').selectOption(group);
      await page.locator('#q').fill(citation); await count('1 results');
      await page.locator('.row').click();
      await page.waitForFunction(c => document.querySelector('#detail h2')?.textContent === c,citation);
      assert.deepEqual(await page.locator('.sum b').allTextContents(),[omit,counted]);
      assert.match(await page.locator('#detail .reading-note').innerText(),new RegExp(`Equality: ${policy}\\.`));
      assert.equal(await page.locator('.line-total').count(),n);
      assert.equal(await page.locator('.greek').count(),n);
      assert(!(await page.locator('#detail').innerText()).includes('NaN'));
    }
    assert.deepEqual(await page.locator('#detail .citation').allTextContents(),['7.548.2','7.548.3','7.548.5','7.548.6']);
    assert((await page.locator('#detail .greek').first().innerText()).includes('Δαίμων'));
    await page.screenshot({path:path.join(out,'desktop-ap7-548.png'),fullPage:true});
    for (const citation of ['7.549','7.550']) {
      await page.locator('#q').fill(citation); await count('0 results');
    }
    await page.locator('#q').fill('7.548'); await count('1 results');
    await page.locator('.row').click();
    await page.waitForFunction(() => document.querySelector('#detail h2')?.textContent === '7.548');
    await page.setViewportSize({width:390,height:844});
    const mobileISO = await overflow(); assert(mobileISO.scrollWidth <= mobileISO.width);
    await page.screenshot({path:path.join(out,'mobile-ap7-548.png'),fullPage:true});
    await page.locator('[data-kind=acrostic]').click();
    await page.locator('#q').fill('Ἕλληνες'); await count('1 results');
    await page.locator('.row').click(); await marks(7);
    const mobile = await overflow(); assert(mobile.scrollWidth <= mobile.width);
    await page.screenshot({path:path.join(out,'mobile-hellenes.png'),fullPage:true});
    const methods = await context.newPage();
    const response = await methods.goto(new URL('methods.html',base).href);
    assert.equal(response.status(),200);
    assert.match(await methods.locator('body').innerText(),/CC BY-SA 4.0/);
    await methods.close();
    // Fresh contexts exercise failure recovery without previously cached data.
    for (const resource of ['manifest.json','index.json']) {
      const failure = await browser.newContext(); const p = await failure.newPage();
      p.on('pageerror',e => errors.push(e.message));
      let fail = true;
      await p.route(`**/${resource}`,r => {if (fail) {fail=false; return r.fulfill({status:503,body:'Temporarily unavailable'});} return r.continue();});
      await p.goto(base); await p.locator('#retry').waitFor({state:'visible'});
      await p.locator('#retry').click();
      await p.waitForFunction(() => document.getElementById('result-count').textContent === '54,564 results');
      await failure.close();
    }
    const failure = await browser.newContext(); const p = await failure.newPage();
    p.on('pageerror',e => errors.push(e.message));
    let fail = true;
    await p.route('**/passages/148.json',r => {if (fail) {fail=false; return r.fulfill({status:404,body:'Missing'});} return r.continue();});
    await p.goto(base); await p.waitForFunction(() => document.getElementById('result-count').textContent === '54,564 results');
    await p.locator('#q').fill('ΕΚΤΩΡ');
    await p.waitForFunction(() => document.getElementById('result-count').textContent === '1 results');
    await p.locator('.row').click(); await p.getByRole('button',{name:'Retry passage',exact:true}).waitFor({state:'visible'});
    await p.getByRole('button',{name:'Retry passage',exact:true}).click();
    await p.waitForFunction(() => document.querySelectorAll('#detail mark').length === 5);
    await failure.close();
    // A slow, failing old passage must not replace a newer successful selection.
    const race = await browser.newContext(); const rp = await race.newPage();
    rp.on('pageerror',e => errors.push(e.message));
    let release;
    const held = new Promise(resolve => release = resolve);
    await rp.route('**/passages/148.json',async r => {await held; await r.fulfill({status:503,body:'Old request failed'});});
    await rp.goto(base); await rp.waitForFunction(() => document.getElementById('result-count').textContent === '54,564 results');
    await rp.locator('#q').fill('ΕΚΤΩΡ'); await rp.waitForFunction(() => document.querySelectorAll('.row').length === 1);
    await rp.locator('.row').click();
    await rp.locator('#q').fill('ΕΛΛΗΝΕΣ'); await rp.waitForFunction(() => document.querySelector('.row .word')?.textContent === 'ΕΛΛΗΝΕΣ');
    await rp.locator('.row').click(); await rp.waitForFunction(() => document.querySelectorAll('#detail mark').length === 7);
    release(); await rp.waitForLoadState('networkidle');
    assert.equal(await rp.locator('#detail h2').innerText(),'ΕΛΛΗΝΕΣ');
    await race.close();
    assert.deepEqual(errors,[]);
    const result = {url:base,browser:await browser.version(),desktop,mobile,mobileISO,recoveredPoems:recovered.map(r => r[0]),
      checks:['counts','lazy passages','paging','all sorts','combined filters','accented Greek search','keyboard selection','Homer reverse ΕΚΤΩΡ','Quintus second-letter ΕΛΛΗΝΕΣ','Euripides ΕΡΑΣΑΙ','literal wildcard search','AP8.39 both iota conventions','mobile layout','source link','methods and license','manifest failure recovery','index failure recovery','passage failure recovery','stale failed request ignored'],pageErrors:errors};
    fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
    await context.close();
  } finally {await browser.close();}
})().catch(e => {console.error(e.stack);process.exitCode=1;});
