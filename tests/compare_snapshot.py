#!/usr/bin/env python3
"""Compare a reproduced snapshot with the included results, row by row."""
import argparse
import json
from pathlib import Path
import sqlite3


def compare(expected_path, actual_path):
    expected = sqlite3.connect(expected_path.resolve().as_uri() + '?mode=ro', uri=True)
    actual = sqlite3.connect(actual_path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        tables = []
        for db in (expected, actual):
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            tables.append([r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])
        assert tables[0] == tables[1], 'Table names differ'
        counts = {}
        for table in tables[0]:
            # Quote identifiers read from SQLite; values remain data.
            name = '"' + table.replace('"', '""') + '"'
            columns = [[r[1] for r in db.execute('PRAGMA table_info(' + name + ')')] for db in (expected, actual)]
            assert columns[0] == columns[1], f'{table}: columns differ'
            order = ','.join(str(i + 1) for i in range(len(columns[0])))
            where = " WHERE key != 'python'" if table == 'metadata' else ''
            query = 'SELECT * FROM ' + name + where + ' ORDER BY ' + order
            rows = [db.execute(query).fetchall() for db in (expected, actual)]
            assert rows[0] == rows[1], f'{table}: rows differ'
            counts[table] = len(rows[0])
        versions = [json.loads(db.execute("SELECT value FROM metadata WHERE key='python'").fetchone()[0])
                    for db in (expected, actual)]
        return {'tables_equal': counts, 'python_versions': dict(expected=versions[0], actual=versions[1])}
    finally:
        expected.close()
        actual.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--expected', type=Path, required=True)
    p.add_argument('--actual', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(compare(a.expected, a.actual), indent=2))


if __name__ == '__main__':
    main()
