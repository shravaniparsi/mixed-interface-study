#!/usr/bin/env python3
"""Exposed secondary analysis: isolate information from oracle implementation."""
import argparse
import hashlib
import json
from pathlib import Path
from verify_netbox_config_defaults_v1 import build as verify_calibration

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/netbox-config-defaults-v2-ci-43157153410'
MODES = ['status_only', 'requested_values_only', 'recorded_runtime_configuration', 'parameterized_configuration_reference', 'stale_initial_configuration']


def mismatches(observed, expected):
    output = {}
    for name, value in expected.items():
        if name not in observed:
            output[name] = {'reason': 'absent', 'expected': value}
        elif type(observed[name]) is not type(value) or observed[name] != value:
            output[name] = {'reason': 'different', 'observed': observed[name], 'expected': value}
    return output


def expected_fields(defaults, supplied):
    expected = dict(defaults)
    for name, value in supplied.items():
        expected[name] = value
    return expected


def build():
    validated = verify_calibration(ARCHIVE, corrected=True)
    assert validated == json.loads((ROOT / 'manifests/netbox-config-defaults-results-v2.json').read_text())
    versions = {}
    for version in ['buggy', 'fixed']:
        data = json.loads((ARCHIVE / version / 'observations.json').read_text())
        initial = {}; ids = {}
        for event in data['events'][:4]:
            payload = event['payload']; ids[event['body']['id']] = payload['name']
            if 'default' in payload:
                initial[payload['name']] = payload['default']
        updated = initial.copy()
        for event in data['events']:
            if event['method'] == 'patch' and event['path'].startswith('/api/extras/custom-fields/'):
                name = ids[int(event['path'].rstrip('/').split('/')[-1])]
                updated[name] = event['payload']['default']
        cases = []
        for row in data['cases']:
            assert row['qualified']
            supplied = row['payload'].get('custom_fields', {})
            config = updated if row['phase'] else initial
            observed = {'response': row['create_body']['custom_fields'], 'readback': row['read_body']['custom_fields'], 'database': row['database_custom_fields']}
            expectations = {'requested_values_only': supplied,
                            'parameterized_configuration_reference': expected_fields(config, supplied),
                            'stale_initial_configuration': expected_fields(initial, supplied)}
            detail = {mode: {stage: mismatches(value, expected) for stage, value in observed.items()} for mode, expected in expectations.items()}
            alerts = {mode: any(stages.values()) for mode, stages in detail.items()}
            alerts['status_only'] = row['create_status'] != 201 or row['read_status'] != 200
            alerts['recorded_runtime_configuration'] = any(row['differences'].values())
            cases.append({'phase': row['phase'], 'case': row['case'], 'alerts': alerts, 'reference_expected': expectations['parameterized_configuration_reference'], 'stage_differences': detail})
        versions[version] = {'cases': cases, 'alert_counts': {mode: sum(r['alerts'][mode] for r in cases) for mode in MODES},
                             'runtime_reference_disagreements': sum(r['alerts']['recorded_runtime_configuration'] != r['alerts']['parameterized_configuration_reference'] for r in cases)}
    paths = ['protocol/netbox-information-reference-replay-v1.md', 'manifests/netbox-config-defaults-results-v2.json',
             'scripts/extension/replay_netbox_information_reference_v1.py', 'scripts/extension/verify_netbox_config_defaults_v1.py']
    return {'kind': 'netbox_information_reference_replay_v1', 'outcome_exposed_secondary_analysis': True,
            'new_application_executions': 0, 'paid_model_calls': 0, 'historical_faults_represented': 1,
            'independent_ground_truth': False, 'automatic_inference_evaluated': False, 'versions': versions,
            'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); path = ROOT / 'manifests/netbox-information-reference-replay-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        assert not path.exists(); path.write_text(json.dumps(value, indent=2) + '\n')
    for version, result in value['versions'].items():
        print(version, json.dumps({k: v for k, v in result.items() if k != 'cases'}))


if __name__ == '__main__':
    main()
