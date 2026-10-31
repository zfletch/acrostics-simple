// Run the browser's actual data layer against the exported files without a server.
import fs from 'node:fs/promises';
import path from 'node:path';
const [root, source] = process.argv.slice(2);
const {createStore, normalized} = await import('data:text/javascript;base64,' + Buffer.from(await fs.readFile(source,'utf8')).toString('base64'));
const fetcher = async url => ({ok:true,json:async() => JSON.parse(await fs.readFile(path.join(root,url),'utf8'))});
const store = createStore('',fetcher);
let input = '';
for await (const chunk of process.stdin) input += chunk;
const {queries,passages,normalization} = JSON.parse(input);
const results = await Promise.all(queries.map(q => store.results(q)));
for (const result of results) for (const row of result.rows) delete row.source_url;
console.log(JSON.stringify({results,passages:await Promise.all(passages.map(q => store.passage(q))),normalized:normalization.map(normalized)}));
