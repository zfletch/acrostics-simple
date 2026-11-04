#!/usr/bin/env python3
"""Find dictionary words reading the selected line position from top to bottom."""
import argparse
import json
import math
from pathlib import Path
from corpus import metrical_lines, open_database, position_index

ROOT = Path(__file__).resolve().parent
DIRECTION = 'forward'


def search(db, position):
    index = position_index(position)
    probabilities = {r['letter']: r['probability'] for r in
                     db.execute('SELECT * FROM frequencies WHERE position=?', (position,))}
    if not probabilities:
        raise ValueError('Run calculate_frequencies.py for this position first')
    words = {r[0] for r in db.execute('SELECT word FROM dictionary WHERE included=1')}
    longest = max(map(len, words), default=0)
    shortest = min(map(len, words), default=0)
    matches = []
    for edition in db.execute('SELECT id FROM editions ORDER BY id'):
        lines = list(metrical_lines(db.execute('SELECT * FROM lines WHERE edition_id=? ORDER BY sequence', (edition[0],))))
        for start, (first, _) in enumerate(lines):
            letters = []
            for end in range(start, min(start + longest, len(lines))):
                line, barrier = lines[end]
                if (line['unit'] != first['unit'] or line['issue'] or
                        len(line['letters']) < max(1, position) or
                        (end > start and barrier)):
                    break
                letters.append(line['letters'][index])
                if len(letters) < shortest:
                    continue
                word = ''.join(letters)
                if word in words:
                    # log2(1/product(p)) = -sum(log2(p)); indicator is 1 here.
                    log_score = -sum(math.log2(probabilities[c]) for c in word)
                    matches.append((DIRECTION, position, edition[0], first['sequence'],
                                    line['sequence'], word, log_score))
    with db:
        db.execute('DELETE FROM acrostics WHERE direction=? AND position=?', (DIRECTION, position))
        db.executemany('INSERT INTO acrostics VALUES (?,?,?,?,?,?,?)', matches)
    return len(matches)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--position', type=int, required=True, help='1=first Greek letter, 2=second, etc.; -1=final Greek letter')
    p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
    a = p.parse_args()
    with open_database(a.database) as db:
        count = search(db, a.position)
    print(json.dumps({'direction': DIRECTION, 'position': a.position, 'matches': count}))


if __name__ == '__main__':
    main()
