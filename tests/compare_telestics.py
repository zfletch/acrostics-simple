#!/usr/bin/env python3
"""Audit a fresh telestic scan against a pre-telestic result snapshot."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--database', type=Path, default=Path('output/research.sqlite3'))
p.add_argument('--snapshot', type=Path, default=Path('output/results.sqlite3'))
p.add_argument('--output', type=Path, default=Path('output/telestics-comparison.json'))
a = p.parse_args()
def connect(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory = sqlite3.Row
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    return db
old, full, new = map(connect,[a.baseline,a.database,a.snapshot])
def records(db, table, where=''):
    return {tuple(row) for row in db.execute('SELECT * FROM '+table+' '+where)}
preserved = {}
for table in ['editions','ingest_log','isopsephy_results','isopsephy_audit']:
    before = records(old,table)
    assert before == records(new,table) == records(full,table),table
    preserved[table] = len(before)
for table in ['frequencies','frequency_runs','acrostic_results']:
    before = records(old,table)
    assert before == records(new,table,'WHERE position>0') == records(full,table,'WHERE position>0'),table
    preserved[table] = len(before)
assert records(old,'metadata') == records(new,'metadata') == records(full,'metadata')
old_passages, new_passages = records(old,'passages'), records(new,'passages')
assert old_passages <= new_passages
preserved['passages'] = len(old_passages)
counts = Counter(row['letters'][-1] for row in full.execute("SELECT letters FROM lines WHERE issue='' AND length(letters)>0"))
total = sum(counts.values())
for row in new.execute('SELECT * FROM frequencies WHERE position=-1'):
    assert row['count'] == counts[row['letter']] and row['total'] == total
    assert row['probability'] == counts[row['letter']] / total
for row in new.execute('SELECT * FROM acrostic_results WHERE position=-1'):
    score = -sum(math.log2(counts[c]/total) for c in row['word'])
    assert row['log2_score'] == score
assert {r[0] for r in new.execute('SELECT position FROM frequency_runs')} == {-1,1,2}
assert records(full,'acrostic_results') == records(new,'acrostic_results')
keys = set()
for r in full.execute('SELECT edition_id,start_sequence,end_sequence FROM acrostics'):
    keys.update((r[0],n) for n in range(r[1],r[2]+1))
poems = set(full.execute('SELECT edition_id,poem FROM isopsephy'))
poems = {tuple(r) for r in poems}
columns = [r[1] for r in new.execute('PRAGMA table_info(passages)')]
expected = {tuple(r[c] for c in columns) for r in full.execute('SELECT * FROM lines')
            if r['issue'] != 'speaker_label_only' and ((r['edition_id'],r['sequence']) in keys or (r['edition_id'],r['poem']) in poems)}
assert new_passages == expected
result = {
    'baseline_sha256':hashlib.sha256(a.baseline.read_bytes()).hexdigest(),
    'snapshot_sha256':hashlib.sha256(a.snapshot.read_bytes()).hexdigest(),
    'preserved_unchanged':preserved,
    'ingest_statuses':dict(full.execute('SELECT status,count(*) FROM ingest_log GROUP BY status')),
    'editions':full.execute('SELECT count(*) FROM editions').fetchone()[0],
    'line_records':full.execute('SELECT count(*) FROM lines').fetchone()[0],
    'included_dictionary_words':full.execute('SELECT count(*) FROM dictionary WHERE included=1').fetchone()[0],
    'telestic_eligible_lines':total,
    'telestics_by_direction':dict(new.execute('SELECT direction,count(*) FROM acrostic_results WHERE position=-1 GROUP BY direction')),
    'telestic_scores_independently_verified':new.execute('SELECT count(*) FROM acrostic_results WHERE position=-1').fetchone()[0],
    'snapshot_passages_exactly_match_full_run':len(new_passages),
    'existing_results_removed':0,
    'unsupported_end_positions':[],
}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
