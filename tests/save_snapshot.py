#!/usr/bin/env python3
"""Export results, the processing schema and source manifests into a new directory."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_dictionary import APPLICATION_ID, SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def export(database, destination):
    source = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        if source.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
            raise ValueError('Expected a full database created by build_dictionary.py')
        pins = json.loads(source.execute("SELECT value FROM metadata WHERE key='pins'").fetchone()[0])
        destination.mkdir(parents=True, exist_ok=False)
        path = destination / 'results.sqlite3'
        out = sqlite3.connect(path)
        try:
            for table in ['metadata', 'editions', 'frequencies', 'frequency_runs', 'acrostic_results',
                          'isopsephy_results', 'isopsephy_audit', 'ingest_log']:
                cur = source.execute('SELECT * FROM ' + table)
                columns = [col[0] for col in cur.description]
                out.execute('CREATE TABLE ' + table + '(' + ','.join(columns) + ')')
                out.executemany('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in columns) + ')', cur)
            keys = set()
            for eid, start, end in source.execute('SELECT edition_id,start_sequence,end_sequence FROM acrostics'):
                keys.update((eid, n) for n in range(start, end + 1))
            poems = {(r[0], r[1]) for r in source.execute('SELECT edition_id,poem FROM isopsephy')}
            columns = ['edition_id', 'sequence', 'poem', 'citation', 'text', 'letters', 'issue', 'damaged']
            out.execute('CREATE TABLE passages (' + ','.join(columns) + ', PRIMARY KEY(edition_id,sequence))')
            for row in source.execute('SELECT * FROM lines ORDER BY edition_id,sequence'):
                if (row['edition_id'], row['sequence']) in keys or (row['edition_id'], row['poem']) in poems:
                    out.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?)', tuple(row[c] for c in columns))
            out.execute('CREATE INDEX acrostic_rank ON acrostic_results(direction,position,log2_score DESC)')
            out.commit()
            assert out.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            count = out.execute('SELECT count(*) FROM passages').fetchone()[0]
        finally:
            out.close()
        (destination / 'schema.sql').write_text(SCHEMA, encoding='utf-8')
        provenance = destination / 'provenance'
        provenance.mkdir()
        editions = [dict(r) for r in source.execute('SELECT * FROM editions ORDER BY id')]
        repositories = [dict(directory=name, url=url, commit=commit) for name, url, commit in pins]
        for name, value in [('edition-manifest', editions), ('repositories', repositories)]:
            (provenance / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return {'snapshot_bytes': path.stat().st_size, 'passages': count}
    finally:
        source.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
    p.add_argument('--output-dir', type=Path, default=ROOT / 'output/new-snapshot')
    a = p.parse_args()
    print(json.dumps(export(a.database, a.output_dir)))


if __name__ == '__main__':
    main()
