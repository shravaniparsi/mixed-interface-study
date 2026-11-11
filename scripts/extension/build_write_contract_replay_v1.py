#!/usr/bin/env python3
"""Post-hoc portable replay of existing traces; no new runtime experiments."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_contract import check
from build_write_frame_development_v1 import build as original_export


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    original = original_export()
    assert original == read(ROOT / 'manifests/write-frame-development-v1.json')
    records = copy.deepcopy(original['records'])
    for record in records:
        record.pop('baseline')
        record['views'] = {}
        record['observation_scope'] = 'target_row_only_in_this_export'
    proof_path = ROOT / 'manifests/fastdash-cascade-results-v2.json'
    proof = read(proof_path)
    for name, expected in proof['raw_sha256'].items(): assert sha(ROOT / name) == expected
    paths = sorted((ROOT / 'results/fastdash-cascade-v1-ci-43088065630').glob('*/fastdash-calibration/observations/*.json'))
    assert len(paths) == 8
    for path in paths:
        o = read(path)
        version = 'historical' if '-historical-' in str(path) else 'fixed'
        case = o['case']
        score = next(s for s in proof['scores'] if s['version'] == version and s['case'] == case)
        field, value = o['input']['component_id'], o['input']['value']
        # Mappings are the registered manual contract, never inferred from outcomes.
        derived = {'state': None} if case in ('parent_change', 'already_clear') else {}
        views = {'state': o['after'],
                 'readback': {r['id']: r['current_value'] for r in o['fresh_client_readback']['inputs']},
                 'invocation_arguments': o['history_response'].get('kwargs_summary')}
        records.append({'id': '/'.join(['fastdash', version, case, 'mcp']),
                        'project': 'fastdash', 'mechanism_id': 'fastdash-known-cascade',
                        'split': 'development_outcome_exposed', 'cell': version, 'case': case, 'channel': 'mcp',
                        'source': str(path.relative_to(ROOT)), 'source_index': None, 'source_sha256': sha(path),
                        'before': o['before'], 'after': o['after'], 'views': views,
                        'observation_scope': 'process_state_readback_invocation_arguments_no_database_or_browser',
                        'contract': {'assignments': {field: value}, 'derived_assignments': derived,
                                     'origin': 'manually specified registered experiment',
                                     'agreements': [{'left': left, 'right': right, 'fields': ['country', 'state', 'label']}
                                                    for left, right in [('state', 'readback'), ('readback', 'invocation_arguments')]]},
                        'schema_valid': score['schema_valid'], 'operation_success': score['operation_success']})
    records.sort(key=lambda r: r['id'])
    assert len(records) == len({r['id'] for r in records}) == 44
    scores = [check(r) for r in records]
    # Parity against archived reconstructions, not independent accuracy labels.
    for r, s in zip(records, scores):
        if r['project'] == 'fastdash':
            old = next(v for v in proof['scores'] if v['version'] == r['cell'] and v['case'] == r['case'])
            assert s['contract_violation'] == bool(old['documented_contract_mismatches'])
        else:
            old = next(v for v in original['records'] if v['id'] == r['id'])
            assert s['frame'] == old['baseline']
    sources = [ROOT / 'manifests/write-frame-development-v1.json', proof_path,
               ROOT / 'src/mixed_interface/write_contract.py', ROOT / 'src/mixed_interface/write_frame.py', Path(__file__).resolve()]
    return {'kind': 'portable_manual_write_contract_replay_v1', 'timing': 'post_hoc_development_reconstruction',
            'records': records, 'scores': scores,
            'summary': {'records': len(records), 'projects': 3, 'new_application_executions': 0,
                        'schema_alerts': sum(not r['schema_valid'] for r in records),
                        'operation_success_alerts': sum(not r['operation_success'] for r in records),
                        'requested_assignment_alerts': sum(bool(s['frame']['failed_assignments']) for s in scores),
                        'preservation_frame_alerts': sum(bool(s['frame']['frame_violations']) for s in scores),
                        'derived_assignment_alerts': sum(bool(s['derived_assignment_failures']) for s in scores),
                        'agreement_alert_records': sum(any(a['status'] == 'fail' for a in s['agreements']) for s in scores),
                        'records_with_agreement_measurements': sum(bool(s['agreements']) for s in scores),
                        'union_contract_alert_records': sum(s['contract_violation'] for s in scores),
                        'new_defects_claimed': 0},
            'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources},
            'limits': ['Manual mappings and expected derived changes remain necessary.',
                       'Agreement is measured only for eight Fast Dash records; absence elsewhere is not a passing result.',
                       'Stored state and invocation arguments do not establish browser parity or restart durability.',
                       'Parity with existing reconstruction is not independent accuracy or unseen transfer.',
                       'No novel algorithm, reduced specification effort, or Q1 readiness is established.']}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); output = ROOT / 'manifests/write-contract-replay-v1.json'
    if args.verify: assert read(output) == value
    else:
        assert not output.exists()
        output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value['summary']))


if __name__ == '__main__': main()
