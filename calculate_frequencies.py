#!/usr/bin/env python3
"""Count the selected Greek letter position across every eligible corpus line."""
import argparse
from collections import Counter
import json
from pathlib import Path
from corpus import LETTERS, open_database, position_index

ROOT = Path(__file__).resolve().parent


def calculate(db, position):
    index = position_index(position)
    counts = Counter()
    short = invalid = 0
    for row in db.execute('SELECT letters,issue FROM lines'):
        if row['issue']:
            invalid += 1
        elif len(row['letters']) < max(1, position):
            short += 1
        else:
            counts[row['letters'][index]] += 1
    total = sum(counts.values())
    if not total:
        raise ValueError('No eligible lines at this position')
    with db:
        # Delete dependent results: their scores would be stale after a recalculation.
        db.execute('DELETE FROM acrostics WHERE position=?', (position,))
        db.execute('DELETE FROM frequencies WHERE position=?', (position,))
        db.executemany('INSERT INTO frequencies VALUES (?,?,?,?,?)',
                       [(position, letter, counts[letter], total, counts[letter] / total) for letter in LETTERS])
        db.execute('INSERT OR REPLACE INTO frequency_runs VALUES (?,?,?,?)', (position, total, short, invalid))
    return {'position': position, 'eligible_lines': total, 'short_lines': short,
            'invalid_lines': invalid, 'counts': dict(sorted(counts.items()))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--position', type=int, required=True, help='Positive=start position; -1=final Greek letter')
    p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
    a = p.parse_args()
    with open_database(a.database) as db:
        print(json.dumps(calculate(db, a.position), ensure_ascii=False))


if __name__ == '__main__':
    main()
