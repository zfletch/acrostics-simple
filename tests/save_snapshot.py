#!/usr/bin/env python3
"""Export a portable result-only database and source provenance after a new run."""
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_dictionary import SCHEMA
from corpus import SPEAKER_ONLY

ROOT = Path(__file__).resolve().parents[1]
source = sqlite3.connect((ROOT / 'output/research.sqlite3').as_uri() + '?mode=ro', uri=True)
source.row_factory = sqlite3.Row
path = ROOT / 'output/results.sqlite3'
with path.open('xb'):
    pass
out = sqlite3.connect(path)
for table in ['metadata', 'editions', 'frequencies', 'frequency_runs', 'acrostic_results',
              'isopsephy_results', 'isopsephy_audit', 'ingest_log']:
    cur = source.execute('SELECT * FROM ' + table)
    columns = [col[0] for col in cur.description]
    out.execute('CREATE TABLE ' + table + '(' + ','.join(columns) + ')')
    out.executemany('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in columns) + ')', cur)
keys = set()
for eid, start, end in source.execute('SELECT edition_id,start_sequence,end_sequence FROM acrostics'):
    keys.update((eid, n) for n in range(start, end+1))
poems = {(r[0],r[1]) for r in source.execute('SELECT edition_id,poem FROM isopsephy')}
columns = ['edition_id','sequence','poem','citation','text','letters','issue','damaged']
out.execute('CREATE TABLE passages (' + ','.join(columns) + ', PRIMARY KEY(edition_id,sequence))')
for row in source.execute('SELECT * FROM lines ORDER BY edition_id,sequence'):
    if row['issue'] == SPEAKER_ONLY:
        continue  # Source records remain in the full DB; render metrical lines only.
    if (row['edition_id'],row['sequence']) in keys or (row['edition_id'],row['poem']) in poems:
        out.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?)', tuple(row[c] for c in columns))
out.execute('CREATE INDEX acrostic_rank ON acrostic_results(direction,position,log2_score DESC)')
out.commit()
assert out.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
(ROOT / 'output/schema.sql').write_text(SCHEMA)
(ROOT / 'provenance/edition-manifest.json').write_text(json.dumps([dict(r) for r in source.execute('SELECT * FROM editions ORDER BY id')], ensure_ascii=False, indent=2)+'\n')
(ROOT / 'provenance/repositories.json').write_text((ROOT / 'corpora/repositories.json').read_text())
print(json.dumps({'snapshot_bytes': path.stat().st_size, 'passages': out.execute('SELECT count(*) FROM passages').fetchone()[0]}))
