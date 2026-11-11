#!/usr/bin/env python3
"""Close the frozen six-lead feasibility cohort without treating exclusions as negatives."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    sources = {}
    def proof(name):
        path = ROOT / 'manifests' / name
        sources[str(path.relative_to(ROOT))] = sha(path)
        value = json.loads(path.read_text())
        for file, expected in value.get('raw_sha256', {}).items():
            assert sha(ROOT / file) == expected, file
        return value
    tiller = proof('write-preservation-calibration-results-v2.json')
    iris = proof('iris-write-preservation-results-v1.json')
    vikunja = proof('vikunja-bulk-exclusion-v1.json')
    fastdash = proof('fastdash-cascade-results-v2.json')
    attempts = [proof(f'testplanit-tags-attempt{i}-v1.json') for i in (1, 2)]
    cost = proof('testplanit-tags-cost-v1.json')
    correction = proof('testplanit-tags-calibration-v2.json')
    for name, expected in correction['artifact_sha256'].items():
        assert sha(ROOT / name) == expected
    assert tiller['calibration_gate_passed'] and iris['calibration_gate_passed']
    assert vikunja['scientific_bulk_executions'] == 0
    assert all(a['observations'] == 0 for a in attempts)
    accounting = ROOT / 'results/testplanit-tags-accounting-v1'
    for run_id, failed_step in [(43090047548, 'Start host and warm read-only routes'),
                                (43090747883, 'Execute historical and fixed adapter cases on same host')]:
        jobs = json.loads((accounting / f'{run_id}-jobs.json').read_text())['jobs']
        assert len(jobs) == 1 and jobs[0]['conclusion'] == 'failure'
        failed = [s['name'] for s in jobs[0]['steps'] if s['conclusion'] == 'failure']
        assert failed == [failed_step]
        archive = ROOT / f'results/testplanit-tags-v{1 if run_id == 43090047548 else 2}-ci-{run_id}'
        assert not list(archive.rglob('*-observation.json'))
        for name, expected in [('update-historical.ts', '7b8453bdca45afeb07146809bd1f91e30826c6d9'),
                               ('update-fixed.ts', '96a2b1b711623a49705c14081317d7831538c298'),
                               ('pnpm-lock.yaml', '49a753c7e410f6530742e891bf1e6f27139b045b')]:
            paths = list(archive.glob('*/source/' + name)); assert len(paths) == 1
            data = paths[0].read_bytes()
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    assert 'HTTP Error 405' in (accounting / '43090047548-job.log').read_text()
    assert 'Command "tsx" not found' in (accounting / '43090747883-job.log').read_text()
    documents = ['protocol/write-contract-corpus-expansion-v1.md', 'notes/write_contract_admission_decisions_20261111.md']
    for name in documents:
        sources[name] = sha(ROOT / name)
    return {
        'kind': 'frozen_write_contract_corpus_disposition_v1',
        'finite_cohort_closed': True, 'selected_leads': 6,
        'dispositions': [
            {'project': 'tiller', 'status': 'qualified_historical_repair', 'executions': tiller['executions'], 'known_mechanisms': 1},
            {'project': 'iris', 'status': 'qualified_historical_component_intervention', 'executions': iris['executions'], 'known_mechanisms': 1},
            {'project': 'superset', 'status': 'excluded_ambiguous_pre_repair_contract', 'executions': 0},
            {'project': 'vikunja', 'status': 'excluded_bulk_authorization_qualification', 'scientific_bulk_executions': 0},
            {'project': 'fastdash', 'status': 'observed_with_failed_repair_agreement', 'executions': fastdash['executions'], 'known_reported_mechanisms': 1, 'fully_qualified_repair': False},
            {'project': 'testplanit', 'status': 'excluded_harness_launch_failure', 'executions': 0, 'attempts': 2, 'remaining_attempts': 0},
        ],
        'executions_in_qualified_repair_calibrations': tiller['executions'] + iris['executions'],
        'additional_cascade_observations': fastdash['executions'],
        'fully_qualified_historical_repair_projects': 2,
        'new_defects_claimed': 0,
        'automated_advantage_over_competent_manual_contract_demonstrated': False,
        'independent_input_cohort_unchanged': True,
        'q1_contribution_established': False,
        'expansion_job_elapsed_minutes': cost['bounded_expansion_job_elapsed_minutes'],
        'source_sha256': sources,
        'interpretation': 'The registered feasibility cohort is closed. Exclusions are unmeasured outcomes, not passing or defect-free applications. Known-case observations and correlated variants do not establish independent accuracy, prevalence, current-release defects, or journal readiness.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    output = ROOT / 'manifests/write-contract-corpus-disposition-v1.json'
    if args.verify:
        assert json.loads(output.read_text()) == value
    else:
        assert not output.exists()
        output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('source_sha256', 'dispositions', 'interpretation')}))


if __name__ == '__main__':
    main()
