"""Bounded read-only service/auth/fixture diagnostic; no task mutations."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IMAGE = 'ghcr.io/theagentcompany/servers-gitlab@sha256:6c61011c225953f3c081eb44e5ba80068489f31289aeb31ccf621c3df024142e'
GIB = 1024**3


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    report = dict(head=os.environ['GITHUB_SHA'], run_id=os.environ['GITHUB_RUN_ID'], image=IMAGE,
                  status='in_progress', stage='capacity', scientific_cases=0, task_mutations=0,
                  requests=[], readiness=[], cleanup={})
    cid = None; network = None

    def save():
        (out / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(command, timeout=30):
        return subprocess.run(command, capture_output=True, timeout=timeout)

    def get(path, name, authenticate=True):
        headers = {'PRIVATE-TOKEN': 'root-token'} if authenticate else {}
        request = urllib.request.Request('http://127.0.0.1:8929' + path, headers=headers, method='GET')
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(2 * 1024**2 + 1)
            assert len(raw) <= 2 * 1024**2, 'Response exceeds fixed archive bound'
            record = dict(method='GET', path=path, status=response.status, next_page=response.headers.get('X-Next-Page', ''), bytes=len(raw), file=name + '.json')
        (out / record['file']).write_bytes(raw)
        report['requests'].append(record); save()
        return record, json.loads(raw)

    def terminated(signum, frame):
        raise TimeoutError("Outer runtime deadline reached")

    signal.signal(signal.SIGTERM, terminated)
    save()
    try:
        memory = int(Path('/proc/meminfo').read_text().split('MemTotal:')[1].split()[0]) * 1024
        report['capacity_before'] = dict(disk_free=shutil.disk_usage('/').free, memory_total=memory, cpus=os.cpu_count())
        save()
        assert report['capacity_before']['disk_free'] >= 70_000_000_000, 'Insufficient disk: no cleanup or substitute'
        assert memory >= 12 * GIB and os.cpu_count() >= 4, 'Insufficient memory/CPU'
        report['stage'] = 'pull'; save()
        pulled = run(['docker', 'pull', IMAGE], 900)
        (out / 'pull.log').write_bytes(pulled.stdout + pulled.stderr)
        assert pulled.returncode == 0, 'Image pull failed'
        inspected = run(['docker', 'image', 'inspect', IMAGE]); assert inspected.returncode == 0
        info = json.loads(inspected.stdout)[0]
        report['image_identity'] = {k: info[k] for k in ('Id', 'RepoDigests', 'Architecture', 'Os', 'Size', 'Created')}
        assert IMAGE in info['RepoDigests'] and info['Architecture'] == 'amd64' and info['Os'] == 'linux'
        assert info['Size'] <= 45 * GIB and shutil.disk_usage('/').free >= 20 * GIB, 'Post-pull capacity bound failed'
        report['stage'] = 'startup'; save()
        name = 'tac-gitlab-diagnostic-' + os.environ['GITHUB_RUN_ID']
        made = run(['docker', 'network', 'create', '--internal', name]); assert made.returncode == 0
        network = name
        started = run(['docker', 'run', '-d', '--network', network, '--hostname', 'the-agent-company.com',
                       '--memory', '10g', '--cpus', '4', '--shm-size', '256m', '-p', '127.0.0.1:8929:8929',
                       '-e', "GITLAB_OMNIBUS_CONFIG=external_url 'http://the-agent-company.com:8929'; gitlab_rails['gitlab_shell_ssh_port'] = 2424", IMAGE], 120)
        assert started.returncode == 0, started.stderr.decode()
        cid = started.stdout.decode().strip(); assert len(cid) == 64
        report['container_id'] = cid
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            row = dict(at=time.time())
            try:
                with urllib.request.urlopen('http://127.0.0.1:8929/-/health', timeout=10) as response:
                    row.update(status=response.status, body=response.read(4096).decode(errors='replace'))
            except Exception as error:
                row.update(error_type=type(error).__name__)
            report['readiness'].append(row); save()
            if row.get('status') == 200 and row.get('body', '').strip() == 'GitLab OK': break
            time.sleep(min(15, max(0, deadline - time.monotonic())))
        else:
            raise RuntimeError('Readiness deadline reached')
        report['stage'] = 'authentication'; save()
        version = run(['docker', 'exec', cid, 'cat', '/opt/gitlab/embedded/service/gitlab-rails/VERSION'])
        (out / 'version.txt').write_bytes(version.stdout + version.stderr)
        assert version.returncode == 0 and version.stdout.decode().strip().startswith('17.5.1')
        status, user = get('/api/v4/user', 'user')
        if status['status'] in (401, 403):
            report['status'] = 'authentication_denied'
            # Read only named-token lifecycle metadata. Never print token hashes or renew credentials.
            ruby = "u=User.find_by_username('root'); puts JSON.generate({user_exists: !u.nil?, tokens: u ? u.personal_access_tokens.where(name: 'root-token').map{|t| {name:t.name,expires_at:t.expires_at,revoked:t.revoked,active:t.active?}} : []})"
            token = run(['docker', 'exec', cid, 'gitlab-rails', 'runner', ruby], 120)
            (out / 'token-lifecycle.log').write_bytes(token.stdout + token.stderr)
            report['token_metadata_returncode'] = token.returncode
            return 1
        assert status['status'] == 200 and user.get('username') == 'root' and user.get('is_admin') is True
        report['stage'] = 'fixture_reads'; save()
        status, project = get('/api/v4/projects/root%2Frisingwave', 'project')
        assert status['status'] == 200 and project.get('path_with_namespace') == 'root/risingwave'
        project_id = project['id']; report['project_id'] = project_id
        fixture = {}
        for resource, title, label in [('milestones', 'Alpha Release', 'alpha'), ('milestones', 'Beta Release', 'beta'),
                                       ('issues', 'Implement stream processing engine', 'issue_engine'), ('issues', 'Integrate with Kafka', 'issue_kafka')]:
            status, data = get('/api/v4/projects/' + str(project_id) + '/' + resource + '?per_page=100&search=' + urllib.parse.quote(title, safe=''), label)
            assert status['status'] == 200 and isinstance(data, list) and not status['next_page'], 'Incomplete or failed fixture query'
            matches = [r for r in data if r.get('title') == title]
            fixture[label] = [dict(id=r['id'], iid=r.get('iid'), title=r['title'], state=r.get('state'), project_id=r.get('project_id'), milestone=r.get('milestone')) for r in matches]
        report['fixture'] = fixture
        report['status'] = 'diagnostic_completed'
        report['fixture_interpretation'] = 'Read-only pre-population state. Missing Alpha/issues may be created by the original task setup; no setup ran here.'
        return 0
    except Exception as error:
        report.update(status='diagnostic_failed', error_type=type(error).__name__, error=str(error)[:2000])
        return 1
    finally:
        if cid:
            for label, command in [('container-state', ['docker', 'inspect', cid]), ('service-status', ['docker', 'exec', cid, 'gitlab-ctl', 'status']), ('container-log', ['docker', 'logs', '--tail', '150', cid])]:
                try:
                    result = run(command, 30); (out / (label + '.log')).write_bytes(result.stdout + result.stderr)
                except Exception as error:
                    report[label + '_error'] = type(error).__name__
            try: report['cleanup']['container_and_volumes'] = run(['docker', 'rm', '-fv', cid], 60).returncode
            except Exception as error: report['cleanup']['container_error'] = type(error).__name__
        if network:
            try: report['cleanup']['network'] = run(['docker', 'network', 'rm', network]).returncode
            except Exception as error: report['cleanup']['network_error'] = type(error).__name__
        report['disk_free_after'] = shutil.disk_usage('/').free
        save()


if __name__ == '__main__': raise SystemExit(main())
