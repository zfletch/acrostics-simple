"""Hand-sized independent fixtures; run: python3 -m unittest discover -s tests -v."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import unicodedata

from build_dictionary import SCHEMA
from calculate_frequencies import calculate
from corpus import extract, normalized, tokens, open_database
from search_forward import search as forward
from search_reverse import search as reverse
from search_isopsephy import equal_groups, search as isopsephy, total


class SimpleTests(unittest.TestCase):
    def database(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript(SCHEMA)
        db.execute("INSERT INTO editions VALUES(1,'urn:fixture','Test','Fixture','fixture.xml','test')")
        self.addCleanup(db.close)
        return db

    def lines(self, db, texts, units=None, sequences=None, issues=None, poem=None, eid=1):
        for i, text in enumerate(texts):
            db.execute('INSERT INTO lines VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (eid, sequences[i] if sequences else i, units[i] if units else 'one',
                        poem, str(i + 1), text, text, normalized(text), issues[i] if issues else '', 0))

    def test_normalization(self):
        self.assertEqual(normalized('Ἄ ᾠ ς ϲ, β!'), 'ΑΩΣΣΒ')
        self.assertEqual(normalized('ᾠ ῳ \u1fbe', True), 'ΩΙΩΙΙ')
        self.assertEqual(normalized('αβ 12 Latin'), 'ΑΒ')
        self.assertEqual(tokens('ἄνδρες, ὦ· παῖδες'), ['ΑΝΔΡΕΣ', 'Ω', 'ΠΑΙΔΕΣ'])
        self.assertEqual(tokens('κἀγώ'), ['ΚΑΓΩ'])
        self.assertEqual(tokens('α\u1fbeβ'), ['ΑΒ'])
        self.assertEqual(tokens('ἄνδρες'), tokens(unicodedata.normalize('NFD', 'ἄνδρες')))

    def test_forward_reverse_and_exact_score(self):
        db = self.database()
        self.lines(db, ['ἀν', 'βο', 'γο', 'δς'])
        for word in ['ΑΒΓΔ', 'ΔΓΒΑ', 'ΝΟΟΣ', 'ΣΟΟΝ']:
            db.execute('INSERT INTO dictionary VALUES(?,2,1,1)', (word,))
        f = calculate(db, 1)
        self.assertEqual(f['counts'], {'Α': 1, 'Β': 1, 'Γ': 1, 'Δ': 1})
        self.assertEqual(forward(db, 1), 1)
        self.assertEqual(reverse(db, 1), 1)
        self.assertEqual([r[0] for r in db.execute('SELECT log2_score FROM acrostics')], [8, 8])
        calculate(db, 2)
        self.assertEqual(forward(db, 2), 1)
        self.assertEqual(reverse(db, 2), 1)
        self.assertEqual(db.execute("SELECT log2_score FROM acrostics WHERE word='ΝΟΟΣ'").fetchone()[0], 6)

    def test_telestics_use_final_letters_and_separate_frequencies(self):
        db = self.database()
        self.lines(db, ['ἀν!', 'βο;', 'γο', 'δς·'])
        for word in ['ΑΒΓΔ', 'ΔΓΒΑ', 'ΝΟΟΣ', 'ΣΟΟΝ']:
            db.execute('INSERT INTO dictionary VALUES(?,2,1,1)', (word,))
        calculate(db, 1)
        forward(db, 1)
        reverse(db, 1)
        with self.assertRaises(ValueError):
            forward(db, -1)  # Initial-letter probabilities are insufficient.
        f = calculate(db, -1)
        self.assertEqual(f['counts'], {'Ν': 1, 'Ο': 2, 'Σ': 1})
        self.assertEqual(forward(db, -1), 1)
        self.assertEqual(reverse(db, -1), 1)
        self.assertEqual([tuple(r) for r in db.execute('SELECT word,log2_score FROM acrostics WHERE position=-1 ORDER BY word')], [('ΝΟΟΣ',6),('ΣΟΟΝ',6)])
        calculate(db, -1)
        self.assertEqual(db.execute('SELECT count(*) FROM acrostics WHERE position=-1').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT count(*) FROM acrostics WHERE position=1').fetchone()[0], 2)
        for position in [-2, -3, 0]:
            for action in [calculate, forward, reverse]:
                with self.assertRaises(ValueError):
                    action(db, position)

    def test_telestics_respect_barriers_and_source_boundaries(self):
        for kwargs in [dict(units=['a','a','b','b']), dict(sequences=[0,1,3,4]),
                       dict(issues=['','','split_line',''])]:
            db = self.database()
            self.lines(db, ['ωα','ωβ','ωγ','ωδ'], **kwargs)
            for word in ['ΑΒΓΔ','ΔΓΒΑ']:
                db.execute('INSERT INTO dictionary VALUES(?,2,1,1)', (word,))
            calculate(db,-1)
            self.assertEqual(forward(db,-1),0)
            self.assertEqual(reverse(db,-1),0)

    def test_short_line_is_a_barrier(self):
        db = self.database()
        self.lines(db, ['αα', 'β', 'γβ', 'δγ', 'εδ'])
        db.execute("INSERT INTO dictionary VALUES('ΑΒΓΔ',2,1,1)")
        f = calculate(db, 2)
        self.assertEqual((f['eligible_lines'], f['short_lines']), (4, 1))
        self.assertEqual(forward(db, 2), 0)
        self.assertEqual(reverse(db, 2), 0)
        with self.assertRaises(ValueError):
            calculate(db, 0)
        with self.assertRaises(ValueError):
            calculate(db, 100)
        with self.assertRaises(ValueError):
            forward(db, 0)

    def test_units_gaps_and_invalid_lines_break_windows(self):
        for kwargs in [dict(units=['a', 'a', 'b', 'b']),
                       dict(sequences=[0, 1, 3, 4]),
                       dict(issues=['', '', 'split_line', ''])]:
            db = self.database()
            self.lines(db, ['α', 'β', 'γ', 'δ'], **kwargs)
            db.execute("INSERT INTO dictionary VALUES('ΑΒΓΔ',2,1,1)")
            calculate(db, 1)
            self.assertEqual(forward(db, 1), 0)

    def test_editions_never_join_and_nonwords_not_emitted(self):
        db = self.database()
        self.lines(db, ['α', 'β'])
        db.execute("INSERT INTO editions VALUES(2,'urn:other','Test','Other','other.xml','test')")
        self.lines(db, ['γ', 'δ'], eid=2)
        db.execute("INSERT INTO dictionary VALUES('ΑΒΓΔ',2,1,1)")
        calculate(db, 1)
        self.assertEqual(forward(db, 1), 0)

    def test_xml_boundaries_and_reading(self):
        xml = '''<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt>
        <title>T</title><author>A</author></titleStmt></fileDesc></teiHeader><text><body>
        <div type="edition" n="urn:test"><div subtype="epigram" n="1">
        <l n="1">α<note>β<l>χ</l></note>γ<app><lem>δ</lem><rdg>ω</rdg></app>
        <choice><sic>ζ</sic><corr>ε</corr></choice><lb/>ν</l><l n="2" part="I">ἄν</l></div>
        <div subtype="epigram" n="1"><l n="1">β</l><l n="2">...</l></div>
        </div></body></text></TEI>'''
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'test.xml'
            path.write_text(xml)
            _, poems, lines = extract(path)
        self.assertEqual(len(poems), 2)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0][6], 'ΑΓΔΕΝ')
        self.assertNotEqual(lines[0][1], lines[2][1])
        self.assertEqual(lines[1][7], 'split_line')
        self.assertEqual(lines[3][7], 'no_greek_letters')

    def test_numerical_values_and_explicit_iota(self):
        self.assertEqual(total('αβγ'), 6)
        self.assertEqual(total('αʼ βʹ'), 3)
        self.assertEqual(total('ϛ ϝ ϟ ϙ ϡ'), 1092)
        self.assertEqual(total('νηῷ'), 858)
        self.assertEqual(total('νηῷ', True), 868)
        self.assertEqual(total('νηωι'), 868)
        with self.assertRaises(ValueError):
            total('alpha')
        self.assertEqual(equal_groups([1, 2, 3, 0], 2), ([3, 3], True))
        self.assertFalse(equal_groups([1, 2], 2)[1])
        self.assertFalse(equal_groups([0, 0], 1)[1])

    def test_ap839_genuine_search_and_iota_conventions(self):
        db = self.database()
        db.execute("INSERT INTO poems VALUES(1,39,'8.39','epigram','Gregory','')")
        self.lines(db, [
            'εὐχαί τε στοναχαί τε φίλαι καὶ νύκτες ἄυπνοι,',
            'καὶ νηοῖο πέδον δάκρυσι δευόμενον,',
            'σοί, Νόννα ζαθέη, τοίην βιότοιο τελευτὴν',
            'ὤπασαν, ἐν νηῷ ψῆφον ἑλεῖν θανάτου.'], poem=39)
        result = isopsephy(db, 2)
        self.assertEqual(result['matches'], 1)
        row = db.execute('SELECT * FROM isopsephy').fetchone()
        self.assertEqual(row['convention'], 'omit_only')
        self.assertEqual(json.loads(row['omit_totals']), [6903, 6903])
        self.assertEqual(json.loads(row['count_totals']), [6903, 6913])

    def test_equal_window_in_longer_poem_is_not_a_whole_poem_hit(self):
        db = self.database()
        db.execute("INSERT INTO poems VALUES(1,1,'1','poem','Test','')")
        self.lines(db, ['α', 'β', 'α', 'β', 'δ', 'ε'], poem=1)
        # The first two pairs each sum to 3; the third sums to 9.
        self.assertEqual(isopsephy(db, 2)['matches'], 0)
        self.assertEqual(db.execute('SELECT status FROM isopsephy_audit').fetchone()[0], 'tested')

    def test_numbering_gap_is_a_barrier(self):
        db = self.database()
        self.lines(db, ['α', 'β', 'γ', 'δ'])
        db.execute("UPDATE lines SET citation='7' WHERE sequence=2")
        db.execute("INSERT INTO dictionary VALUES('ΑΒΓΔ',2,1,1)")
        calculate(db, 1)
        self.assertEqual(forward(db, 1), 0)

    def test_new_isopsephic_fixture_is_found(self):
        db = self.database()
        db.execute("INSERT INTO poems VALUES(1,8,'8','poem','Test','')")
        self.lines(db, ['αβ', 'γ'], poem=8)
        self.assertEqual(isopsephy(db, 1)['matches'], 1)
        self.assertEqual(db.execute('SELECT convention FROM isopsephy').fetchone()[0], 'both')

    def test_unknown_database_is_not_modified(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'unrelated.sqlite3'
            sqlite3.connect(path).close()
            with self.assertRaises(ValueError):
                open_database(path)


if __name__ == '__main__':
    unittest.main()
