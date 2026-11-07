#!/usr/bin/env python3
"""Recompute integration accounting from preserved executions, not prose totals."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    root = args.run.resolve()
    summary = load(root / 'summary.json')
    assert summary['status'] == 'completed'
    assert len(summary['validation']) == 18 and len(summary['calibration']) == 8
    assert len(summary['sessions']) == 9
    for name, digest in summary['source_sha256'].items():
        assert hashlib.sha256((root / 'sources' / name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((root / 'original-pool.json').read_bytes()).hexdigest() == summary['original_pool_sha256']
    original = load(root / 'original-pool.json')
    effective = load(root / 'effective-pool.json')
    assert len(original['cases']) == len(effective['cases']) == 18
    for before, after in zip(original['cases'], effective['cases']):
        assert {k:v for k,v in before.items() if k != 'estimated_cost_s'} == {
            k:v for k,v in after.items() if k != 'estimated_cost_s'}
    contexts = set()
    rows = []
    timed_records = []
    for entry in summary['sessions']:
        run = load(root / entry['record'])
        contexts.add(run['hashes']['comparison_context_sha256'])
        assert run['budget_s'] == summary['budget_seconds']
        assert run['stop_reason'] != 'execution_error'
        dependencies, obligations = set(), set()
        for case in run['cases']:
            timed_records.append(case)
            if case['feedback_credited']:
                assert case['status'] == case['callback_status'] == 'completed'
                assert case['ended_elapsed_s'] <= run['budget_s']
                assert case['feedback']['case_id'] == case['case_id']
                dependencies.update(json.dumps(v, sort_keys=True) for v in case['feedback']['exercised_dependencies'])
                obligations.update(json.dumps(v, sort_keys=True) for v in case['feedback']['exercised_obligations'])
        assert dependencies == {json.dumps(v, sort_keys=True) for v in run['observed_coverage']['dependencies']}
        assert obligations == {json.dumps(v, sort_keys=True) for v in run['observed_coverage']['obligations']}
        rows.append({'seed':run['seed'], 'strategy':run['strategy'],
                     'callback_invocations':len(run['execution_order']),
                     'workers_started':sum((root / c['details']['evidence'] / 'worker.log').exists()
                                           for c in run['cases'] if c['details'] and 'evidence' in c['details']),
                     'credited_completed':sum(c['feedback_credited'] for c in run['cases']),
                     'outcomes':dict(Counter(c['outcome'] for c in run['cases'] if c['status'] == 'completed')),
                     'dependencies':len(dependencies), 'route_obligations':len(obligations),
                     'elapsed_s':run['elapsed_s'], 'overrun_s':run['deadline_overrun_s'],
                     'stop_reason':run['stop_reason']})
    assert len(contexts) == 1
    resets = list(root.rglob('reset.json'))
    assert resets and {load(p)['sha256'] for p in resets} == {summary['resources']['fixture_sha256']}
    cleanup = list(root.rglob('parent-browser-cleanup.json'))
    assert cleanup and all(load(p)['ok'] for p in cleanup)
    observations = list(root.rglob('observation.json'))
    for path in observations:
        obs = load(path)
        assert all(c['passed'] for c in obs['checks'] if c['name'].endswith('_actual_payload'))
    for stage in ['validation', 'calibration']:
        for entry in summary[stage]:
            obs = root / entry['details']['evidence'] / 'observation.json'
            assert hashlib.sha256(obs.read_bytes()).hexdigest() == entry['details']['observation_sha256']
    for case in timed_records:
        if case['details'] and 'observation_sha256' in case['details']:
            obs = root / case['details']['evidence'] / 'observation.json'
            assert hashlib.sha256(obs.read_bytes()).hexdigest() == case['details']['observation_sha256']
    result = {'kind':'runtime_integration_accounting', 'run_id':summary['run_id'],
              'validation':dict(Counter(v['outcome'] for v in summary['validation'])),
              'calibration_controls':len(summary['calibration']),
              'route_cost_seconds':load(root / 'calibrated-costs.json')['route_seconds'],
              'budget_seconds':summary['budget_seconds'], 'sessions':rows,
              'session_callback_invocations':sum(r['callback_invocations'] for r in rows),
              'session_workers_started':sum(r['workers_started'] for r in rows),
              'session_credited_completed':sum(r['credited_completed'] for r in rows),
              'independent_reset_records':len(resets),
              'confirmed_parent_browser_cleanup_records':len(cleanup),
              'comparison_contexts':list(contexts),
              'late_feedback_credited':0, 'immutable_inputs_verified':True,
              'analysis_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'application_defect_or_method_effectiveness_claim':False}
    (root / 'runtime-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
