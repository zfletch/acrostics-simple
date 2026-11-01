#!/usr/bin/env python3
"""Check delivered SQL results, every reading path, and documented corpus examples."""
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import SPEAKER_ONLY, line_boundary

ROOT = Path(__file__).resolve().parents[1]
db = sqlite3.connect((ROOT / 'output/research.sqlite3').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not db.execute('PRAGMA foreign_key_check').fetchall()
lines = {(r['edition_id'], r['sequence']): r for r in db.execute('SELECT * FROM lines')}
checked = 0
for r in db.execute('SELECT * FROM acrostics'):
    source_rows = [lines[(r['edition_id'], i)] for i in range(r['start_sequence'], r['end_sequence']+1)]
    assert all(not line_boundary(a,b) for a,b in zip(source_rows,source_rows[1:]))
    passage = [line for line in source_rows if line['issue'] != SPEAKER_ONLY]
    assert len({line['unit'] for line in passage}) == 1
    assert all(not line['issue'] and len(line['letters']) >= r['position'] for line in passage)
    reading = ''.join(line['letters'][r['position']-1] for line in passage)
    assert (reading if r['direction'] == 'forward' else reading[::-1]) == r['word']
    checked += 1
examples = [
    ('forward', 1, 'ΛΕΠΤΗ', 'urn:cts:greekLit:tlg0653.tlg001.perseus-grc2', '783', '787'),
    ('reverse', 1, 'ΕΚΤΩΡ', 'urn:cts:greekLit:tlg0012.tlg001.perseus-grc2', '6.511', '6.515'),
    ('forward', 2, 'ΕΛΛΗΝΕΣ', 'urn:cts:greekLit:tlg2046.tlg001.perseus-grc2', '7.502', '7.508'),
    ('forward', 2, 'ΕΡΑΣΑΙ', 'urn:cts:greekLit:tlg0006.tlg014.perseus-grc2', '3', '8'),
]
for row in examples:
    assert db.execute('SELECT 1 FROM acrostic_results WHERE direction=? AND position=? AND word=? AND urn=? AND start_citation=? AND end_citation=?', row).fetchone()
ap = dict(db.execute("SELECT * FROM isopsephy_results WHERE urn='urn:cts:greekLit:tlg7000.tlg001.perseus-grc7' AND citation='8.39' AND group_size=2").fetchone())
assert json.loads(ap['omit_totals']) == [6903, 6903]
assert json.loads(ap['count_totals']) == [6903, 6913]
result = {'integrity_check': 'ok', 'foreign_key_errors': 0, 'reading_paths_checked': checked,
          'known_examples': examples, 'ap8_39': ap}
(ROOT / 'output/corpus-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'reading_paths_checked': checked, 'known_examples': len(examples), 'AP8.39': 'passed'}))
