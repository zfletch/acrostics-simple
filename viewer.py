#!/usr/bin/env python3
"""Read-only, loopback-only viewer for the compact SQLite results snapshot."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlparse
from corpus import normalized

ROOT = Path(__file__).resolve().parent
FILES = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
         '/style.css': ('style.css', 'text/css'), '/letters.js': ('letters.js', 'text/javascript')}


def connect(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def results(db, args):
    kind = args.get('kind', 'acrostic')
    if kind not in {'acrostic', 'isopsephy'}:
        raise ValueError('Unknown result kind')
    table = 'acrostic_results' if kind == 'acrostic' else 'isopsephy_results'
    clauses, params = [], []
    query = args.get('q', '').strip()[:200]
    if query:
        literal = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pieces = ["author LIKE ? ESCAPE '\\'", "title LIKE ? ESCAPE '\\'"]
        params.extend(['%' + literal + '%'] * 2)
        if kind == 'acrostic':
            pieces.extend(["start_citation LIKE ? ESCAPE '\\'", "end_citation LIKE ? ESCAPE '\\'"])
            params.extend(['%' + literal + '%'] * 2)
            greek = normalized(query)
            if greek:
                pieces.append('word LIKE ?')
                params.append('%' + greek + '%')
        else:
            pieces.append("citation LIKE ? ESCAPE '\\'")
            params.append('%' + literal + '%')
        clauses.append('(' + ' OR '.join(pieces) + ')')
    for field in (['direction', 'position'] if kind == 'acrostic' else ['group_size']):
        if args.get(field):
            clauses.append(field + '=?')
            params.append(args[field] if field == 'direction' else int(args[field]))
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    order = {'score': 'log2_score DESC,word,edition_id,start_sequence',
             'word': 'word,log2_score DESC,edition_id,start_sequence',
             'author': 'author,title,edition_id,start_sequence',
             'location': 'urn,start_sequence,word'}
    sort = order.get(args.get('sort', 'score'), order['score']) if kind == 'acrostic' else 'urn,citation,group_size'
    page = max(0, int(args.get('page', 0)))
    count = db.execute('SELECT count(*) FROM ' + table + where, params).fetchone()[0]
    rows = [dict(r) for r in db.execute('SELECT * FROM ' + table + where + ' ORDER BY ' + sort + ' LIMIT 50 OFFSET ?', params + [page*50])]
    return {'count': count, 'page': page, 'rows': rows}


def handler(database):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed:
                self.send_error(403)
                return
            url = urlparse(self.path)
            try:
                if url.path in FILES:
                    filename, mime = FILES[url.path]
                    data = (ROOT / 'viewer' / filename).read_bytes()
                else:
                    args = {k: v[0] for k,v in parse_qs(url.query).items()}
                    db = connect(database)
                    try:
                        if url.path == '/api/results':
                            value = results(db, args)
                        elif url.path == '/api/stats':
                            value = {name: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                                     for name,table in [('acrostics','acrostic_results'),('isopsephy','isopsephy_results')]}
                            value['positions'] = [r[0] for r in db.execute('SELECT position FROM frequency_runs ORDER BY position')]
                        elif url.path == '/api/passage':
                            eid = int(args['edition_id'])
                            if 'poem' in args:
                                sql, values = 'poem=?', [int(args['poem'])]
                            else:
                                sql, values = 'sequence BETWEEN ? AND ?', [int(args['start']),int(args['end'])]
                            value = [dict(r) for r in db.execute('SELECT * FROM passages WHERE edition_id=? AND '+sql+' ORDER BY sequence LIMIT 1000', [eid]+values)]
                        else:
                            self.send_error(404)
                            return
                    finally:
                        db.close()
                    data, mime = json.dumps(value, ensure_ascii=False).encode(), 'application/json'
                self.send_response(200)
                self.send_header('Content-Type', mime + '; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(data)
            except (ValueError, KeyError):
                self.send_error(400, 'Invalid query')
        def log_message(self, *_):
            pass
    return Handler


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', type=Path, default=ROOT / 'output/results.sqlite3')
    p.add_argument('--port', type=int, default=8766)
    a = p.parse_args()
    with connect(a.database) as db:
        db.execute('SELECT count(*) FROM acrostic_results').fetchone()
    server = HTTPServer(('127.0.0.1', a.port), handler(a.database))
    print(f'Greek acrostics: http://127.0.0.1:{server.server_port} (Ctrl-C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
