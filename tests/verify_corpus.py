#!/usr/bin/env python3
"""Check delivered SQL results, every reading path, and documented corpus examples."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
p.add_argument('--output', type=Path, help='Optional JSON report; stdout is always available')
a = p.parse_args()
db = sqlite3.connect(a.database.resolve().as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not db.execute('PRAGMA foreign_key_check').fetchall()
lines = {(r['edition_id'], r['sequence']): r for r in db.execute('SELECT * FROM lines')}
probabilities = {}
for run in db.execute('SELECT * FROM frequency_runs'):
    position = run['position']
    eligible = [r for r in lines.values() if not r['issue'] and len(r['letters']) >= position]
    counts = Counter(r['letters'][position - 1] for r in eligible)
    assert len(eligible) == run['eligible_lines']
    assert sum(bool(r['issue']) for r in lines.values()) == run['invalid_lines']
    assert len(lines) - len(eligible) - run['invalid_lines'] == run['short_lines']
    for r in db.execute('SELECT * FROM frequencies WHERE position=?', (position,)):
        assert r['count'] == counts[r['letter']] and r['total'] == len(eligible)
        assert r['probability'] == counts[r['letter']] / len(eligible)
        probabilities[position, r['letter']] = r['count'] / r['total']
words = {r[0] for r in db.execute('SELECT word FROM dictionary WHERE included=1')}
checked = 0
for r in db.execute('SELECT * FROM acrostics'):
    passage = [lines[(r['edition_id'], i)] for i in range(r['start_sequence'], r['end_sequence']+1)]
    assert len({line['unit'] for line in passage}) == 1
    assert all(not line['issue'] and len(line['letters']) >= r['position'] for line in passage)
    reading = ''.join(line['letters'][r['position']-1] for line in passage)
    assert (reading if r['direction'] == 'forward' else reading[::-1]) == r['word']
    assert r['word'] in words
    for before, after in zip(passage, passage[1:]):
        x, y = before['citation'].rsplit('.', 1)[-1], after['citation'].rsplit('.', 1)[-1]
        assert not (x.isdecimal() and y.isdecimal()) or int(y) == int(x) + 1
    expected = -math.log2(math.prod(probabilities[r['position'], c] for c in r['word']))
    assert math.isclose(expected, r['log2_score'], rel_tol=0, abs_tol=1e-12)
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
          'scores_checked': checked, 'frequency_positions_checked': sorted({p for p, c in probabilities}),
          'known_examples': examples, 'ap8_39': ap}
if a.output:
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
db.close()
