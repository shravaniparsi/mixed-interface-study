#!/usr/bin/env python3
"""Account for both bounded TestPlanIt attempts, including setup failures."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = [43090047548, 43090747883]


def build():
    folder = ROOT / 'results/testplanit-tags-accounting-v1'
    rows = []
    for run_id in RUNS:
        run = json.loads((folder / f'{run_id}-run.json').read_text())
        jobs = json.loads((folder / f'{run_id}-jobs.json').read_text())
        assert run['id'] == run_id and run['status'] == 'completed'
        assert run['run_attempt'] == 1
        assert jobs['total_count'] == len(jobs['jobs']) == 1
        for job in jobs['jobs']:
            assert job['status'] == 'completed' and job['run_id'] == run_id
            parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
            rows.append({'run_id': run_id, 'study_commit': run['head_sha'],
                         'job_id': job['id'], 'conclusion': job['conclusion'],
                         'elapsed_seconds': (parse(job['completed_at']) - parse(job['started_at'])).total_seconds()})
    elapsed = sum(r['elapsed_seconds'] for r in rows) / 60
    previous = {name: json.loads((ROOT / name).read_text())['job_elapsed_minutes'] for name in
                ['manifests/vikunja-bulk-cost-v1.json', 'manifests/fastdash-cascade-cost-v1.json']}
    return {'kind': 'testplanit_tags_job_accounting_v1', 'application_runs': len(RUNS),
            'jobs': rows, 'job_elapsed_minutes': elapsed,
            'bounded_expansion_job_elapsed_minutes': elapsed + sum(previous.values()),
            'earlier_expansion_job_minutes': previous, 'paid_model_calls': 0,
            'scope': 'Elapsed application-job time includes failed preparation. Not an invoice or billed minutes. Excludes unit CI, local work, assistant usage, and earlier independent-input/Tiller/Iris cohorts.',
            'raw_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(folder.iterdir()) if p.is_file()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    output = ROOT / 'manifests/testplanit-tags-cost-v1.json'
    if args.verify:
        assert json.loads(output.read_text()) == value
    else:
        assert not output.exists()
        output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: value[k] for k in ['application_runs', 'job_elapsed_minutes', 'bounded_expansion_job_elapsed_minutes']}))


if __name__ == '__main__':
    main()
