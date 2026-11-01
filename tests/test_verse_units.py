"""Regression tests for source-declared epigrams and nonmetrical speaker records."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from build_dictionary import SCHEMA
from calculate_frequencies import calculate
from corpus import CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER, SPEAKER_ONLY, extract
from search_forward import search as forward
from search_reverse import search as reverse
from search_isopsephy import search as isopsephy

FIXTURES = Path(__file__).parent / 'fixtures'
LABEL = '<label type="speaker">α.</label>'
SPEECH = (f'<l n="1">{LABEL}</l><l n="2">α</l><l n="3">β</l>'
          f'<l n="4">{LABEL}</l><l n="5">β</l><l n="6">α</l>')


class VerseUnitTests(unittest.TestCase):
    def load(self, parsed):
        _, poems, lines = parsed
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        db.execute("INSERT INTO editions VALUES(1,'fixture','Test','Fixture','fixture.xml','test')")
        db.executemany('INSERT INTO poems VALUES(?,?,?,?,?,?)', [(1, p, *v) for p, v in poems.items()])
        db.executemany('INSERT INTO lines VALUES(?,?,?,?,?,?,?,?,?,?)', [(1, *r) for r in lines])
        self.addCleanup(db.close)
        return db

    def parse(self, body, urn='urn:fixture', pointer=None):
        refs = '' if pointer is None else ('<encodingDesc><refsDecl n="CTS">'
            f'<cRefPattern n="epigram" replacementPattern="{pointer}"/>'
            '</refsDecl></encodingDesc>')
        xml = (f'<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>{refs}</teiHeader>'
               f'<text><body><div type="edition" n="{urn}">{body}</div></body></text></TEI>')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fixture.xml'
            p.write_text(xml)
            return extract(p)

    def speech(self, text=SPEECH):
        return self.load(self.parse(f'<div subtype="epigram" n="1">{text}</div>'))

    def acrostics(self, db):
        db.execute("INSERT INTO dictionary VALUES('ΑΒΒΑ',2,1,1)")
        calculate(db, 1)
        return forward(db, 1), reverse(db, 1)

    def test_actual_ap7548_and_neighbor_controls(self):
        db = self.load(extract(FIXTURES / 'ap-7-source.xml'))
        isopsephy(db, 2)
        results = {r['citation']: dict(r) for r in db.execute('SELECT * FROM isopsephy_results')}
        self.assertEqual(set(results), {'7.547', '7.548'})
        self.assertEqual(results['7.547']['convention'], 'count_only')
        self.assertEqual(json.loads(results['7.547']['count_totals']), [7267, 7267])
        r = results['7.548']
        self.assertEqual(r['convention'], 'omit_only')
        self.assertEqual(json.loads(r['omit_lines']), [3880, 3270, 4844, 2306])
        self.assertEqual(json.loads(r['count_totals']), [7160, 7150])
        rows = list(db.execute('SELECT * FROM lines WHERE poem=? ORDER BY sequence', (r['poem'],)))
        self.assertEqual([x['citation'] for x in rows], [f'7.548.{i}' for i in range(1, 7)])
        self.assertEqual([x['issue'] for x in rows], [SPEAKER_ONLY, '', '', SPEAKER_ONLY, '', ''])
        self.assertEqual(rows[0]['raw_text'], 'α.')
        self.assertIn('Δαίμων', rows[1]['text'])  # Never substitute a critical reading.
        db.execute("INSERT INTO dictionary VALUES('ΙΣΧΕ',2,1,1)")
        calculate(db, 2)
        self.assertEqual(forward(db, 2), 1)
        self.assertEqual(reverse(db, 2), 0)
        self.assertEqual(tuple(db.execute('SELECT word,start_citation,end_citation FROM acrostic_results').fetchone()),
                         ('ΙΣΧΕ', '7.548.2', '7.548.6'))
        for citation in ['7.549', '7.550']:
            self.assertEqual(db.execute('SELECT status FROM isopsephy_audit a JOIN poems p USING(edition_id,poem) WHERE p.citation=?', (citation,)).fetchone()[0], 'tested')

    def test_actual_book6_declared_epigrams(self):
        db = self.load(extract(FIXTURES / 'ap-6-source.xml'))
        isopsephy(db, 1)
        isopsephy(db, 2)
        expected = {'6.321': (2, 'count_only', 5699), '6.324': (2, 'count_only', 9117),
                    '6.325': (2, 'both', 5953), '6.326': (2, 'both', 5982),
                    '6.327': (1, 'both', 4111), '6.329': (2, 'count_only', 7579)}
        rows = list(db.execute('SELECT * FROM isopsephy_results'))
        self.assertEqual(len(rows), 6)
        for r in rows:
            group, convention, value = expected[r['citation']]
            self.assertEqual((r['group_size'], r['convention']), (group, convention))
            self.assertEqual(json.loads(r['count_totals']), [value, value])
            self.assertEqual(r['kind'], 'chapter')  # Original encoding remains visible.

    def test_only_declared_edition_and_hierarchy_get_chapter_poems(self):
        chapter = '<div subtype="chapter" n="1"><l n="1">α</l><l n="2">α</l></div>'
        book = f'<div subtype="book" n="6">{chapter}</div>'
        good = self.parse(book, CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER)
        self.assertEqual(len(good[1]), 1)
        for body, urn, pointer in [
            (book, 'urn:other', EPIGRAM_POINTER), (book, CHAPTER_EPIGRAM_EDITION, None),
            (book, CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER.replace("[@n='$2']", "[@n='$3']")),
            (chapter, CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER),
            (f'<div subtype="book" n="6"><div>{chapter}</div></div>', CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER),
            (f'<div subtype="book">{chapter}</div>', CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER)]:
            with self.subTest(body=body, urn=urn, pointer=pointer):
                parsed = self.parse(body, urn, pointer)
                self.assertFalse(parsed[1])
                self.assertTrue(all(r[2] is None for r in parsed[2]))

    def test_speaker_records_are_skipped_without_losing_original_endpoints(self):
        db = self.speech()
        self.assertEqual(self.acrostics(db), (1, 1))
        self.assertEqual([tuple(r) for r in db.execute('SELECT start_sequence,end_sequence FROM acrostics')], [(1, 5), (1, 5)])
        self.assertEqual(isopsephy(db, 2)['matches'], 1)
        self.assertEqual(json.loads(db.execute('SELECT omit_lines FROM isopsephy').fetchone()[0]), [1, 2, 2, 1])

    def test_inline_speaker_label_does_not_erase_a_real_line(self):
        db = self.speech(SPEECH.replace('<l n="3">β</l>', f'<l n="3">{LABEL}β</l>'))
        r = db.execute("SELECT * FROM lines WHERE citation='1.3'").fetchone()
        self.assertEqual((r['text'], r['letters'], r['issue']), ('β', 'Β', ''))
        self.assertEqual(self.acrostics(db), (1, 1))
        self.assertEqual(isopsephy(db, 2)['matches'], 1)

    def test_empty_editorial_or_incomplete_lines_are_not_speaker_exceptions(self):
        bad = ['', '...', 'Latin', '<label>α.</label>', '<label type="speaker"/>',
               LABEL+'<gap/>', LABEL+'<note>missing</note>', LABEL+'<unclear/>',
               '<label type="speaker"><supplied>α.</supplied></label>']
        for content in bad:
            with self.subTest(content=content):
                text = SPEECH.replace(f'<l n="4">{LABEL}</l>', f'<l n="4">{content}</l>')
                db = self.speech(text)
                self.assertNotEqual(db.execute("SELECT issue FROM lines WHERE citation='1.4'").fetchone()[0], SPEAKER_ONLY)
                self.assertEqual(self.acrostics(db), (0, 0))
                self.assertEqual(isopsephy(db, 2)['matches'], 0)
        for part in ['I', 'M', 'F']:
            db = self.speech(SPEECH.replace('<l n="4">', f'<l n="4" part="{part}">'))
            self.assertEqual(self.acrostics(db), (0, 0))
            self.assertEqual(isopsephy(db, 2)['matches'], 0)

    def test_labels_cannot_bridge_numbering_or_xml_gaps(self):
        for field, value, expected in [('citation', '1.8', 'line_number_discontinuity'),
                                       ('sequence', 20, 'xml_line_discontinuity')]:
            db = self.speech()
            db.execute(f'UPDATE lines SET {field}=? WHERE sequence=3', (value,))
            self.assertEqual(self.acrostics(db), (0, 0))
            self.assertEqual(isopsephy(db, 2)['matches'], 0)
            self.assertEqual(db.execute('SELECT status FROM isopsephy_audit').fetchone()[0], expected)

    def test_whole_poem_checks_leading_and_trailing_speaker_adjacency(self):
        for text in [SPEECH.replace('n="1"', 'n="0"', 1), SPEECH+f'<l n="8">{LABEL}</l>']:
            db = self.speech(text)
            self.assertEqual(isopsephy(db, 2)['matches'], 0)
            self.assertEqual(db.execute('SELECT status FROM isopsephy_audit').fetchone()[0], 'line_number_discontinuity')

    def test_nested_divisions_remain_boundaries(self):
        text = SPEECH.replace(f'<l n="4">{LABEL}</l>', f'<div><l n="4">{LABEL}</l>')+'</div>'
        db = self.speech(text)
        self.assertEqual(self.acrostics(db), (0, 0))
        self.assertEqual(isopsephy(db, 2)['matches'], 0)
        self.assertEqual(db.execute('SELECT status FROM isopsephy_audit').fetchone()[0], 'unit_boundary')

    def test_damaged_verse_and_prose_chapter_still_fail_isopsephy(self):
        db = self.speech(SPEECH.replace('<l n="3">β</l>', '<l n="3"><supplied>β</supplied></l>'))
        self.assertEqual(isopsephy(db, 2)['matches'], 0)
        body = '<div subtype="book" n="6"><div subtype="chapter" n="1"><p>prose</p><l n="1">α</l><l n="2">α</l></div></div>'
        db = self.load(self.parse(body, CHAPTER_EPIGRAM_EDITION, EPIGRAM_POINTER))
        self.assertEqual(isopsephy(db, 1)['matches'], 0)
        self.assertEqual(db.execute('SELECT status FROM isopsephy_audit').fetchone()[0], 'prose_paragraph')


if __name__ == '__main__':
    unittest.main()
