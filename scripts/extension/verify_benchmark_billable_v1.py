#!/usr/bin/env python3
"""Bind GitHub timing responses to the archived benchmark jobs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    folder = ROOT / 'results/benchmark-actions-billable-v1'
    cost = json.loads((ROOT / 'manifests/benchmark-archived-compute-v1.json').read_text())
    expected = {r['run_id']: {j['job_id'] for j in r['jobs']} for r in cost['runs']}
    readme = json.loads((ROOT / 'results/benchmark-gitlab-readme-inputs-v1-ci-44033922143/run.json').read_text())
    expected[readme['databaseId']] = {j['databaseId'] for j in readme['jobs']}
    collection = json.loads((folder / 'collection.json').read_text())
    assert set(collection['run_ids']) == set(expected)
    rows = []
    for rid, jobs in expected.items():
        response = json.loads((folder / f'{rid}.json').read_text())
        actual = set()
        milliseconds = 0
        for runner, item in response['billable'].items():
            assert runner == 'UBUNTU'
            assert item['jobs'] == len(item['job_runs'])
            assert item['total_ms'] == sum(j['duration_ms'] for j in item['job_runs'])
            for job in item['job_runs']:
                assert job['job_id'] not in actual
                actual.add(job['job_id'])
            milliseconds += item['total_ms']
        assert actual == jobs
        rows.append({'run_id': rid, 'job_count': len(jobs), 'reported_billable_ms': milliseconds})
    sources = list(folder.glob('*.json')) + [ROOT / 'manifests/benchmark-archived-compute-v1.json', ROOT / 'results/benchmark-gitlab-readme-inputs-v1-ci-44033922143/run.json']
    return {
        'kind': 'benchmark_actions_reported_billable_v1',
        'run_count': len(rows), 'job_count': sum(r['job_count'] for r in rows),
        'reported_billable_ms': sum(r['reported_billable_ms'] for r in rows),
        'collected_at_utc': collection['collected_at_utc'],
        'scope': 'GitHub run-timing endpoint for 17 archived benchmark runs; job IDs matched to retained terminal metadata.',
        'limitation': 'Reported billable execution time is not a whole-account invoice. Storage, other runs, subscriptions and non-GitHub charges are outside this response.',
        'billed_dollars': None,
        'runs': rows,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    target = ROOT / 'manifests/benchmark-actions-billable-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('runs', 'source_sha256')}, indent=2))
