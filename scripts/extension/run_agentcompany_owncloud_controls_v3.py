#!/usr/bin/env python3
"""Run three ordinary paths with fresh ownCloud/Collabora pairs; no case retries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

IMAGES = {
    'owncloud': 'ghcr.io/theagentcompany/servers-owncloud@sha256:326406d88345899db22fc1081aa8fa15415c542a71b80486c0a2cebf59f56f63',
    'collabora': 'collabora/code@sha256:a9dcf35063c4ef58be3fc250d833642b74b9d12c59cac5ea2cd1f3cc655a5b85',
}
BRANCHES = ['native_native', 'api_native', 'api_api']


def main():
    out = Path(sys.argv[1]);out.mkdir(parents=True, exist_ok=True)
    report = {'head': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
              'kind': 'agentcompany_owncloud_controls_runtime_v3', 'images': IMAGES,
              'status': 'in_progress', 'branches': [], 'scientific_cases': 0}
    def save():
        (out / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n')
    def run(args, timeout=30):
        return subprocess.run(args, capture_output=True, timeout=timeout)
    save()
    try:
        for name, image in IMAGES.items():
            response = run(['docker', 'pull', image], 420)
            (out / f'pull-{name}.log').write_bytes(response.stdout + response.stderr)
            assert response.returncode == 0, f'{name} image pull failed'
            inspected = run(['docker', 'image', 'inspect', image])
            assert inspected.returncode == 0
            info = json.loads(inspected.stdout)[0]
            assert image in info['RepoDigests'] and info['Os'] == 'linux' and info['Architecture'] == 'amd64'
        for index, branch in enumerate(BRANCHES):
            directory = out / branch;directory.mkdir()
            row = {'branch': branch, 'containers': {}, 'cleanup': {}, 'node_returncode': None, 'ready': False}
            report['branches'].append(row);save()
            network = f'tac-oc-{os.environ["GITHUB_RUN_ID"]}-{index}'
            started = time.monotonic()
            network_created = False
            try:
                made = run(['docker', 'network', 'create', network]);assert made.returncode == 0
                network_created = True
                for name, port, internal, env in [
                    ('collabora', '9980', '9980', ['extra_params=--o:ssl.enable=false']),
                    ('owncloud', '8092', '80', ['OWNCLOUD_DOMAIN=the-agent-company.com:8092', 'OWNCLOUD_TRUSTED_DOMAINS=localhost,the-agent-company.com:8092', 'OWNCLOUD_ADMIN_USERNAME=theagentcompany', 'OWNCLOUD_ADMIN_PASSWORD=theagentcompany'])]:
                    command = ['docker', 'run', '-d', '--network', network, '--add-host', 'the-agent-company.com:host-gateway', '-p', f'{port}:{internal}']
                    for value in env:command.extend(['-e', value])
                    response = run(command + [IMAGES[name]], 60);assert response.returncode == 0, response.stderr.decode()
                    cid = response.stdout.decode().strip();assert len(cid) == 64 and all(c in '0123456789abcdef' for c in cid)
                    row['containers'][name] = cid;save()
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    try:
                        with urllib.request.urlopen('http://the-agent-company.com:8092/status.php', timeout=5) as response:status = json.load(response)
                        with urllib.request.urlopen('http://the-agent-company.com:9980/hosting/discovery', timeout=5) as response:discovery = response.read(200000)
                        if status.get('installed') and str(status.get('version', '')).startswith('10.0.10.') and b'wopi-discovery' in discovery:
                            row['ready'] = True;row['owncloud_status'] = status;break
                    except Exception:
                        pass
                    time.sleep(2)
                assert row['ready'], 'Service readiness failed; stop schedule'
                save()
                result = run(['node', 'scripts/extension/run_agentcompany_owncloud_control_v3.mjs', branch, str(directory)], 240)
                row['node_returncode'] = result.returncode
                (directory / 'node.log').write_bytes(result.stdout + result.stderr)
            except Exception as error:
                row['error_type'] = type(error).__name__;row['error'] = str(error)[:2000]
            finally:
                for name, cid in row['containers'].items():
                    logs = run(['docker', 'logs', '--tail', '150', cid])
                    (directory / f'{name}.log').write_bytes(logs.stdout + logs.stderr)
                    row['cleanup'][name] = run(['docker', 'rm', '-fv', cid]).returncode
                if network_created:row['cleanup']['network'] = run(['docker', 'network', 'rm', network]).returncode
                row['elapsed_seconds'] = round(time.monotonic() - started, 3);save()
            if not row['ready'] or any(code != 0 for code in row['cleanup'].values()) or 'error_type' in row:
                report['status'] = 'infrastructure_stopped';break
        else:
            report['status'] = 'completed'
    except Exception as error:
        report.update(status='infrastructure_failed', error_type=type(error).__name__, error=str(error)[:2000])
    finally:
        save()
    return 0 if report['status'] == 'completed' and all(r['node_returncode'] == 0 for r in report['branches']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
