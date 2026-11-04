"""Check source-position mapping against every published passage, including Unicode."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SourceLetterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for viewer highlighting checks')
    def test_source_maps_and_corner_highlights(self):
        with sqlite3.connect((ROOT/'output/results.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory = sqlite3.Row
            passages = [dict(r) for r in db.execute('SELECT text,letters FROM passages')]
        run = subprocess.run(['node',str(ROOT/'tests/source_letters.cjs')],input=json.dumps({'passages':passages}),text=True,capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['passagesChecked'],113571)
