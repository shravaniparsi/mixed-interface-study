#!/usr/bin/env python3
"""Reconstruct configuration calibration without treating failed setup as detection."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEAD = '6479519e474e39b51aba9ae01d0c306590467dae'
RUN = 43156734009


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_fields(actual, expected):
    return {key: {'missing': key not in actual, 'actual': actual.get(key), 'expected': value}
            for key, value in expected.items()
            if key not in actual or type(actual[key]) is not type(value) or actual[key] != value}


def reconstruct(data):
    supplied_cases = [
        ('omitted_map', None), ('empty_map', {}), ('sibling_only', {'study_sibling': 'preserve-me'}),
        ('explicit_overrides', {'study_text': 'override', 'study_bool': False, 'study_int': 9}),
        ('explicit_null_false_zero', {'study_text': None, 'study_bool': False, 'study_int': 0}),
        ('partial_override', {'study_text': 'override'}),
    ]
    schedule = [(phase, name, supplied) for phase in range(2) for name, supplied in supplied_cases]
    rows = data['cases']; assert len(rows) <= len(schedule)
    outcomes = []
    for i, row in enumerate(rows):
        phase, name, supplied = schedule[i]
        assert (row['phase'], row['case']) == (phase, name)
        defaults = {'study_text': 'beta' if phase else 'alpha', 'study_bool': not bool(phase), 'study_int': 0 if phase else 7}
        # Compare types too: Python's equality treats False==0.
        assert not compare_fields(row['metadata_defaults'], defaults)
        expected = defaults.copy()
        if supplied is not None:
            expected.update(supplied)
        assert not compare_fields(row['expected'], expected) and set(row['expected']) == set(expected)
        payload = {'prefix': f'10.{phase}.{i % 6}.0/24', 'status': 'active', 'description': name}
        if supplied is not None:
            payload['custom_fields'] = supplied
        assert row['payload'] == payload
        result = {'phase': phase, 'case': name, 'qualified': row['qualified']}
        if not row['qualified']:
            result['reason'] = row.get('reason', 'incomplete_execution')
        else:
            assert row['create_status'] == 201 and row['read_status'] == 200
            assert row['create_body']['id'] == row['read_body']['id']
            assert row['create_body']['prefix'] == row['read_body']['prefix'] == payload['prefix']
            computed = {stage: compare_fields(value, expected) for stage, value in [
                ('response', row['create_body'].get('custom_fields', {})),
                ('readback', row['read_body'].get('custom_fields', {})),
                ('database', row['database_custom_fields'])]}
            assert computed == row['differences']
            result.update(status_baseline_pass=True, configuration_violation=any(computed.values()), differences=computed)
            # Tie observations to the raw ordered API events.
            start = 7 + (i % 6) * 2 if phase == 0 else 25 + (i % 6) * 2
            create, read = data['events'][start:start + 2]
            assert create == {'method': 'post', 'path': '/api/ipam/prefixes/', 'payload': payload, 'status': 201, 'body': row['create_body']}
            assert read == {'method': 'get', 'path': f"/api/ipam/prefixes/{row['create_body']['id']}/", 'payload': None, 'status': 200, 'body': row['read_body']}
        outcomes.append(result)
    if data['terminal'] == 'completed':
        assert len(rows) == 12 and len(data['events']) == 37
        ids = {}
        for event in data['events'][:4]:
            assert event['method'] == 'post' and event['path'] == '/api/extras/custom-fields/' and event['status'] == 201
            assert event['payload']['object_types'] == ['ipam.prefix'] and event['payload']['required'] is False
            ids[event['payload']['name']] = event['body']['id']
        for phase, start in [(0, 4), (1, 22)]:
            for j, name in enumerate(['study_text', 'study_bool', 'study_int']):
                event = data['events'][start + j]
                assert event['method'] == 'get' and event['status'] == 200 and event['path'] == f'/api/extras/custom-fields/{ids[name]}/'
                assert not compare_fields({name: event['body']['default']}, {name: rows[phase * 6]['metadata_defaults'][name]})
        for i, (name, value) in enumerate([('study_text', 'beta'), ('study_bool', False), ('study_int', 0)]):
            event = data['events'][19 + i]
            assert event['method'] == 'patch' and event['status'] == 200 and event['path'] == f'/api/extras/custom-fields/{ids[name]}/'
            assert not compare_fields(event['payload'], {'default': value})
    qualified = [r for r in outcomes if r['qualified']]
    return {'terminal': data['terminal'], 'recorded_cases': len(rows), 'qualified_cases': len(qualified), 'unattempted_cases': len(schedule) - len(rows),
            'status_baseline_passes': len(qualified), 'configuration_violations': sum(r['configuration_violation'] for r in qualified), 'outcomes': outcomes}


def build(archive):
    registration = json.loads((ROOT / 'manifests/netbox-config-defaults-registration-v1.json').read_text())
    for key in ['instrument_sha256', 'source_evidence_sha256']:
        for path, expected in registration[key].items():
            assert sha(ROOT / path) == expected, path
    run = json.loads((archive / 'run.json').read_text())
    assert run['id'] == RUN and run['head_sha'] == HEAD and run['status'] == 'completed' and run['run_attempt'] == 1
    jobs = json.loads((archive / 'jobs.json').read_text())['jobs']
    assert len(jobs) == 2 and all(j['status'] == 'completed' for j in jobs)
    variants = {}
    for version, commit in registration['upstream_commits'].items():
        folder = archive / version
        if (folder / 'study-head.txt').exists():
            assert (folder / 'study-head.txt').read_text().strip() == HEAD
            assert (folder / 'upstream-head.txt').read_text().strip() == commit
        path = folder / 'observations.json'
        if not path.exists():
            variants[version] = {'terminal': 'no_observations', 'qualified_cases': 0}
            continue
        instrument = (folder / 'instrument-sha256.txt').read_text().split()[0]
        assert instrument == registration['instrument_sha256']['scripts/extension/netbox_config_defaults_probe_v1.py']
        data = json.loads(path.read_text()); assert data['upstream_commit'] == commit
        variants[version] = reconstruct(data)
    minutes = sum((datetime.fromisoformat(j['completed_at'].replace('Z', '+00:00')) - datetime.fromisoformat(j['started_at'].replace('Z', '+00:00'))).total_seconds() / 60 for j in jobs)
    return {'kind': 'netbox_config_defaults_results_v1', 'run_id': RUN, 'study_head': HEAD, 'versions': variants,
            'application_job_minutes': minutes, 'job_minutes_ceiling': 30, 'paid_model_calls': 0,
            'historical_faults': 1, 'independent_discoveries': 0, 'automatic_oracle_inference_evaluated': False,
            'evidence_sha256': {str(p.relative_to(archive)): sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--archive', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(args.archive)
    if args.verify:
        assert json.loads(args.output.read_text()) == value
    else:
        assert not args.output.exists(); args.output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ['evidence_sha256', 'versions']}, indent=2))
    for name, result in value['versions'].items():
        print(name, json.dumps({k: v for k, v in result.items() if k != 'outcomes'}))


if __name__ == '__main__':
    main()
