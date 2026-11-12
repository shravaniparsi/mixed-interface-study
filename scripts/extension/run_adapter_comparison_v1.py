#!/usr/bin/env python3
"""Frozen paired source-versus-MCP comparison over real HTTP and SQLite."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import subprocess
import sys
import threading
import time
from jsonschema.validators import validator_for
from calibrate_adapter_reference_v1 import request, typed

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:8765'

def normalize(name):
    return re.sub('[^a-z0-9]', '', name.lower())

class Client:
    def __init__(self, command, folder):
        self.log = (folder / 'mcp-stderr.log').open('w')
        self.wire = (folder / 'mcp-stdio.jsonl').open('w')
        self.messages = queue.Queue(); self.serial = 0
        env = dict(os.environ, STUDY_SPEC=str(ROOT / 'evidence/openapi-adapter-inputs-v1/openapi.json'))
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, env=env)
        self.reader = threading.Thread(target=self.read, daemon=True); self.reader.start()

    def read(self):
        for line in self.process.stdout:
            self.wire.write(json.dumps({'direction': 'received', 'line': line}) + '\n'); self.wire.flush()
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                self.messages.put({'invalid_stdout': line})
        self.messages.put({'eof': True})

    def send(self, message):
        self.wire.write(json.dumps({'direction': 'sent', 'message': message}) + '\n'); self.wire.flush()
        self.process.stdin.write(json.dumps(message) + '\n'); self.process.stdin.flush()

    def call(self, method, params):
        self.serial += 1; serial = self.serial
        self.send({'jsonrpc': '2.0', 'id': serial, 'method': method, 'params': params})
        deadline = time.monotonic() + 20
        while True:
            item = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if item.get('eof') or 'invalid_stdout' in item:
                raise RuntimeError(item)
            if item.get('id') == serial:
                return item
            if time.monotonic() > deadline:
                raise TimeoutError(method)

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill(); self.process.wait(timeout=5)
        self.reader.join(timeout=2); self.log.close(); self.wire.close()

def snapshot(db):
    with sqlite3.connect(db) as connection:
        return {key: json.loads(data) for key, data in connection.execute('SELECT id,data FROM records')}

def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', choices=['prefect', 'punkpeye', 'ivo-toby'], required=True)
    parser.add_argument('--converter-python')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); folder = args.output.resolve(); folder.mkdir(parents=True, exist_ok=False)
    db = folder / 'records.sqlite'; eventfile = folder / 'events.jsonl'; ready = folder / 'ready.json'
    outcome = {'subject': args.subject, 'terminal': 'started', 'records': [], 'paid_model_calls': 0}
    started = time.monotonic(); backend = None; client = None
    logfile = (folder / 'backend.log').open('w')
    try:
        backend = subprocess.Popen([sys.executable, str(ROOT / 'scripts/extension/adapter_reference_backend_v1.py'), '--db', str(db), '--events', str(eventfile), '--ready', str(ready)], stdout=logfile, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while not ready.exists():
            if backend.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('backend startup failure')
            time.sleep(0.05)
        environment = ROOT / 'evidence/openapi-adapter-environments-v1' / args.subject
        command = [args.converter_python, str(environment / 'server.py')] if args.subject == 'prefect' else ['node', str(environment / 'server.mjs')]
        client = Client(command, folder)
        outcome['initialize'] = client.call('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'adapter-study', 'version': '1.0.0'}})
        assert 'result' in outcome['initialize'], outcome['initialize']
        client.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        outcome['tools_response'] = client.call('tools/list', {})
        tools = outcome['tools_response']['result']['tools']
        assert not outcome['tools_response']['result'].get('nextCursor'), 'Unexpected pagination in three-operation fixture'
        bindings = {}
        for operation in ['create_record', 'patch_record']:
            candidates = [tool for tool in tools if normalize(tool['name']) == normalize(operation)]
            assert len(candidates) == 1, ('ambiguous/missing operation binding', operation)
            bindings[operation] = candidates[0]
        cases = json.loads((ROOT / 'manifests/openapi-adapter-input-inventory-v1.json').read_text())['cases']
        cases = [case for case in cases if case['id'].endswith(':all-ordinary')] + [case for case in cases if not case['id'].endswith(':all-ordinary')]
        # Two complete predeclared repetitions. Route order reverses in repetition two.
        for repetition in [1, 2]:
            for case in cases:
                row = {'repetition': repetition, 'case_id': case['id'], 'routes': {}}
                tool = bindings[case['operation_id']]
                arguments = deepcopy(case['body'])
                if case['operation_id'] == 'patch_record':
                    arguments['record_id'] = 'seed'
                schema = tool['inputSchema']; validator = validator_for(schema); validator.check_schema(schema)
                row['tool_name'] = tool['name']; row['tool_arguments'] = arguments
                row['tool_schema_errors'] = [error.message for error in validator(schema).iter_errors(arguments)]
                for route in (['rest', 'mcp'] if repetition == 1 else ['mcp', 'rest']):
                    reset_status, _ = request(BASE, 'POST', '/__study/reset', {'records': case['initial_records']})
                    assert reset_status == 200 and typed(snapshot(db)) == typed(case['initial_records'])
                    offset = len(events(eventfile)); route_start = time.monotonic()
                    if route == 'rest':
                        create = case['operation_id'] == 'create_record'
                        status, response = request(BASE, 'POST' if create else 'PATCH', '/records' if create else '/records/seed', case['body'], 'application/json' if create else 'application/merge-patch+json')
                        call = {'status': status, 'response': response}
                    else:
                        call = client.call('tools/call', {'name': tool['name'], 'arguments': arguments})
                    captured = events(eventfile)[offset:]
                    read_status, readback = request(BASE, 'GET', '/records/' + case['target_id'])
                    state = snapshot(db)
                    observation = {'call': call, 'captured_requests': captured, 'read_status': read_status, 'readback': readback, 'database_records': state, 'expected_state_match': typed(state) == typed(case['expected_records']), 'elapsed_seconds': time.monotonic() - route_start}
                    row['routes'][route] = observation
                    if route == 'rest':
                        assert call['status'] == (201 if case['operation_id'] == 'create_record' else 200) and observation['expected_state_match'], 'Direct REST qualification failed'
                outcome['records'].append(row)
                (folder / 'observations.json').write_text(json.dumps(outcome, indent=2) + '\n')
                if case['id'].endswith(':all-ordinary'):
                    assert not row['tool_schema_errors'] and row['routes']['mcp']['expected_state_match'], 'Ordinary-value qualification failed'
        outcome['terminal'] = 'completed'
    except Exception as error:
        outcome['terminal'] = 'failed'; outcome['error'] = repr(error)
        raise
    finally:
        if client:
            client.close()
        if backend:
            backend.terminate()
            try:
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill(); backend.wait(timeout=5)
        logfile.close(); outcome['elapsed_seconds'] = time.monotonic() - started
        outcome['backend_reaped'] = backend is None or backend.poll() is not None
        outcome['converter_reaped'] = client is None or client.process.poll() is not None
        (folder / 'observations.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps({'subject': args.subject, 'terminal': outcome['terminal'], 'paired_observations': len(outcome['records'])}))

if __name__ == '__main__':
    main()
