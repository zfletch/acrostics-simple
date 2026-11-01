#!/usr/bin/env python3
"""Find whole encoded poems whose successive equal-size line groups have equal sums."""
import argparse
from collections import Counter
import json
from pathlib import Path
from corpus import SPEAKER_ONLY, VALUES, line_boundary, normalized, open_database

ROOT = Path(__file__).resolve().parent


def total(text, count_iota=False):
    return sum(VALUES[c] for c in normalized(text, count_iota=count_iota, numeric=True))


def equal_groups(values, group_size):
    if group_size < 1:
        raise ValueError('Group size must be at least 1')
    if len(values) < 2 * group_size or len(values) % group_size:
        return [], False
    sums = [sum(values[i:i + group_size]) for i in range(0, len(values), group_size)]
    return sums, sums[0] > 0 and len(set(sums)) == 1


def search(db, group_size):
    if group_size < 1:
        raise ValueError('Group size must be at least 1')
    results, audit = [], []
    for poem in db.execute('SELECT * FROM poems ORDER BY edition_id,poem'):
        eid, pid = poem['edition_id'], poem['poem']
        lines = list(db.execute('SELECT * FROM lines WHERE edition_id=? AND poem=? ORDER BY sequence', (eid, pid)))
        status = poem['issue']
        if not status and any((r['issue'] and r['issue'] != SPEAKER_ONLY) or r['damaged'] for r in lines):
            status = 'uncertain_or_incomplete_line'
        if not status:
            for before, after in zip(lines, lines[1:]):
                status = line_boundary(before, after)
                if status:
                    break
        # Speaker records remain in the database and continuity checks above,
        # but are not metrical lines or numerical groups.
        lines = [r for r in lines if r['issue'] != SPEAKER_ONLY]
        if not status and (len(lines) < 2 * group_size or len(lines) % group_size):
            status = 'ineligible_line_count'
        if status:
            audit.append((group_size, eid, pid, status))
            continue
        try:
            omit = [total(r['text']) for r in lines]
            count = [total(r['text'], True) for r in lines]
        except ValueError:
            audit.append((group_size, eid, pid, 'unsupported_alphabetic_character'))
            continue
        omit_sums, omit_equal = equal_groups(omit, group_size)
        count_sums, count_equal = equal_groups(count, group_size)
        audit.append((group_size, eid, pid, 'tested'))
        if omit_equal or count_equal:
            convention = 'both' if omit_equal and count_equal else 'omit_only' if omit_equal else 'count_only'
            results.append((eid, pid, group_size, convention, json.dumps(omit_sums),
                            json.dumps(count_sums), json.dumps(omit), json.dumps(count)))
    with db:
        db.execute('DELETE FROM isopsephy WHERE group_size=?', (group_size,))
        db.execute('DELETE FROM isopsephy_audit WHERE group_size=?', (group_size,))
        db.executemany('INSERT INTO isopsephy VALUES (?,?,?,?,?,?,?,?)', results)
        db.executemany('INSERT INTO isopsephy_audit VALUES (?,?,?,?)', audit)
    return {'group_size': group_size, 'matches': len(results), 'poems': dict(Counter(r[-1] for r in audit))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--group-size', type=int, default=2, help='2 compares successive line-pairs; 1 compares individual lines')
    p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
    a = p.parse_args()
    with open_database(a.database) as db:
        print(json.dumps(search(db, a.group_size)))


if __name__ == '__main__':
    main()
