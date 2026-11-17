#!/usr/bin/env python3
"""Verify the terminal metadata-only diagnostic; no effectiveness inference."""
import json
from pathlib import Path
from datetime import datetime
import resolve_agentcompany_services_v1 as resolver

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/agentcompany-service-metadata-ci-44047142832'
HEAD = 'c50aaf7dfe1ac60ef37d2495ae2b5ae161beff36'


def main():
    run = json.loads((BASE / 'run.json').read_text())
    context = json.loads((BASE / 'metadata/context.json').read_text())
    assert run['databaseId'] == 44047142832 and run['headSha'] == HEAD
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert context['head'] == HEAD and context['run_id'] == str(run['databaseId'])
    assert len(run['jobs']) == 1
    job = run['jobs'][0]
    assert job['databaseId'] == 133915554702 and job['conclusion'] == 'success'
    original = json.loads((resolver.BASE / 'collection.json').read_text())
    resolver.BASE = BASE / 'metadata'
    result = resolver.verify()
    current = json.loads((resolver.BASE / 'collection.json').read_text())
    old = {r['image']: r for r in original['images']}
    comparisons = [{'image': r['image'], 'prior_status': old[r['image']]['status'], 'status': r['status'],
                    'prior_digest': old[r['image']].get('platform_manifest', {}).get('digest'),
                    'current_digest': r.get('platform_manifest', {}).get('digest')} for r in current['images']]
    assert comparisons == json.loads((resolver.BASE / 'comparison.json').read_text())
    changed = [r['image'] for r in comparisons if r['prior_digest'] and r['prior_digest'] != r['current_digest']]
    timing = json.loads((BASE / 'timing.json').read_text())
    assert set(timing['billable']) == {'UBUNTU'}
    reported = timing['billable']['UBUNTU']
    assert reported['jobs'] == len(reported['job_runs']) == 1
    assert reported['job_runs'][0]['job_id'] == job['databaseId']
    assert reported['total_ms'] == sum(r['duration_ms'] for r in reported['job_runs'])
    elapsed = (datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) -
               datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()
    print(json.dumps({**result, 'previously_resolved_digest_changes': changed,
                      'job_elapsed_seconds': elapsed, 'reported_billable_execution_ms': reported['total_ms'],
                      'scope': 'One metadata diagnostic, not a whole-project invoice or runtime qualification.'}, indent=2))


if __name__ == '__main__':
    main()
