#!/usr/bin/env python3
"""Local SQLite reference service for the frozen synthetic source API."""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlsplit
from openapi_schema_validator import OAS30Validator

ROOT = Path(__file__).resolve().parents[2]


def update_object(existing, changes):
    # Iterative implementation; does not import the inventory's recursive oracle.
    result = deepcopy(existing)
    queue = [(result, changes)]
    while queue:
        target, values = queue.pop()
        for name, value in values.items():
            if value is None:
                target.pop(name, None)
            elif isinstance(value, dict):
                if not isinstance(target.get(name), dict):
                    target[name] = {}
                queue.append((target[name], value))
            else:
                target[name] = deepcopy(value)
    return result


def serve(db, events, port, ready):
    spec = json.loads((ROOT / 'evidence/openapi-adapter-inputs-v1/openapi.json').read_text())
    creation = spec['paths']['/records']['post']['requestBody']['content']['application/json']['schema']
    update = spec['paths']['/records/{record_id}']['patch']['requestBody']['content']['application/json']['schema']
    defaults = {name: deepcopy(schema['default']) for name, schema in creation['properties'].items() if 'default' in schema}
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE records (id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body, raw):
            encoded = json.dumps(body, ensure_ascii=False).encode()
            with events.open('a') as stream:
                stream.write(json.dumps({'method': self.command, 'path': self.path, 'content_type': self.headers.get('Content-Type'), 'raw_body': raw.decode(errors='replace'), 'status': status, 'response': body}, ensure_ascii=False) + '\n')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers(); self.wfile.write(encoded)

        def dispatch(self):
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            path = urlsplit(self.path).path
            try:
                body = json.loads(raw) if raw else None
                with sqlite3.connect(db) as conn:
                    if self.command == 'POST' and path == '/__study/reset':
                        assert isinstance(body, dict) and isinstance(body['records'], dict)
                        conn.execute('DELETE FROM records')
                        for identity, data in body['records'].items():
                            conn.execute('INSERT INTO records VALUES (?, ?)', (identity, json.dumps(data)))
                        conn.commit(); self.respond(200, {'reset': True, 'records': len(body['records'])}, raw); return
                    if self.command == 'POST' and path == '/records':
                        if self.headers.get_content_type() != 'application/json':
                            self.respond(415, {'error': 'unsupported content type'}, raw); return
                        OAS30Validator(creation).validate(body)
                        if conn.execute('SELECT 1 FROM records WHERE id=?', ('created',)).fetchone():
                            self.respond(409, {'error': 'already created; reset required'}, raw); return
                        data = deepcopy(defaults); data.update(body); identity = 'created'; status = 201
                    elif path.startswith('/records/'):
                        identity = unquote(path[len('/records/'):])
                        row = conn.execute('SELECT data FROM records WHERE id=?', (identity,)).fetchone()
                        if row is None:
                            self.respond(404, {'error': 'not found'}, raw); return
                        data = json.loads(row[0])
                        if self.command == 'GET':
                            self.respond(200, {'id': identity, 'data': data}, raw); return
                        if self.command != 'PATCH':
                            self.respond(405, {'error': 'method not allowed'}, raw); return
                        if self.headers.get_content_type() not in ['application/json', 'application/merge-patch+json']:
                            self.respond(415, {'error': 'unsupported content type'}, raw); return
                        OAS30Validator(update).validate(body)
                        data = update_object(data, body); status = 200
                    else:
                        self.respond(404, {'error': 'not found'}, raw); return
                    conn.execute('INSERT OR REPLACE INTO records VALUES (?, ?)', (identity, json.dumps(data)))
                    conn.commit()
                    self.respond(status, {'id': identity, 'data': data}, raw)
            except Exception as error:
                from jsonschema.exceptions import ValidationError
                if isinstance(error, (ValidationError, ValueError, AssertionError, KeyError)):
                    self.respond(400, {'error': type(error).__name__, 'detail': str(error)}, raw)
                else:
                    self.respond(500, {'error': type(error).__name__, 'detail': str(error)}, raw)

        do_GET = dispatch
        do_POST = dispatch
        do_PATCH = dispatch

    server = HTTPServer(('127.0.0.1', port), Handler)
    ready.write_text(json.dumps({'host': '127.0.0.1', 'port': server.server_port}) + '\n')
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--ready', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    assert not args.db.exists(), 'Fresh database required'
    serve(args.db, args.events, args.port, args.ready)
