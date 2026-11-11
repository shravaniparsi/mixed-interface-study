#!/usr/bin/env python3
"""Verify archived harness qualification evidence, without running a REST service."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    path = ROOT / 'results/restestbench-scoring-probe-v1/observations.json'
    probe = json.loads(path.read_text())
    pins_path = ROOT / 'manifests/restestbench-source-pins-v1.json'
    pins = json.loads(pins_path.read_text())
    assert probe['upstream_commit'] == pins['commit'] == '4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae'
    for name, expected in probe['source_sha256'].items(): assert sha(ROOT / name) == expected
    for row in pins['files']:
        data = (ROOT / 'evidence/restestbench-source-v1' / row['path']).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob']
    instrument = ROOT / 'scripts/extension/probe_restestbench_scoring_v1.py'
    assert sha(instrument) == probe['instrument_sha256']
    cases = {r['case']: r for r in probe['observations']}
    assert len(cases) == len(probe['observations']) == 4
    expected = {'changed_value': ([True], 2, 1), 'unapplied_mutation': ([False], 1, 1),
                'equivalent_comment': ([True], 2, 0), 'invalid_test_control': ([], 1, 0)}
    for name, (applied, executions, score) in expected.items():
        case = cases[name]
        assert case['application_results'] == applied
        assert case['actual_test_process_executions'] == executions
        assert case['score']['score'] == score
        assert case['score']['passes_on_valid'] == (name != 'invalid_test_control')
    failed = cases['unapplied_mutation']
    assert failed['results'][0]['passed'] and failed['results'][0]['return_code'] == 0
    phantom = failed['results'][1]
    assert phantom['execution_context'] == 'mutated_0' and not phantom['passed']
    assert phantom['output'] == 'Mutation could not be applied' and phantom['return_code'] == -1
    assert phantom['duration_ms'] == 0 and failed['score']['mutants_killed'] == [0]
    inventory_path = ROOT / 'manifests/restestbench-source-inventory-v1.json'
    inventory = json.loads(inventory_path.read_text())
    counts = {service: len(rows) for service, rows in inventory['services'].items()}
    assert counts == {'fastapi': 63, 'nestjs-realworld': 29, 'todoapp': 14}
    return {'kind': 'restestbench_scoring_qualification_v1', 'upstream_commit': pins['commit'],
            'qualification_probe_cases': 4, 'real_application_executions': 0,
            'unapplied_mutation_receives_kill_credit': True,
            'mutant_test_process_executions_in_failure_case': 0,
            'published_result_impact_established': False, 'novel_defect_claimed': False,
            'requirement_file_inventory_counts': counts,
            'valid_parsed_requirement_counts_established': False,
            'benchmark_admitted_for_scientific_evaluation': False,
            'paid_model_calls': 0,
            'evidence_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [path, pins_path, inventory_path, instrument]},
            'limits': ['Synthetic lifecycle fixture; upstream mutation/execution/scoring code runs unchanged.',
                       'The failure was source-exposed before probing; no independent defect-discovery estimate.',
                       'No claim about frequency or effect on the published benchmark rankings.',
                       'Inventory counts files, not parsed, validated, executed or paper-selected requirements.']}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(); output = ROOT / 'manifests/restestbench-scoring-qualification-v1.json'
    if args.verify: assert json.loads(output.read_text()) == value
    else:
        assert not output.exists()
        output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('limits', 'evidence_sha256')}))


if __name__ == '__main__': main()
