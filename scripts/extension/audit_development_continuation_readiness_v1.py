#!/usr/bin/env python3
"""Offline reuse assessment; does not execute or qualify an API continuation."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'manifests/development-continuation-readiness-v1.json'


def build():
    manifest_path = ROOT / 'manifests/development-admin-control-v2.json'
    manifest = json.loads(manifest_path.read_text())
    records = {}
    hashes = {}
    for arm in manifest['arms']:
        name = arm['arm']
        path = 'results/development-admin-control-v2-' + name + '-ci-44105779135/admin-workflow.json'
        raw = (ROOT / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != arm['hashes'][path]:
            raise ValueError('Retained evidence hash mismatch: ' + path)
        hashes[path] = digest
        records[name] = json.loads(raw)
    checks = {}
    for name, record in records.items():
        checks[name] = {
            'qualified_native_continuation': record['status'] == 'qualified',
            'producer_201': record['producer']['status'] == 201,
            'native_update_200': record['consumer']['status'] == 200,
            'captured_native_body_equals_projected_start_with_single_edit':
                record['consumer']['body'] == dict(record['after_create'], firstName='Edited'),
            'projected_final_equals_captured_native_body':
                record['after_edit'] == record['consumer']['body'],
        }
    return {
        'kind': 'retrospective_development_continuation_reuse_assessment',
        'source_run_id': 44105779135,
        'source_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'evidence_sha256': hashes,
        'checks': checks,
        'between_arm_actor_projection_equal': records['ui']['actor'] == records['api']['actor'],
        'between_arm_start_projection_equal': records['ui']['after_create'] == records['api']['after_create'],
        'between_arm_native_update_json_equal': records['ui']['consumer']['body'] == records['api']['consumer']['body'],
        'readback_projection_keys': sorted(records['api']['after_create']),
        'captured_native_update_body': records['api']['consumer']['body'],
        'api_continuation_observed_in_these_controls': False,
        'complete_state_checkpoint_qualified_by_these_controls': False,
        'new_application_runs': 0,
        'new_independent_evaluation_cases': 0,
        'decision': 'reuse_native_serialization_as_development_reference_only',
        'remaining_gates': [
            'Define and qualify relevant persisted, browser, cache and background state equivalence.',
            'Freeze a separate ordinary API continuation control before execution.',
            'Qualify API continuation using the complete native JSON payload and same actor.',
            'Register an independent evaluation frame separately; this exposed workflow is development only.',
        ],
        'deployment_constraint': 'Public open-source systems and synthetic isolated data only; no organizational sandbox is available.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.verify:
        if json.loads(OUTPUT.read_text()) != result:
            raise ValueError('Saved assessment differs from retained evidence')
        print('Retained-control assessment reproduced; no runtime or checkpoint qualification added.')
    else:
        OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
        print(result['decision'])


if __name__ == '__main__':
    main()
