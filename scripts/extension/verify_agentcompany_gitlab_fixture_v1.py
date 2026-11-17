"""Reconstruct the frozen read-only GitLab diagnostic, including denial outcomes."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
RUN = 44057447970
JOB = 133950348352
HEAD = 'f900bf70db5f44b5c659a26a9fb1874eddf628e6'
IMAGE = 'ghcr.io/theagentcompany/servers-gitlab@sha256:6c61011c225953f3c081eb44e5ba80068489f31289aeb31ccf621c3df024142e'


def reconstruct_fixture(requests, payloads):
    assert len(requests) == 6 and all(r['method'] == 'GET' and r['status'] == 200 for r in requests)
    assert requests[0]['path'] == '/api/v4/user' and requests[1]['path'] == '/api/v4/projects/root%2Frisingwave'
    user, project = payloads[0], payloads[1]
    assert user.get('username') == 'root' and user.get('is_admin') is True
    assert project.get('path_with_namespace') == 'root/risingwave'
    result = {}
    for row, data, resource, title, label in zip(requests[2:], payloads[2:],
            ['milestones', 'milestones', 'issues', 'issues'],
            ['Alpha Release', 'Beta Release', 'Implement stream processing engine', 'Integrate with Kafka'],
            ['alpha', 'beta', 'issue_engine', 'issue_kafka']):
        url = urlsplit(row['path'])
        assert url.path == '/api/v4/projects/' + str(project['id']) + '/' + resource
        assert parse_qs(url.query) == {'per_page': ['100'], 'search': [title]}
        assert not row['next_page'] and isinstance(data, list)
        matches = [r for r in data if r.get('title') == title]
        result[label] = [dict(id=r['id'], iid=r.get('iid'), title=r['title'], state=r.get('state'), project_id=r.get('project_id'), milestone=r.get('milestone')) for r in matches]
    return result


def build():
    base = ROOT / f'results/agentcompany-gitlab-fixture-ci-{RUN}'
    artifact = base / 'artifact'
    run = json.loads((base / 'run.json').read_text())
    assert run['databaseId'] == RUN and run['headSha'] == HEAD and run['status'] == 'completed'
    assert len(run['jobs']) == 1 and run['jobs'][0]['databaseId'] == JOB
    job = run['jobs'][0]
    runtime = json.loads((artifact / 'runtime.json').read_text())
    assert runtime['head'] == HEAD and runtime['run_id'] == str(RUN) and runtime['image'] == IMAGE
    assert runtime['scientific_cases'] == runtime['task_mutations'] == 0
    requests = runtime['requests']
    assert len(requests) <= 6 and all(r['method'] == 'GET' for r in requests)
    payloads = []
    for row in requests:
        raw = (artifact / row['file']).read_bytes()
        assert len(raw) == row['bytes']
        payloads.append(json.loads(raw))
    cleanup_ok = runtime.get('cleanup') == {'container_and_volumes': 0, 'network': 0}
    if runtime.get('container_id'):
        inspected = json.loads((artifact / 'container-state.log').read_text())[0]
        assert inspected['Id'] == runtime['container_id']
        assert inspected['Config']['Image'] == IMAGE
        assert inspected['HostConfig']['Memory'] == 10 * 1024**3
        assert inspected['HostConfig']['NetworkMode'] == 'tac-gitlab-diagnostic-' + str(RUN)
        assert inspected['HostConfig']['PortBindings'] == {'8929/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8929'}]}
        mounts = inspected['Mounts']
        assert {m['Destination'] for m in mounts} == {'/etc/gitlab', '/var/log/gitlab', '/var/opt/gitlab'}
        assert all(m['Type'] == 'volume' for m in mounts)
    version = (artifact / 'version.txt').read_text().strip() if (artifact / 'version.txt').exists() else None
    lifecycle = None
    token_file = artifact / 'token-lifecycle.log'
    if token_file.exists():
        for line in token_file.read_text().splitlines():
            try:
                candidate = json.loads(line)
            except ValueError:
                continue
            if isinstance(candidate, dict) and 'user_exists' in candidate and 'tokens' in candidate:
                assert lifecycle is None
                lifecycle = candidate
        if lifecycle:
            assert all(set(t) == {'name', 'expires_at', 'revoked', 'active'} and t['name'] == 'root-token' for t in lifecycle['tokens'])
    if runtime['status'] == 'authentication_denied':
        assert len(requests) == 1 and requests[0]['path'] == '/api/v4/user' and requests[0]['status'] in (401, 403)
        assert 'fixture' not in runtime
    elif runtime['status'] == 'diagnostic_completed':
        assert reconstruct_fixture(requests, payloads) == runtime['fixture']
    else:
        assert runtime['status'] in ('diagnostic_failed', 'in_progress')
    if runtime['status'] in ('authentication_denied', 'diagnostic_completed'):
        assert version and version.startswith('17.5.1')
        assert any(r.get('status') == 200 and r.get('body', '').strip() == 'GitLab OK' for r in runtime['readiness'])
        assert IMAGE in runtime['image_identity']['RepoDigests']
    timing = json.loads((base / 'timing.json').read_text())['billable']['UBUNTU']
    assert timing['jobs'] == len(timing['job_runs']) == 1 and timing['job_runs'][0]['job_id'] == JOB
    assert timing['total_ms'] == sum(j['duration_ms'] for j in timing['job_runs'])
    def timestamp(s): return datetime.fromisoformat(s.replace('Z', '+00:00'))
    return dict(run_id=RUN, job_id=JOB, frozen_head=HEAD, conclusion=run['conclusion'], diagnostic_status=runtime['status'],
                stage=runtime['stage'], error=runtime.get('error'), packaged_version=version, cleanup_verified=cleanup_ok,
                request_statuses=[dict(path=r['path'], status=r['status']) for r in requests], token_lifecycle=lifecycle,
                fixture=runtime.get('fixture'), elapsed_job_seconds=(timestamp(job['completedAt'])-timestamp(job['startedAt'])).total_seconds(),
                reported_billable_execution_ms=timing['total_ms'], scientific_cases=0, confirmed_defects=0,
                scope='One read-only infrastructure diagnostic, not a scientific task or whole-account invoice.',
                archive_sha256={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*')) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); output = ROOT / 'manifests/agentcompany-gitlab-fixture-outcome-v1.json'
    if args.verify: assert json.loads(output.read_text()) == value
    else: output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k:v for k,v in value.items() if k != 'archive_sha256'}, indent=2))
