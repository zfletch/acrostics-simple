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
        self.assertEqual((self.manifest['acrostics'],self.manifest['isopsephy'],count),(27470,20,71764))
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(),self.digest)

    def test_only_public_allowlist_and_resolving_relative_links(self):
        allowed = {'index.html','app.js','data.js','style.css','pages.css','methods.html','LICENSE.txt',
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
                for position in ['', '1','2']:
                    for page in [0,1,7]: queries.append(dict(sort=sort,direction=direction,position=position,page=page))
        for q in ['ἐράσαι','ΕΚΤΩΡ','Ἕλληνες','Homer','HOMER','Quintus','6.511','Ἰλιάς','%','_',"'; DROP TABLE editions;--",'no-such-word-qq']:
            for direction in ['', 'forward','reverse']: queries.append(dict(q=q,direction=direction))
        for q in ['', '8.39','11.87','Gregorius','%']:
            for group in ['',1,2]: queries.append(dict(kind='isopsephy',q=q,group_size=group))
        passages = [{'edition_id':r['edition_id'],'start':r['start_sequence'],'end':r['end_sequence']} for r in self.db.execute("SELECT * FROM acrostic_results WHERE word IN ('ΕΚΤΩΡ','ΕΛΛΗΝΕΣ','ΕΡΑΣΑΙ')")]
        passages += [{'edition_id':r['edition_id'],'poem':r['poem']} for r in self.db.execute('SELECT * FROM isopsephy_results')]
        texts = ['ᾧ','ω\u0345','ῳ','῾Ι','ι','ϲϹϽϐϑϰϱϕϖ','Ἑλλῆνες','ᾠδή','Ιι','ſß','ʼʹʹ','hello','%']
        request = dict(queries=queries,passages=passages,normalization=texts)
        process = subprocess.run(['node',str(ROOT/'tests/static_data.mjs'),str(self.site),str(ROOT/'pages/data.js')], input=json.dumps(request),text=True,capture_output=True,check=True)
        actual = json.loads(process.stdout)
        self.assertEqual(actual['normalized'],[normalized(t) for t in texts])
        for args,answer in zip(queries,actual['results']):
            with self.subTest(args=args): self.assertEqual(answer,results(self.db,args))
        for args,lines in zip(passages,actual['passages']):
            where,params = ('poem=?',[args['poem']]) if 'poem' in args else ('sequence BETWEEN ? AND ?',[args['start'],args['end']])
            expected = [dict(r) for r in self.db.execute('SELECT * FROM passages WHERE edition_id=? AND '+where+' ORDER BY sequence LIMIT 1000',[args['edition_id']]+params)]
            self.assertEqual(lines,expected)


if __name__ == '__main__': unittest.main()
