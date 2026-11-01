#!/usr/bin/env python3
"""Read-only, exhaustive comparison against the pre-fix full research database."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


def connect(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def rows(db, table, order=''):
    return [dict(r) for r in db.execute('SELECT * FROM ' + table + (' ORDER BY ' + order if order else ''))]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old', type=Path, required=True)
    p.add_argument('--new', type=Path, required=True)
    p.add_argument('--old-snapshot', type=Path, required=True)
    p.add_argument('--new-snapshot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    old, new = connect(a.old), connect(a.new)
    for db in [old, new]:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    unchanged = ['editions', 'dictionary', 'frequencies', 'frequency_runs', 'ingest_log']
    for table in unchanged:
        assert rows(old, table) == rows(new, table), table
    old_poems = {(r['edition_id'], r['poem']): r for r in rows(old, 'poems')}
    new_poems = {(r['edition_id'], r['poem']): r for r in rows(new, 'poems')}
    assert all(new_poems[k] == v for k, v in old_poems.items())
    added_poems = {k: v for k, v in new_poems.items() if k not in old_poems}
    assert len(added_poems) == 815
    editions = {r['id']: r for r in rows(new, 'editions')}
    assert all(editions[k[0]]['urn'] == 'urn:cts:greekLit:tlg7000.tlg001.perseus-grc6'
               and r['kind'] == 'chapter' for k, r in added_poems.items())
    line_changes, speaker_records = Counter(), []
    ol, nl = rows(old, 'lines', 'edition_id,sequence'), rows(new, 'lines', 'edition_id,sequence')
    assert len(ol) == len(nl)
    for before, after in zip(ol, nl):
        keys = [k for k in before if before[k] != after[k]]
        if not keys:
            continue
        line_changes[','.join(keys)] += 1
        if keys == ['poem']:
            assert before['poem'] is None and (after['edition_id'], after['poem']) in added_poems
        else:
            assert keys == ['issue'] and before['issue'] == 'no_greek_letters'
            assert after['issue'] == 'speaker_label_only' and after['citation'] in ['7.548.1', '7.548.4']
            speaker_records.append({k: after[k] for k in ['edition_id', 'sequence', 'citation', 'raw_text', 'issue']})
    assert len(speaker_records) == 2
    def delta(table, key):
        prior = {tuple(r[k] for k in key): r for r in rows(old, table)}
        current = {tuple(r[k] for k in key): r for r in rows(new, table)}
        removed = [v for k, v in prior.items() if k not in current]
        changed = [{'before': v, 'after': current[k]} for k, v in prior.items() if k in current and v != current[k]]
        added = [v for k, v in current.items() if k not in prior]
        return {'old_count': len(prior), 'new_count': len(current), 'added': added, 'removed': removed, 'changed': changed}
    acrostics = delta('acrostic_results', ['direction', 'position', 'edition_id', 'start_sequence', 'end_sequence', 'word'])
    assert not acrostics['removed'] and not acrostics['changed']
    assert len(acrostics['added']) == 1
    ac = acrostics['added'][0]
    assert (ac['word'], ac['direction'], ac['position'], ac['start_citation'], ac['end_citation']) == ('ΙΣΧΕ', 'forward', 2, '7.548.2', '7.548.6')
    iso = delta('isopsephy_results', ['edition_id', 'poem', 'group_size'])
    assert not iso['removed'] and not iso['changed']
    assert {r['citation'] for r in iso['added']} == {'6.321', '6.324', '6.325', '6.326', '6.327', '6.329', '7.548'}
    audit = delta('isopsephy_audit', ['group_size', 'edition_id', 'poem'])
    assert not audit['removed']
    transitions = Counter((r['before']['status'], r['after']['status']) for r in audit['changed'])
    for change in audit['changed']:
        r = change['after']
        change['citation'] = new_poems[(r['edition_id'], r['poem'])]['citation']
        change['urn'] = editions[r['edition_id']]['urn']
    audit['added_status_counts'] = dict(Counter(r['status'] for r in audit.pop('added')))
    audit['status_transitions'] = [{'before': b, 'after': n, 'count': c} for (b, n), c in sorted(transitions.items())]
    report = {'baseline_commit': '726b30e6533906d7a691aa3f01a80078015f0a89',
              'hashes': {k: digest(getattr(a, k)) for k in ['old', 'new', 'old_snapshot', 'new_snapshot']},
              'integrity': 'ok', 'unchanged_tables': unchanged, 'source_readings_changed': 0,
              'line_records': len(nl), 'line_changes': dict(line_changes), 'speaker_records': speaker_records,
              'recognized_chapter_epigrams': len(added_poems),
              'acrostics': acrostics, 'isopsephy': iso, 'isopsephy_audit': audit}
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'acrostics': [acrostics['old_count'], acrostics['new_count']],
                      'isopsephy': [iso['old_count'], iso['new_count']], 'line_changes': dict(line_changes),
                      'audit_transitions': audit['status_transitions'], 'hashes': report['hashes']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
