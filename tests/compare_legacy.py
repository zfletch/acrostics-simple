#!/usr/bin/env python3
"""Read-only comparison with the historical Python DB; no old table is rewritten."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sqlite3
import unicodedata as U


def legacy_letters(text):
    return ''.join(c.upper().replace('Ϲ', 'Σ').replace('Ͻ', 'Σ')
                   for c in U.normalize('NFD', text) if not U.combining(c)
                   and c.upper().replace('Ϲ', 'Σ').replace('Ͻ', 'Σ') in set('ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'))


def read(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def key(row):
    return (row['urn'], row['start_sequence'], row['end_sequence'], row['word'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy', type=Path, required=True)
    p.add_argument('--database', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    old, new = read(a.legacy), read(a.database)
    words = {r[0] for r in old.execute('SELECT normalized FROM word_forms WHERE length(normalized) BETWEEN 4 AND 12 AND frequency>=2')}
    new_words = {r[0] for r in new.execute('SELECT word FROM dictionary WHERE included=1')}
    old_lines, new_lines = defaultdict(list), defaultdict(list)
    for r in old.execute('SELECT e.urn,l.* FROM lines l JOIN editions e ON e.id=l.edition_id ORDER BY e.id,l.sequence'):
        old_lines[r['urn']].append(dict(r, letters=legacy_letters(r['text'])))
    for r in new.execute('SELECT e.urn,l.* FROM lines l JOIN editions e ON e.id=l.edition_id ORDER BY e.id,l.sequence'):
        new_lines[r['urn']].append(dict(r))
    lookup = {u: {r['sequence']: r for r in lines} for u, lines in new_lines.items()}
    report = {'historical_dictionary': {'stored_4_to_12_forms': old.execute('SELECT count(*) FROM word_forms').fetchone()[0],
                                      'searchable': len(words)},
              'new_dictionary': {'all_lengths': new.execute('SELECT count(*) FROM dictionary').fetchone()[0],
                                 'searchable': len(new_words), 'lost_eligible': len(words-new_words),
                                 'gained_eligible': len(new_words-words)}, 'searches': {}}
    old_lookup = {u: {r['sequence']: r for r in lines} for u, lines in old_lines.items()}
    changes = []
    for direction, position, table in [('forward', 1, 'candidates'), ('reverse', 1, 'reverse_candidates'),
                                       ('forward', 2, 'fixed_column_candidates'), ('reverse', 2, None)]:
        # Replay the historical window rules using their frozen lines and lexicon.
        baseline = set()
        for urn, lines in old_lines.items():
            for start, first in enumerate(lines):
                letters = []
                for line in lines[start:start+12]:
                    if line['container'] != first['container'] or len(line['letters']) < position:
                        break
                    letters.append(line['letters'][position-1])
                    word = ''.join(letters if direction == 'forward' else letters[::-1])
                    if len(letters) >= 4 and word in words:
                        baseline.add((urn, first['sequence'], line['sequence'], word))
        if table:
            archived = {tuple(r) for r in old.execute(f'SELECT e.urn,c.start_sequence,c.end_sequence,c.normalized FROM {table} c JOIN editions e ON e.id=c.edition_id')}
            assert baseline == archived, (direction, position, len(baseline ^ archived))
        current = {key(r) for r in new.execute('SELECT * FROM acrostic_results WHERE direction=? AND position=?', (direction, position))}
        reasons = Counter()
        for urn, start, end, word in sorted(baseline-current):
            rows = [lookup.get(urn, {}).get(i) for i in range(start, end+1)]
            if urn not in lookup:
                reason = 'edition_has_no_retained_verse'
            elif any(r is None for r in rows):
                reason = 'excluded_editorial_or_nested_line'
            elif any(r['issue'] for r in rows):
                reason = 'unusable_or_split_line'
            elif len({r['unit'] for r in rows}) != 1:
                reason = 'stricter_division_or_quote_boundary'
            elif any(len(r['letters']) < position for r in rows):
                reason = 'short_line'
            elif word not in new_words:
                reason = 'dictionary_count_changed'
            else:
                nums = [r['citation'].rsplit('.', 1)[-1] for r in rows]
                extracted = ''.join(r['letters'][position-1] for r in rows)
                if direction == 'reverse': extracted = extracted[::-1]
                if extracted != word:
                    reason = 'selected_reading_or_normalization_changed'
                elif any(x.isdecimal() and y.isdecimal() and int(y) != int(x)+1 for x,y in zip(nums,nums[1:])):
                    reason = 'line_number_discontinuity'
                else:
                    reason = 'UNEXPLAINED'
            reasons[reason] += 1
            changes.append({'direction': direction, 'position': position, 'change': 'removed', 'urn': urn,
                            'start_sequence': start, 'end_sequence': end, 'word': word, 'reason': reason})
        additions = Counter()
        for urn, start, end, word in sorted(current-baseline):
            if word not in words:
                reason = 'new_dictionary_eligibility'
            else:
                prior = [old_lookup.get(urn, {}).get(i) for i in range(start,end+1)]
                if any(r is None for r in prior):
                    reason = 'new_retained_line'
                else:
                    before = ''.join(r['letters'][position-1:position] for r in prior)
                    if direction == 'reverse': before = before[::-1]
                    assert before != word, ('Unexplained addition', urn, start, end, word)
                    reason = 'selected_reading_or_normalization_changed'
            additions[reason] += 1
            changes.append({'direction': direction, 'position': position, 'change': 'added', 'urn': urn,
                            'start_sequence': start, 'end_sequence': end, 'word': word, 'reason': reason})
        probabilities = {r['letter']: r['count']/r['total'] for r in new.execute('SELECT * FROM frequencies WHERE position=?', (position,))}
        for r in new.execute('SELECT word,log2_score FROM acrostics WHERE direction=? AND position=?', (direction,position)):
            expected = -math.log2(math.prod(probabilities[c] for c in r['word']))
            assert math.isclose(expected, r['log2_score'], abs_tol=1e-12)
        assert 'UNEXPLAINED' not in reasons, reasons
        report['searches'][f'{direction}_{position}'] = {
            'historical_rule_replay': len(baseline), 'archived_table_exactly_reproduced': bool(table),
            'current': len(current), 'shared': len(current & baseline),
            'removed': dict(reasons), 'added': dict(additions), 'all_current_scores_verified': True}
    a.output.mkdir(exist_ok=True, parents=True)
    (a.output / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    (a.output / 'candidate-differences.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
