#!/usr/bin/env python3
"""Reconstruct elapsed Actions job accounting, not cash or billable minutes."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def build():
    folder = ROOT / 'results/fastdash-cascade-accounting-v1'
    value = json.loads((folder / '43088065630-jobs.json').read_text())
    run = json.loads((folder / '43088065630-run.json').read_text())
    assert value['total_count'] == len(value['jobs']) == 3
    assert run['conclusion'] == 'success' and run['status'] == 'completed'
    rows = []
    for job in value['jobs']:
        parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
        rows.append({'job_id': job['id'], 'name': job['name'], 'conclusion': job['conclusion'],
                     'elapsed_seconds': (parse(job['completed_at']) - parse(job['started_at'])).total_seconds()})
    return {'kind': 'fastdash_cascade_job_accounting_v1', 'run_id': 43088065630,
            'application_runs': 1, 'jobs': rows,
            'job_elapsed_minutes': sum(r['elapsed_seconds'] for r in rows) / 60,
            'paid_model_calls': 0,
            'scope': 'Includes environment resolution and two version jobs. Excludes other cohorts, unit checks, assistant/tool usage and local work. Elapsed job time is not an invoice or billed minutes.',
            'raw_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(folder.iterdir()) if p.is_file()}}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    output = ROOT / 'manifests/fastdash-cascade-cost-v1.json'
    if args.verify:
        assert result == json.loads(output.read_text())
    else:
        assert not output.exists()
        output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'application_runs': result['application_runs'], 'jobs': len(result['jobs']),
                      'job_elapsed_minutes': result['job_elapsed_minutes']}))

if __name__ == '__main__':
    main()
