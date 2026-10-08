"""Exercise real SQLite filtering and sorting without a browser or extra packages."""
from pathlib import Path
import sqlite3
import unittest
from html.parser import HTMLParser
from viewer import connect, results

ROOT = Path(__file__).resolve().parents[1]


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(ROOT / 'output/results.sqlite3')
        self.addCleanup(self.db.close)

    def test_direction_menu_contains_both_options(self):
        class Options(HTMLParser):
            def __init__(self):
                super().__init__()
                self.inside = False
                self.values = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'select':
                    self.inside = attrs.get('id') == 'direction'
                if tag == 'option' and self.inside:
                    self.values.append(attrs.get('value'))
            def handle_endtag(self, tag):
                if tag == 'select':
                    self.inside = False
        parser = Options()
        parser.feed((ROOT / 'viewer/index.html').read_text())
        self.assertEqual(parser.values, ['', 'forward', 'reverse'])

    def test_search_and_direction(self):
        data = results(self.db, {'q': 'ἐράσαι', 'direction': 'forward', 'position': '2'})
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['rows'][0]['title'], 'Ἑλένη')

    def test_sort_and_pagination(self):
        data = results(self.db, {'sort': 'score'})
        self.assertEqual(len(data['rows']), 50)
        scores = [r['log2_score'] for r in data['rows']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        second = results(self.db, {'page': '1'})
        self.assertNotEqual(data['rows'][0], second['rows'][0])
        self.assertGreaterEqual(scores[-1], second['rows'][0]['log2_score'])

    def test_whole_poem(self):
        data = results(self.db, {'kind': 'isopsephy', 'q': '8.39'})
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['rows'][0]['omit_totals'], '[6903, 6903]')
        self.assertEqual(data['rows'][0]['count_totals'], '[6903, 6913]')

    def test_queries_are_data_and_snapshot_read_only(self):
        self.assertEqual(results(self.db, {'q': "'; DROP TABLE editions;--"})['count'], 0)
        self.assertEqual(results(self.db, {'q': '%'})['count'], 0)
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute('DELETE FROM editions')
        self.assertEqual(results(self.db, {'q': 'no-such-word-qq'})['count'], 0)


if __name__ == '__main__':
    unittest.main()
