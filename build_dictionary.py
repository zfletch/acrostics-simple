#!/usr/bin/env python3
"""Read pinned TEI verse, preserve boundaries, and build a corpus word-form list."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from corpus import extract, tokens
from download_corpora import PINS

ROOT = Path(__file__).resolve().parent
APPLICATION_ID = 1094931027
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE editions(id INTEGER PRIMARY KEY, urn TEXT UNIQUE, author TEXT, title TEXT,
                      source_path TEXT, sha256 TEXT);
CREATE TABLE poems(edition_id INTEGER REFERENCES editions, poem INTEGER, citation TEXT,
                   kind TEXT, author TEXT, issue TEXT, PRIMARY KEY(edition_id,poem));
CREATE TABLE lines(edition_id INTEGER REFERENCES editions, sequence INTEGER, unit TEXT,
                   poem INTEGER, citation TEXT, raw_text TEXT, text TEXT, letters TEXT,
                   issue TEXT, damaged INTEGER, PRIMARY KEY(edition_id,sequence));
CREATE INDEX lines_poem ON lines(edition_id,poem);
CREATE TABLE dictionary(word TEXT PRIMARY KEY, frequency INTEGER, edition_count INTEGER,
                        included INTEGER);
CREATE TABLE ingest_log(source_path TEXT, status TEXT, detail TEXT);
CREATE TABLE frequencies(position INTEGER, letter TEXT, count INTEGER, total INTEGER,
                         probability REAL, PRIMARY KEY(position,letter));
CREATE TABLE frequency_runs(position INTEGER PRIMARY KEY, eligible_lines INTEGER,
                            short_lines INTEGER, invalid_lines INTEGER);
CREATE TABLE acrostics(direction TEXT, position INTEGER, edition_id INTEGER REFERENCES editions,
                       start_sequence INTEGER, end_sequence INTEGER, word TEXT,
                       log2_score REAL, PRIMARY KEY(direction,position,edition_id,start_sequence,end_sequence,word));
CREATE TABLE isopsephy(edition_id INTEGER, poem INTEGER, group_size INTEGER,
                      convention TEXT, omit_totals TEXT, count_totals TEXT,
                      omit_lines TEXT, count_lines TEXT,
                      PRIMARY KEY(edition_id,poem,group_size));
CREATE TABLE isopsephy_audit(group_size INTEGER, edition_id INTEGER, poem INTEGER, status TEXT,
                            PRIMARY KEY(group_size,edition_id,poem));
CREATE VIEW acrostic_results AS
SELECT a.*,e.urn,e.author,e.title,s.citation AS start_citation,t.citation AS end_citation,
       e.source_path,d.frequency AS word_frequency,d.edition_count
FROM acrostics a JOIN editions e ON e.id=a.edition_id
JOIN lines s ON s.edition_id=a.edition_id AND s.sequence=a.start_sequence
JOIN lines t ON t.edition_id=a.edition_id AND t.sequence=a.end_sequence
JOIN dictionary d ON d.word=a.word;
CREATE VIEW isopsephy_results AS
SELECT i.*,e.urn,e.title,p.author,p.citation,p.kind,e.source_path
FROM isopsephy i JOIN editions e ON e.id=i.edition_id
JOIN poems p ON p.edition_id=i.edition_id AND p.poem=i.poem;
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpora', type=Path, default=ROOT / 'corpora')
    p.add_argument('--database', type=Path, default=ROOT / 'output/research.sqlite3')
    p.add_argument('--min-length', type=int, default=4)
    p.add_argument('--max-length', type=int, default=12)
    p.add_argument('--min-frequency', type=int, default=2)
    a = p.parse_args()
    if not 1 <= a.min_length <= a.max_length or a.min_frequency < 1:
        p.error('Require 1 <= min-length <= max-length and min-frequency >= 1')
    # Verify the actual repository bytes belong to the recorded clean revisions.
    for name, _, commit in PINS:
        folder = a.corpora / name
        def git(*args):
            return subprocess.check_output(['git', '-C', str(folder), *args], text=True).strip()
        if git('rev-parse', 'HEAD') != commit or git('status', '--porcelain'):
            p.error(f'{folder} is not the clean pinned revision')
    a.database.parent.mkdir(parents=True, exist_ok=True)
    # Never unlink or overwrite a previous run, especially the original databases.
    with a.database.open('xb'):
        pass
    db = sqlite3.connect(a.database)
    db.executescript(SCHEMA)
    db.execute(f'PRAGMA application_id={APPLICATION_ID}')
    settings = {'pins': PINS, 'min_length': a.min_length, 'max_length': a.max_length,
                'min_frequency': a.min_frequency, 'normalization': 'NFD; omit subscript; uppercase; fold sigma',
                'scope': 'All Greek <l> elements in selected Greek-named XML editions; no primary-edition filter',
                'python': sys.version.split()[0]}
    db.executemany('INSERT INTO metadata VALUES (?,?)',
                   [(k, json.dumps(v, ensure_ascii=False)) for k, v in settings.items()])
    frequencies, documents = Counter(), Counter()
    seen = set()
    for name, _, _ in PINS:
        for path in sorted((a.corpora / name).rglob('*.xml')):
            if '-grc' not in path.name and '.grc' not in path.name:
                continue
            source = str(path.relative_to(a.corpora))
            try:
                parsed = extract(path)
            except (ET.ParseError, ValueError) as error:
                db.execute('INSERT INTO ingest_log VALUES (?,?,?)', (source, 'rejected', str(error)))
                continue
            if parsed is None or not parsed[2]:
                db.execute('INSERT INTO ingest_log VALUES (?,?,?)', (source, 'no_verse', ''))
                continue
            edition, poems, lines = parsed
            if edition['urn'] in seen:
                db.execute('INSERT INTO ingest_log VALUES (?,?,?)', (source, 'duplicate_urn', edition['urn']))
                continue
            seen.add(edition['urn'])
            eid = db.execute('INSERT INTO editions(urn,author,title,source_path,sha256) VALUES (?,?,?,?,?)',
                             (edition['urn'], edition['author'], edition['title'], source,
                              hashlib.sha256(path.read_bytes()).hexdigest())).lastrowid
            db.executemany('INSERT INTO poems VALUES (?,?,?,?,?,?)', [(eid, key, *data) for key, data in poems.items()])
            db.executemany('INSERT INTO lines VALUES (?,?,?,?,?,?,?,?,?,?)', [(eid, *line) for line in lines])
            vocabulary = []
            for line in lines:
                if not line[7]:
                    vocabulary.extend(tokens(line[5]))
            frequencies.update(vocabulary)
            documents.update(set(vocabulary))
            db.execute('INSERT INTO ingest_log VALUES (?,?,?)', (source, 'included', edition['urn']))
    db.executemany('INSERT INTO dictionary VALUES (?,?,?,?)',
                   [(word, count, documents[word], int(a.min_length <= len(word) <= a.max_length and count >= a.min_frequency))
                    for word, count in sorted(frequencies.items())])
    db.commit()
    print(json.dumps({'database': str(a.database), 'editions': len(seen),
                      'lines': db.execute('SELECT count(*) FROM lines').fetchone()[0],
                      'word_forms': len(frequencies),
                      'included_words': db.execute('SELECT sum(included) FROM dictionary').fetchone()[0]}))
    db.close()


if __name__ == '__main__':
    main()
