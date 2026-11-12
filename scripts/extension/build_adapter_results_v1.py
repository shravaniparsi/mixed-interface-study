#!/usr/bin/env python3
"""Reconstruct bounded converter feasibility results and job-time accounting."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from verify_adapter_comparison_archive_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
INITIAL = ROOT / 'results/openapi-adapter-comparison-v1-ci-43163040718'
CORRECTION = ROOT / 'results/openapi-adapter-comparison-v2-ci-43163575286'

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    runs = [json.loads((folder / 'run.json').read_text()) for folder in [INITIAL, CORRECTION]]
    assert runs[0]['headSha'] == 'b64f898aae93cc384919da08f5218ee3e86f66b3'
    assert runs[1]['headSha'] == '57d819bf98685e990a2a9c36a5393de776ced626'
    assert all(run['status'] == 'completed' for run in runs)
    jobs = []
    for run in runs:
        for job in run['jobs']:
            duration = (datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) - datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()
            jobs.append({'job_id': job['databaseId'], 'name': job['name'], 'conclusion': job['conclusion'], 'elapsed_seconds': duration})
    assert len(jobs) == 4 and sum(j['elapsed_seconds'] for j in jobs) <= 90 * 60
    subjects = {}
    paths = {'prefect': INITIAL / 'adapter-prefect-43163040718-1', 'ivo-toby': INITIAL / 'adapter-ivo-toby-43163040718-1', 'punkpeye': CORRECTION / 'adapter-v2-punkpeye-43163575286-1'}
    for subject, folder in paths.items():
        comparison = folder / 'comparison'
        if (comparison / 'observations.json').exists():
            checked = verify(comparison)
            observation = json.loads((comparison / 'observations.json').read_text())
            scores = json.loads((comparison / 'scores.json').read_text())
            checked.update({'unique_source_cases_executed': len({r['case_id'] for r in observation['records']}), 'planned_unique_source_cases': 48, 'planned_pairs': 96, 'unexecuted_pairs': 96 - len(observation['records']), 'classification_counts': dict(Counter(r['classification'] for r in scores['records'])), 'tool_schema_invalid_pairs': sum(not r['tool_schema_valid'] for r in scores['records']), 'error': observation.get('error')})
        else:
            checked = {'subject': subject, 'terminal': 'no_comparison_archive', 'verified_pairs': 0, 'unique_source_cases_executed': 0, 'planned_unique_source_cases': 48, 'planned_pairs': 96, 'unexecuted_pairs': 96, 'classification_counts': {}}
        subjects[subject] = checked
    files = sorted(p for folder in [INITIAL, CORRECTION] for p in folder.rglob('*') if p.is_file())
    result = {'kind': 'openapi_adapter_feasibility_results_v1', 'subjects': subjects, 'jobs': jobs, 'application_job_seconds': sum(j['elapsed_seconds'] for j in jobs), 'application_job_minutes': sum(j['elapsed_seconds'] for j in jobs) / 60, 'paid_model_calls': 0, 'billing_amount_verified': False, 'case_repetitions_are_independent_defects': False, 'q1_readiness_established': False, 'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    target = ROOT / 'manifests/openapi-adapter-results-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == result
    else:
        target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, indent=2))

if __name__ == '__main__':
    main()
