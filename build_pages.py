#!/usr/bin/env python3
"""Build an allowlisted static viewer from the existing snapshot, without rescanning."""
import argparse
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parent
ACRO_COLUMNS = ['direction', 'position', 'edition_id', 'start_sequence', 'end_sequence',
                'word', 'log2_score', 'start_citation', 'end_citation', 'word_frequency', 'edition_count']
ISO_COLUMNS = ['edition_id', 'poem', 'group_size', 'convention', 'omit_totals', 'count_totals',
               'omit_lines', 'count_lines', 'author', 'citation', 'kind']
PASSAGE_COLUMNS = ['sequence', 'poem', 'citation', 'text', 'letters', 'issue', 'damaged']


def json_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')


def packed(db, table, columns, where='', parameters=(), order=''):
    return {'columns': columns, 'rows': [list(r) for r in db.execute(
        'SELECT ' + ','.join(columns) + ' FROM ' + table + where + order, parameters)]}


def build(destination, database=None, revision=None):
    database = (database or ROOT / 'output/results.sqlite3').resolve()
    destination = destination.resolve()
    # Never remove or overwrite a directory supplied by the caller.
    destination.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    revision = revision or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('A full source commit SHA is required')
    dataset = 'v1-' + digest[:16]
    data = destination / 'data' / dataset
    repos = json.loads((ROOT / 'provenance/repositories.json').read_text())
    pins = {r['directory']: r for r in repos}
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        # Preserve table order for SQLite's final ORDER BY ties in the local viewer.
        acrostics = packed(db, 'acrostic_results', ACRO_COLUMNS, order=' ORDER BY rowid')
        isopsephy = packed(db, 'isopsephy_results', ISO_COLUMNS, order=' ORDER BY edition_id,poem,group_size')
        editions = {}
        passage_count = 0
        for row in db.execute('SELECT * FROM editions WHERE id IN (SELECT DISTINCT edition_id FROM passages) ORDER BY id'):
            e = {k: row[k] for k in ['urn', 'author', 'title', 'source_path', 'sha256']}
            source = PurePosixPath(e['source_path'])
            if source.is_absolute() or '..' in source.parts or source.parts[0] not in pins:
                raise ValueError('Source path is not a pinned corpus-relative path')
            pin = pins[source.parts[0]]
            e['source_url'] = pin['url'].removesuffix('.git') + '/blob/' + pin['commit'] + '/' + '/'.join(source.parts[1:])
            editions[str(row['id'])] = e
            passage = packed(db, 'passages', PASSAGE_COLUMNS, ' WHERE edition_id=?', (row['id'],), ' ORDER BY sequence')
            passage_count += len(passage['rows'])
            json_file(data / 'passages' / (str(row['id']) + '.json'), passage)
        manifest = {'schema_version': 1, 'dataset': dataset, 'source_commit': revision,
                    'snapshot_sha256': digest, 'acrostics': len(acrostics['rows']),
                    'isopsephy': len(isopsephy['rows']), 'passages': passage_count,
                    'editions': len(editions), 'positions': [r[0] for r in db.execute('SELECT position FROM frequency_runs ORDER BY position')]}
        json_file(data / 'index.json', {'acrostics': acrostics, 'isopsephy': isopsephy, 'editions': editions})
        json_file(destination / 'attribution.json', {'repositories': repos, 'editions': editions,
                  'text_license': 'https://creativecommons.org/licenses/by-sa/4.0/',
                  'changes': 'Selected TEI readings and extracted passages; normalized Greek letters and research annotations added. See methods.html.'})
    json_file(destination / 'data' / 'manifest.json', manifest)
    # Explicit file allowlist: no repository directory, SQLite DB, logs, or PDFs are copied.
    for name in ['index.html', 'app.js', 'data.js', 'pages.css']:
        shutil.copyfile(ROOT / 'pages' / name, destination / name)
    shutil.copyfile(ROOT / 'viewer/style.css', destination / 'style.css')
    shutil.copyfile(ROOT / 'LICENSE', destination / 'LICENSE.txt')
    for name in ['First1KGreek-license.md', 'canonical-greekLit-license.md']:
        shutil.copyfile(ROOT / 'provenance' / name, destination / name)
    (destination / '.nojekyll').touch()
    source_link = 'https://github.com/zfletch/acrostics-simple/tree/' + revision
    template = (ROOT / 'pages/methods.html').read_text(encoding='utf-8')
    for key, value in {'COMMIT': revision, 'SNAPSHOT': digest, 'SOURCE_LINK': source_link,
                       'COUNTS': f"{manifest['acrostics']:,} acrostic candidates, {manifest['isopsephy']:,} isopsephy results, {passage_count:,} passage lines"}.items():
        template = template.replace('{{' + key + '}}', html.escape(value, quote=True))
    (destination / 'methods.html').write_text(template, encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site', help='New output directory; existing paths are refused')
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False))
