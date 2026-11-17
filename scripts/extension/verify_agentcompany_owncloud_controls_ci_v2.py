"""Bind ordinary-control artifacts to the frozen run and reconstruct its outcome."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from score_agentcompany_owncloud_controls_v2 import qualify, BRANCHES, ROOT

HEAD = 'b28ba915abef9652d7829425592f75aa42cf4a23'
RUN = 44054061318
JOB = 133938727961


def build(base):
    run = json.loads((base / 'run.json').read_text())
    assert run['databaseId'] == RUN and run['headSha'] == HEAD and run['status'] == 'completed'
    assert len(run['jobs']) == 1 and run['jobs'][0]['databaseId'] == JOB
    job = run['jobs'][0]
    artifact = base / 'artifact'
    registration = json.loads((ROOT / 'manifests/agentcompany-owncloud-ordinary-v1.json').read_text())
    if (artifact / 'runtime.json').exists():
        runtime = json.loads((artifact / 'runtime.json').read_text())
        assert runtime['head'] == HEAD and runtime['run_id'] == str(RUN)
        results = {b: json.loads((artifact / b / 'result.json').read_text()) for b in BRANCHES if (artifact / b / 'result.json').exists()}
        outcome = qualify(runtime, results, registration)
        assert outcome == json.loads((artifact / 'qualification.json').read_text())
    else:
        assert job['conclusion'] != 'success'
        runtime, results = {}, {}
        outcome = dict(qualified=False, problems=['runtime_not_started'], scientific_cases=0, confirmed_defects=0)
    timing = json.loads((base / 'timing.json').read_text())
    ubuntu = timing['billable']['UBUNTU']
    assert ubuntu['jobs'] == len(ubuntu['job_runs']) == 1
    assert ubuntu['job_runs'][0]['job_id'] == JOB
    assert ubuntu['total_ms'] == sum(r['duration_ms'] for r in ubuntu['job_runs'])
    def timestamp(value):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    return dict(run_id=RUN, frozen_head=HEAD, job_id=JOB, conclusion=run['conclusion'], qualification=outcome,
                runtime_status=runtime.get('status'), runtime_error=runtime.get('error'),
                branches=[dict(branch=b, stage=r.get('stage'), passed=r.get('passed'), error=r.get('error')) for b, r in results.items()],
                elapsed_job_seconds=(timestamp(job['completedAt']) - timestamp(job['startedAt'])).total_seconds(),
                reported_billable_execution_ms=ubuntu['total_ms'],
                archive_sha256={str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*')) if p.is_file()},
                scope='One ordinary qualification run; billing is not a whole-account invoice. No scientific cases or confirmed defects.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build(ROOT / f'results/agentcompany-owncloud-ordinary-ci-{RUN}')
    destination = ROOT / 'manifests/agentcompany-owncloud-ordinary-outcome-v2.json'
    if args.verify:
        assert json.loads(destination.read_text()) == value
    else:
        destination.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k != 'archive_sha256'}, indent=2))
