#!/usr/bin/env python3
"""Reconstruct reference calibration from captured HTTP and persisted snapshots."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def altered(value, mode):
    if isinstance(value, list):
        items = [altered(item, mode) for item in value]
        return items[::-1] if mode == 'reverse_arrays' else items
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if mode == 'drop_null' and item is None:
            continue
        if mode == 'drop_falsy' and not item:
            continue
        result[key] = altered(item, mode)
    return result

def reconstruct(archive):
    observations = json.loads((archive / 'observations.json').read_text())
    assert observations['terminal'] == 'completed' and observations['server_reaped']
    assert observations['converter_executions'] == observations['paid_model_calls'] == 0
    for name, digest in observations['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    cases = json.loads((ROOT / 'manifests/openapi-adapter-input-inventory-v1.json').read_text())['cases']
    events = [json.loads(line) for line in (archive / 'events.jsonl').read_text().splitlines()]
    modes = ['identity', 'drop_null', 'drop_falsy', 'reverse_arrays']
    assert len(observations['records']) == 192 and len(events) == 576 and len(cases) == 48
    summary = {}
    index = 0
    for mode in modes:
        mismatches = 0
        for case in cases:
            row = observations['records'][index]
            reset, write, read = events[index * 3:index * 3 + 3]
            assert row['mode'] == mode and row['case_id'] == case['id']
            assert (reset['method'], reset['path'], reset['status']) == ('POST', '/__study/reset', 200)
            assert canonical(json.loads(reset['raw_body'])) == canonical({'records': case['initial_records']})
            payload = altered(case['body'], mode)
            assert canonical(row['sent_body']) == canonical(payload) == canonical(json.loads(write['raw_body']))
            create = case['operation_id'] == 'create_record'
            assert (write['method'], write['path'], write['status']) == ('POST' if create else 'PATCH', '/records' if create else '/records/seed', 201 if create else 200)
            assert write['content_type'] == ('application/json' if create else 'application/merge-patch+json')
            assert row['status'] == write['status']
            assert (read['method'], read['path'], read['status']) == ('GET', '/records/' + case['target_id'], 200)
            expected_response = {'id': case['target_id'], 'data': row['database_records'][case['target_id']]}
            assert all(canonical(item) == canonical(expected_response) for item in [write['response'], read['response'], row['response'], row['readback']])
            matched = canonical(row['database_records']) == canonical(case['expected_records'])
            assert row['expected_state_match'] is matched
            mismatches += not matched
            index += 1
        summary[mode] = {'cases': 48, 'state_mismatches': mismatches}
    assert summary == observations['summary']
    assert [summary[m]['state_mismatches'] for m in modes] == [0, 14, 30, 4]
    with sqlite3.connect('file:' + str(archive / 'records.sqlite') + '?mode=ro', uri=True) as connection:
        final = {k: json.loads(v) for k, v in connection.execute('SELECT id,data FROM records')}
    assert canonical(final) == canonical(observations['records'][-1]['database_records'])
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=ROOT / 'results/adapter-reference-calibration-v1-local-allowed')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    summary = reconstruct(args.archive.resolve())
    if args.runtime:
        print(json.dumps(summary)); return
    failed = ROOT / 'results/adapter-reference-calibration-v1'
    failure = json.loads((failed / 'observations.json').read_text())
    assert failure['terminal'] == 'failed' and failure['records'] == [] and failure['server_reaped']
    assert 'Operation not permitted' in (failed / 'service.log').read_text()
    files = sorted(p for folder in [failed, args.archive] for p in folder.iterdir() if p.is_file())
    result = {'kind': 'adapter_reference_calibration_verification_v1', 'summary': summary,
              'http_events': 576, 'converter_executions': 0, 'paid_model_calls': 0,
              'startup_failures_before_requests': 1,
              'scope': 'Synthetic reference harness and deliberately altered requests; not natural defects or converter findings.',
              'archive_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    output = ROOT / 'manifests/adapter-reference-calibration-v1.json'
    if args.verify:
        assert json.loads(output.read_text()) == result
    else:
        output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(summary))

if __name__ == '__main__':
    main()
