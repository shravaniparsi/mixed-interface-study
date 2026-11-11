#!/usr/bin/env python3
"""Export existing historical traces and score one shared frame baseline.

Post-hoc development analysis. No new application executions or unseen efficacy.
Run the original independent reconstruction commands before using this export.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_frame import evaluate

OUTPUT = ROOT / 'manifests/write-frame-development-v1.json'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    records = []
    proofs = {
        'tiller': ROOT / 'manifests/write-preservation-calibration-results-v2.json',
        'iris': ROOT / 'manifests/iris-write-preservation-results-v1.json',
    }
    for app, proof_path in proofs.items():
        proof = read(proof_path)
        assert proof['calibration_gate_passed']
        for name, expected in proof['raw_sha256'].items():
            assert digest(ROOT / name) == expected, name
        scores = proof['scores']
        if app == 'tiller':
            paths = sorted((ROOT / 'results/write-preservation-calibration-v2-ci-43079843246').glob('*/observations.json'))
            assert len(paths) == 2
            groups = [(('historical' if '-historical-' in str(p) else 'fixed'), p, read(p)) for p in paths]
        else:
            paths = sorted((ROOT / 'results/iris-write-calibration-v1-ci-43082290147').glob('*/iris-calibration/observations/*.json'))
            assert len(paths) == 24
            groups = [(p.parents[2].name.split('iris-write-calibration-v1-')[1].split('-430')[0], p, [read(p)]) for p in paths]
        for cell, path, observations in groups:
            for index, observation in enumerate(observations):
                case, channel = observation['case'], observation['channel']
                matches = [s for s in scores if s.get('version', s.get('cell')) == cell and s['case'] == case and s['channel'] == channel]
                assert len(matches) == 1
                score = matches[0]
                # Contract mappings come from the registered experiments, not changed fields.
                if app == 'tiller':
                    assignments = observation['input']['updates']
                    derived = []
                else:
                    assignments = {k: v for k, v in observation['intent'].items() if k != 'set_id'}
                    derived = ['updated_at']
                computed = evaluate(observation['before'], observation['after'], assignments, derived)
                assert computed['frame_violations'] == score['frame_violations']
                assert not computed['failed_assignments']
                records.append({
                    'id': '/'.join([app, cell, case, channel]),
                    'project': app, 'mechanism_id': app + '-known-write-loss',
                    'split': 'development_outcome_exposed', 'cell': cell,
                    'case': case, 'channel': channel,
                    'source': str(path.relative_to(ROOT)), 'source_index': index if app == 'tiller' else None,
                    'source_sha256': digest(path),
                    'before': observation['before'], 'after': observation['after'],
                    'contract': {'assignments': assignments, 'derived_fields': derived, 'origin': 'manually specified registered experiment'},
                    'schema_valid': score['schema_valid'], 'operation_success': score['operation_success'],
                    'baseline': computed,
                })
    records.sort(key=lambda r: r['id'])
    assert len(records) == len({r['id'] for r in records}) == 36
    return {
        'kind': 'shared_write_frame_development_v1',
        'analysis_timing': 'post_hoc_on_completed_calibrations',
        'executions': len(records), 'independent_known_mechanisms': 2,
        'new_application_executions': 0, 'new_defects': 0,
        'schema_alerts': sum(not r['schema_valid'] for r in records),
        'success_alerts': sum(not r['operation_success'] for r in records),
        'requested_assignment_alerts': sum(bool(r['baseline']['failed_assignments']) for r in records),
        'frame_alerts': sum(bool(r['baseline']['frame_violations']) for r in records),
        'proof_sha256': {str(p.relative_to(ROOT)): digest(p) for p in proofs.values()},
        'implementation_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__).resolve(), ROOT / 'src/mixed_interface/write_frame.py']},
        'limits': ['Contracts are manual; no automatic inference advantage is established.',
                   'Labels and frame baseline share the preservation contract; this is reconstruction, not independent diagnostic accuracy.',
                   'Only target rows are observed; effects on other tables or external services are outside this export.',
                   'Derived exceptions are field-level; correctness of the new timestamp itself is not checked.',
                   'Historical cases and variants cannot estimate ecosystem prevalence or population false-positive rates.'],
        'records': records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.verify:
        assert read(OUTPUT) == result, 'export differs from archived sources or implementation'
    else:
        OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['records', 'proof_sha256', 'implementation_sha256', 'limits']}))


if __name__ == '__main__':
    main()
