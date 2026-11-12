#!/usr/bin/env python3
"""Exercise actual HTTP persistence and negative request-transformation controls."""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MODES = ['identity', 'drop_null', 'drop_falsy', 'reverse_arrays']


def typed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def transform(value, mode):
    if isinstance(value, dict):
        return {k: transform(v, mode) for k, v in value.items() if not ((mode == 'drop_null' and v is None) or (mode == 'drop_falsy' and not v))}
    if isinstance(value, list):
        transformed = [transform(v, mode) for v in value]
        return list(reversed(transformed)) if mode == 'reverse_arrays' else transformed
    return value


def request(base, method, path, body=None, media='application/json'):
    encoded = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=encoded, method=method, headers={'Content-Type': media})
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    folder = args.output; folder.mkdir(parents=True, exist_ok=False)
    db = folder / 'records.sqlite'; ready = folder / 'ready.json'
    inputs = json.loads((ROOT / 'manifests/openapi-adapter-input-inventory-v1.json').read_text())
    result = {'kind': 'adapter_reference_calibration_v1', 'converter_executions': 0, 'paid_model_calls': 0, 'records': [], 'terminal': 'started'}
    log = (folder / 'service.log').open('w')
    process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/extension/adapter_reference_backend_v1.py'), '--db', str(db), '--events', str(folder / 'events.jsonl'), '--ready', str(ready), '--port', '0'], stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 15
        while not ready.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('reference server did not start')
            time.sleep(0.05)
        base = 'http://127.0.0.1:' + str(json.loads(ready.read_text())['port'])
        for mode in MODES:
            for case in inputs['cases']:
                reset_status, reset = request(base, 'POST', '/__study/reset', {'records': case['initial_records']})
                assert reset_status == 200 and reset['records'] == 2
                with sqlite3.connect(db) as conn:
                    before = {k: json.loads(v) for k, v in conn.execute('SELECT id,data FROM records')}
                assert typed(before) == typed(case['initial_records'])
                payload = transform(deepcopy(case['body']), mode)
                create = case['operation_id'] == 'create_record'
                status, response = request(base, 'POST' if create else 'PATCH', '/records' if create else '/records/seed', payload,
                                           'application/json' if create else 'application/merge-patch+json')
                assert status == (201 if create else 200), (mode, case['id'], status, response)
                read_status, readback = request(base, 'GET', '/records/' + case['target_id'])
                assert read_status == 200
                with sqlite3.connect(db) as conn:
                    after = {k: json.loads(v) for k, v in conn.execute('SELECT id,data FROM records')}
                assert typed(response) == typed(readback) == typed({'id': case['target_id'], 'data': after[case['target_id']]})
                result['records'].append({'mode': mode, 'case_id': case['id'], 'sent_body': payload, 'status': status, 'response': response, 'readback': readback, 'database_records': after,
                                          'expected_state_match': typed(after) == typed(case['expected_records'])})
        result['summary'] = {mode: {'cases': sum(r['mode'] == mode for r in result['records']), 'state_mismatches': sum(r['mode'] == mode and not r['expected_state_match'] for r in result['records'])} for mode in MODES}
        assert result['summary']['identity']['state_mismatches'] == 0
        assert all(result['summary'][mode]['state_mismatches'] > 0 for mode in MODES if mode != 'identity')
        result['terminal'] = 'completed'
    except Exception as error:
        result['terminal'] = 'failed'; result['error'] = repr(error)
        raise
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
        log.close()
        result['server_reaped'] = process.poll() is not None
        files = ['scripts/extension/adapter_reference_backend_v1.py', 'scripts/extension/calibrate_adapter_reference_v1.py', 'manifests/openapi-adapter-input-inventory-v1.json', 'evidence/openapi-adapter-inputs-v1/openapi.json']
        result['source_sha256'] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
        result['validator_version'] = importlib.metadata.version('openapi-schema-validator')
        (folder / 'observations.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
