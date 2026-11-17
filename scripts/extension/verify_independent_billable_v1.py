#!/usr/bin/env python3
"""Verify captured GitHub timing metadata against independent-input job IDs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify():
    value = json.loads((ROOT / 'manifests/independent-input-actions-billable-v1.json').read_text())
    cost_path = ROOT / value['source_cost_manifest']
    assert hashlib.sha256(cost_path.read_bytes()).hexdigest() == value['source_cost_sha256']
    cost = json.loads(cost_path.read_text())
    expected = {r['run_id']: {j['id'] for j in r['jobs']} for r in cost['runs']}
    seen, all_jobs = set(), set()
    for row in value['runs']:
        rid = row['run_id']
        assert rid not in seen
        seen.add(rid)
        raw = (ROOT / row['source']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        data = json.loads(raw)
        jobs = set()
        total = 0
        for label, item in data['billable'].items():
            assert label == 'UBUNTU'
            assert item['jobs'] == len(item['job_runs'])
            assert item['total_ms'] == sum(j['duration_ms'] for j in item['job_runs'])
            total += item['total_ms']
            for j in item['job_runs']:
                assert j['job_id'] not in jobs and j['job_id'] not in all_jobs
                jobs.add(j['job_id'])
        all_jobs.update(jobs)
        assert jobs == expected[rid]
        assert row['job_count'] == len(jobs) and row['reported_billable_ms'] == total
    assert seen == set(expected)
    assert value['run_count'] == len(seen) and value['job_count'] == len(all_jobs)
    assert value['reported_billable_ms'] == sum(r['reported_billable_ms'] for r in value['runs'])
    benchmark = json.loads((ROOT / 'manifests/benchmark-actions-billable-v1.json').read_text())
    assert not {int(r) for r in seen} & {r['run_id'] for r in benchmark['runs']}
    print('Verified 14 independent-input runs and 39 job identities; no overlap with 17 benchmark runs.')


if __name__ == '__main__':
    verify()
