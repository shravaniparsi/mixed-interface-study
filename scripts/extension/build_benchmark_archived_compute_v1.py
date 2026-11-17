#!/usr/bin/env python3
"""Reconstruct an explicit archive-scoped compute snapshot, not an invoice."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = (
    'benchmark-host-capacity-v1-ci-43166124958',
    'benchmark-gitlab-image-inspection-v1-ci-43166622248',
    'benchmark-gitlab-startup-v1-ci-43168226517',
    'benchmark-gitlab-connectivity-v1-ci-43170995499',
    'benchmark-gitlab-auth-v2-ci-43172360473',
    'benchmark-gitlab-browser-v1-ci-43173565701',
    'benchmark-gitlab-issue-controls-v1-ci-43175216640',
    'benchmark-gitlab-issue-inputs-v1-ci-43284543994',
    'benchmark-gitlab-members-controls-v1-ci-43290251888',
    'benchmark-gitlab-members-controls-v2-ci-44018502088',
    'benchmark-gitlab-mr-form-v1-ci-44019120926',
    'benchmark-gitlab-members-controls-v3-ci-44021434885',
    'benchmark-gitlab-mr-source-v1-ci-44024863535',
    'benchmark-gitlab-readme-controls-v1-ci-44027377236',
    'benchmark-reddit-api-source-v1-ci-44028579797',
    'benchmark-gitlab-readme-controls-v2-ci-44030229250',
)


def build():
    runs, hashes, seen_jobs, seen_runs = [], {}, set(), set()
    for archive in ARCHIVES:
        path = ROOT / 'results' / archive / 'run.json'
        raw = path.read_bytes()
        run = json.loads(raw)
        rid = int(archive.rsplit('-', 1)[1])
        assert run.get('databaseId', rid) == rid and rid not in seen_runs
        assert run['status'] == 'completed'
        seen_runs.add(rid)
        jobs = []
        for job in run['jobs']:
            jid = job['databaseId']
            assert jid not in seen_jobs and job['status'] == 'completed'
            assert f'/runs/{rid}/job/{jid}' in job['url']
            seen_jobs.add(jid)
            start, end = (datetime.fromisoformat(job[k].replace('Z', '+00:00'))
                          for k in ('startedAt', 'completedAt'))
            seconds = (end - start).total_seconds()
            assert seconds >= 0
            jobs.append({'job_id': jid, 'name': job['name'],
                         'conclusion': job['conclusion'], 'job_seconds': seconds})
        runs.append({'run_id': rid, 'archive': str(path.relative_to(ROOT)),
                     'head_sha': run['headSha'], 'conclusion': run['conclusion'],
                     'jobs': jobs, 'job_seconds': sum(j['job_seconds'] for j in jobs)})
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    seconds = sum(r['job_seconds'] for r in runs)
    return {
        'kind': 'benchmark_archived_compute_snapshot_v1',
        'scope': 'Sixteen explicitly listed terminal benchmark run archives before README scientific completion; not a complete account history or whole-project total.',
        'excluded_pending_run': 44033922143,
        'exclusions': ['Non-benchmark studies', 'Unit and repository verification workflows',
                       'Runs without a listed terminal archive', 'Local work and transfer time'],
        'run_count': len(runs), 'job_count': len(seen_jobs),
        'job_seconds': seconds, 'job_minutes': seconds / 60,
        'failed_job_seconds': sum(j['job_seconds'] for r in runs for j in r['jobs']
                                  if j['conclusion'] == 'failure'),
        'missing_intervals_in_listed_archives': 0,
        'billed_dollars': None,
        'billing_interpretation': 'Elapsed job intervals are compute accounting, not invoices or proof of zero charges.',
        'runs': runs, 'source_sha256': hashes,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    target = ROOT / 'manifests/benchmark-archived-compute-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('runs', 'source_sha256')}, indent=2))
