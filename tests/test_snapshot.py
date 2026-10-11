"""Check export provenance, overwrite protection and reproduced-row comparison."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from build_dictionary import APPLICATION_ID, SCHEMA
from compare_snapshot import compare
from save_snapshot import export


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input.sqlite3'
        with sqlite3.connect(self.source) as db:
            db.executescript(SCHEMA)
            db.execute(f'PRAGMA application_id={APPLICATION_ID}')
            db.executemany('INSERT INTO metadata VALUES (?,?)', [
                ('pins', json.dumps([['fixture', 'https://example.org/corpus.git', 'test-revision']])),
                ('python', json.dumps('3.9.6'))])
            db.execute("INSERT INTO editions VALUES(1,'urn:test','Author','Title','fixture.xml','test-hash')")
            db.execute("INSERT INTO dictionary VALUES('ΑΒ',2,1,1)")
            for n, letter in enumerate('ΑΒΓ'):
                db.execute('INSERT INTO lines VALUES(1,?,?,?,?,?,?,?,?,?)',
                           (n, 'unit', None, str(n + 1), letter, letter, letter, '', 0))
            db.execute("INSERT INTO acrostics VALUES('forward',1,1,0,1,'ΑΒ',4.0)")

    def test_export_uses_recorded_provenance_and_referenced_passages(self):
        dest = self.root / 'export'
        result = export(self.source, dest)
        self.assertEqual(result['passages'], 2)
        pins = json.loads((dest / 'provenance/repositories.json').read_text())
        self.assertEqual(pins[0]['commit'], 'test-revision')
        self.assertEqual((dest / 'schema.sql').read_text(), SCHEMA)
        with sqlite3.connect(dest / 'results.sqlite3') as db:
            self.assertEqual(db.execute('SELECT word,log2_score FROM acrostic_results').fetchone(), ('ΑΒ', 4.0))
        before = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            export(self.source, dest)
        self.assertEqual(self.source.read_bytes(), before)
        with self.assertRaises(ValueError):
            export(dest / 'results.sqlite3', self.root / 'wrong')
        self.assertFalse((self.root / 'wrong').exists())

    def test_comparison_detects_score_changes_and_reports_python_versions(self):
        for folder in ('expected', 'actual'):
            export(self.source, self.root / folder)
        expected, actual = [self.root / folder / 'results.sqlite3' for folder in ('expected', 'actual')]
        with sqlite3.connect(actual) as db:
            db.execute("UPDATE metadata SET value=? WHERE key='python'", (json.dumps('3.12.0'),))
        report = compare(expected, actual)
        self.assertEqual(report['python_versions']['actual'], '3.12.0')
        self.assertEqual(report['tables_equal']['acrostic_results'], 1)
        with sqlite3.connect(actual) as db:
            db.execute('UPDATE acrostic_results SET log2_score=5.0')
        with self.assertRaisesRegex(AssertionError, 'acrostic_results: rows differ'):
            compare(expected, actual)


if __name__ == '__main__':
    unittest.main()
