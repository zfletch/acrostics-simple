"""Verify published content and browser queries against the unchanged SQLite viewer."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from urllib.parse import urlsplit, unquote

from build_pages import build, ROOT, ACRO_COLUMNS, ISO_COLUMNS, PASSAGE_COLUMNS
from corpus import normalized
from viewer import connect, results


def unpack(packed):
    return [dict(zip(packed['columns'], r)) for r in packed['rows']]


class PagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.site = Path(cls.temp.name) / 'acrostics-simple'
        cls.database = ROOT / 'output/results.sqlite3'
        cls.digest = hashlib.sha256(cls.database.read_bytes()).hexdigest()
        cls.manifest = build(cls.site)
        cls.data = cls.site / 'data' / cls.manifest['dataset']

    def setUp(self):
        self.db = connect(self.database)
        self.addCleanup(self.db.close)

    def test_every_exported_result_and_passage_matches_snapshot(self):
        index = json.loads((self.data / 'index.json').read_text())
        for key, table, columns in [('acrostics','acrostic_results',ACRO_COLUMNS),('isopsephy','isopsephy_results',ISO_COLUMNS)]:
            actual = unpack(index[key])
            expected = [dict(r) for r in self.db.execute('SELECT '+','.join(columns)+' FROM '+table)]
            serial = lambda rows: sorted(json.dumps(r,sort_keys=True,ensure_ascii=False) for r in rows)
            self.assertEqual(serial(actual),serial(expected))
            self.assertEqual(len(actual), self.manifest[key])
        count = 0
        for eid, edition in index['editions'].items():
            lines = unpack(json.loads((self.data / 'passages' / (eid+'.json')).read_text()))
            expected = [dict(r) for r in self.db.execute('SELECT '+','.join(PASSAGE_COLUMNS)+' FROM passages WHERE edition_id=? ORDER BY sequence',(int(eid),))]
            self.assertEqual(lines,expected)
            source = dict(self.db.execute('SELECT * FROM editions WHERE id=?',(int(eid),)).fetchone())
            for key in ['urn','author','title','source_path','sha256']: self.assertEqual(edition[key],source[key])
            self.assertTrue(edition['source_url'].startswith('https://github.com/'))
            count += len(lines)
        self.assertEqual(count,self.db.execute('SELECT count(*) FROM passages').fetchone()[0])
        self.assertEqual((self.manifest['acrostics'],self.manifest['isopsephy'],count),(54564,27,113571))
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(),self.digest)

    def test_gamma_match_index_uses_correct_word_and_vertical_edge(self):
        from corpus import tokens
        index = json.loads((self.data / 'index.json').read_text())
        expected = {'first3': [], 'whole': []}
        passages = {(r['edition_id'], r['sequence']): r['text'] for r in self.db.execute('SELECT * FROM passages')}
        for i, row in enumerate(unpack(index['acrostics'])):
            if row['position'] not in (1, -1):
                continue
            telestic = row['position'] == -1
            if telestic:
                edge = row['end_sequence'] if row['direction'] == 'forward' else row['start_sequence']
                horizontal = tokens(passages[row['edition_id'], edge])[-1]
                match = len(horizontal) >= 3 and row['word'][-3:] == horizontal[-3:]
            else:
                edge = row['start_sequence'] if row['direction'] == 'forward' else row['end_sequence']
                horizontal = tokens(passages[row['edition_id'], edge])[0]
                match = len(horizontal) >= 3 and row['word'][:3] == horizontal[:3]
            if match:
                expected['first3'].append(i)
                if row['word'] == horizontal:
                    expected['whole'].append(i)
        self.assertEqual(index['gamma_matches'], expected)
        rows = unpack(index['acrostics'])
        self.assertEqual(sum(rows[i]['position'] == -1 for i in expected['first3']), 583)
        self.assertEqual(sum(rows[i]['position'] == -1 for i in expected['whole']), 4)

    def test_gamma_corner_counterexamples_and_whole_word(self):
        from build_pages import gamma_matches
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE passages(edition_id,sequence,text)')
        rows = []
        for direction in ['forward','reverse']:
            for position in [1,-1,2]:
                eid = len(rows)+1
                edge = 10 if (direction == 'forward') == (position == 1) else 13
                text = 'ἀβγδ δεύτερον' if position == 1 else 'πρῶτον ἀβγδ'
                db.execute('INSERT INTO passages VALUES(?,?,?)',(eid,edge,text))
                db.execute('INSERT INTO passages VALUES(?,?,?)',(eid,13 if edge==10 else 10,'ξένον ξένον'))
                rows.append([direction,position,eid,10,13,'ΑΒΓΔ'])
        exact = gamma_matches(db,{'rows':rows})
        self.assertEqual(exact,{'first3':[0,1,3,4],'whole':[0,1,3,4]})
        db.execute("UPDATE passages SET text=replace(text,'ἀβγδ','ὠβγδ') WHERE edition_id IN (2,5)")
        suffix = gamma_matches(db,{'rows':rows})
        self.assertEqual(suffix['first3'],[0,1,3,4])
        self.assertEqual(suffix['whole'],[0,3])
        db.execute("UPDATE passages SET text='πρῶτον γδ' WHERE edition_id IN (2,5)")
        self.assertEqual(gamma_matches(db,{'rows':rows}),{'first3':[0,3],'whole':[0,3]})

    def test_only_public_allowlist_and_resolving_relative_links(self):
        allowed = {'index.html','app.js','data.js','letters.js','style.css','pages.css','methods.html','LICENSE.txt',
                   'First1KGreek-license.md','canonical-greekLit-license.md','attribution.json','.nojekyll'}
        self.assertEqual({p.name for p in self.site.iterdir() if p.is_file()},allowed)
        self.assertEqual({p.name for p in self.site.iterdir() if p.is_dir()},{'data'})
        links = []
        class Links(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for name,value in attrs:
                    if name in {'src','href'}: links.append(value)
        for name in ['index.html','methods.html']: Links().feed((self.site/name).read_text())
        for link in links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path: continue
            self.assertFalse(url.path.startswith('/'),link)
            self.assertTrue((self.site/unquote(url.path)).exists(),link)
        for p in self.site.rglob('*'):
            self.assertFalse(p.is_symlink())
            if not p.is_file(): continue
            self.assertNotIn(p.suffix,{'.pdf','.sqlite3','.py','.zip'})
            self.assertNotIn('/Users/',p.read_text())
        self.assertIn('MIT License',(self.site/'LICENSE.txt').read_text())
        self.assertIn('CC BY-SA 4.0',(self.site/'methods.html').read_text())

    def test_refuses_existing_destination(self):
        with self.assertRaises(FileExistsError): build(self.site)

    @unittest.skipUnless(shutil.which('node'),'Node.js is required for browser-query parity')
    def test_javascript_queries_match_python_viewer(self):
        queries = []
        for sort in ['score','word','author','location']:
            for direction in ['', 'forward','reverse']:
                for position in ['', '1','2','-1']:
                    for page in [0,1,7]: queries.append(dict(sort=sort,direction=direction,position=position,page=page))
        for q in ['ἐράσαι','ΕΚΤΩΡ','Ἕλληνες','Homer','HOMER','Quintus','6.511','Ἰλιάς','%','_',"'; DROP TABLE editions;--",'no-such-word-qq']:
            for direction in ['', 'forward','reverse']: queries.append(dict(q=q,direction=direction))
        for q in ['', '8.39','11.87','7.548','6.321','6.327','6.329','Gregorius','%']:
            for group in ['',1,2]: queries.append(dict(kind='isopsephy',q=q,group_size=group))
        for match in ['first3', 'whole']:
            for direction in ['', 'forward', 'reverse']:
                for sort in ['score', 'word']:
                    for position in ['', '1', '-1', '2']:
                        queries.append(dict(shape='gamma',gamma_match=match,direction=direction,position=position,sort=sort))
        passages = [{'edition_id':r['edition_id'],'start':r['start_sequence'],'end':r['end_sequence']} for r in self.db.execute("SELECT * FROM acrostic_results WHERE word IN ('ΕΚΤΩΡ','ΕΛΛΗΝΕΣ','ΕΡΑΣΑΙ','ΙΣΧΕ')")]
        passages += [{'edition_id':r['edition_id'],'poem':r['poem']} for r in self.db.execute('SELECT * FROM isopsephy_results')]
        texts = ['ᾧ','ω\u0345','ῳ','῾Ι','ι','ϲϹϽϐϑϰϱϕϖ','Ἑλλῆνες','ᾠδή','Ιι','ſß','ʼʹʹ','hello','%']
        request = dict(queries=queries,passages=passages,normalization=texts)
        process = subprocess.run(['node',str(ROOT/'tests/static_data.mjs'),str(self.site),str(ROOT/'pages/data.js')], input=json.dumps(request),text=True,capture_output=True,check=True)
        actual = json.loads(process.stdout)
        self.assertEqual(actual['normalized'],[normalized(t) for t in texts])
        match_indexes = json.loads((self.data / 'index.json').read_text())['gamma_matches']
        for args,answer in zip(queries,actual['results']):
            with self.subTest(args=args):
                if args.get('shape') == 'gamma':
                    unfiltered = results(self.db,{k:v for k,v in args.items() if k not in {'shape','gamma_match'}})
                    # Compare the total and the actual returned rows independently against SQLite.
                    candidates = [dict(r) for r in self.db.execute(
                        'SELECT '+','.join(ACRO_COLUMNS)+' FROM acrostic_results ORDER BY rowid')]
                    selected_indexes = set(match_indexes[args['gamma_match']])
                    eligible = {(r['direction'],r['position'],r['edition_id'],r['start_sequence'],
                                 r['end_sequence'],r['word']) for i,r in enumerate(candidates)
                                if i in selected_indexes}
                    sql_rows = [dict(r) for r in self.db.execute('SELECT * FROM acrostic_results')]
                    filtered = [r for r in sql_rows if
                                (r['direction'],r['position'],r['edition_id'],r['start_sequence'],
                                 r['end_sequence'],r['word']) in eligible and
                                (not args.get('direction') or r['direction']==args['direction']) and
                                (not args.get('position') or r['position']==int(args['position']))]
                    self.assertEqual(answer['count'], len(filtered))
                    self.assertEqual(len(answer['rows']), min(50, len(filtered)))
                    self.assertTrue(all(r['position'] in (1,-1) for r in answer['rows']))
                    sort_fields = [('log2_score',-1),('word',1),('edition_id',1),('start_sequence',1)] if args['sort']=='score' else [('word',1),('log2_score',-1),('edition_id',1),('start_sequence',1)]
                    for key, direction in reversed(sort_fields):
                        filtered.sort(key=lambda r:r[key],reverse=direction < 0)
                    self.assertEqual(answer['rows'], filtered[:50])
                    self.assertTrue(all((r['direction'],r['position'],r['edition_id'],r['start_sequence'],
                                         r['end_sequence'],r['word']) in eligible for r in answer['rows']))
                else:
                    self.assertEqual(answer,results(self.db,args))
        for args,lines in zip(passages,actual['passages']):
            where,params = ('poem=?',[args['poem']]) if 'poem' in args else ('sequence BETWEEN ? AND ?',[args['start'],args['end']])
            expected = [dict(r) for r in self.db.execute('SELECT * FROM passages WHERE edition_id=? AND '+where+' ORDER BY sequence LIMIT 1000',[args['edition_id']]+params)]
            self.assertEqual(lines,expected)


if __name__ == '__main__': unittest.main()
