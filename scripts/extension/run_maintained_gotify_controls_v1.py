"""Prepared combined-job ordinary controls; no scientific variants or retries."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
from gotify_state_v1 import read_state

NET = 'study-gotify-v1'
NAME = 'study-gotify-app-v1'
BASE = 'http://172.30.79.2'


def inventory(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Unexpected symlink in persistence')
        result[str(p.relative_to(root))] = (
            {'directory': True} if p.is_dir() else
            {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    return result


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Only the registered isolated CI runner may execute controls')
    out = Path(os.environ['RUNNER_TEMP']) / 'evidence'
    workspace = Path(os.environ['RUNNER_TEMP']) / 'gotify-controls'
    workspace.mkdir()  # Refuse any repeated execution in this job.
    summary = {'status': 'unavailable', 'scientific_cases': 0, 'arms': [], 'snapshots': []}
    deadline = float(os.environ['STUDY_JOB_DEADLINE']) - 60
    build = json.loads((out / 'gotify-build.json').read_text())
    if build['status'] != 'built':
        raise SystemExit('No successful fixed-source build')
    image = build['image_id']

    def cmd(args, timeout=30):
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError('Shared qualification deadline')
        return subprocess.check_output(args, stderr=subprocess.STDOUT, timeout=min(timeout, remaining), text=True)

    def start(data):
        data.mkdir(exist_ok=True)
        args = ['docker', 'run', '-d', '--user', str(os.getuid()) + ':' + str(os.getgid()),
                '--name', NAME, '--network', NET, '--ip', '172.30.79.2',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--tmpfs', '/tmp:rw,nosuid,nodev', '-v', str(data) + ':/app/data']
        for value in ['GOTIFY_DATABASE_DIALECT=sqlite3', 'GOTIFY_DATABASE_CONNECTION=data/gotify.db',
                      'GOTIFY_DEFAULTUSER_NAME=studyadmin', 'GOTIFY_DEFAULTUSER_PASS=StudyFixture2026!',
                      'GOTIFY_UPLOADEDIMAGESDIR=data/images', 'GOTIFY_PLUGINSDIR=data/plugins',
                      'GOTIFY_LOCALAUTH_ENABLED=true', 'GOTIFY_OIDC_ENABLED=false',
                      'GOTIFY_REGISTRATION=false', 'GOTIFY_MCP_ENABLED=false', 'GOTIFY_SERVER_PORT=80']:
            args += ['-e', value]
        cmd(args + [image])
        readiness = []
        until = min(deadline, time.time() + 60)
        while time.time() < until:
            try:
                with urllib.request.urlopen(BASE + '/health', timeout=2) as response:
                    readiness.append({'status': response.status})
                    if response.status == 200:
                        return readiness
            except Exception as exc:
                readiness.append({'error': str(exc)})
            time.sleep(1)
        raise RuntimeError('Readiness unavailable: ' + json.dumps(readiness))

    def stop(label):
        cmd(['docker', 'stop', '-t', '20', NAME], 25)
        inspection = json.loads(cmd(['docker', 'inspect', NAME]))[0]
        (out / (label + '-container.json')).write_text(json.dumps(inspection, indent=2) + '\n')
        (out / (label + '-server.log')).write_text(cmd(['docker', 'logs', NAME]))
        if inspection['State']['ExitCode'] != 0:
            raise RuntimeError('Non-clean application shutdown')
        cmd(['docker', 'rm', NAME])

    def run_arm(arm, data, fixture=None):
        dest = out / arm
        dest.mkdir()
        record = {'arm': arm, 'status': 'unavailable', 'started_unix': time.time()}
        summary['arms'].append(record)
        record['readiness'] = start(data)
        args = ['node', 'scripts/extension/qualify_maintained_gotify_v1.mjs',
                '--out', str(dest), '--arm', arm, '--base', BASE,
                '--database', str(data / 'gotify.db')]
        if fixture:
            args += ['--fixture', str(fixture)]
        with (dest / 'adapter.log').open('wb') as log:
            r = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                               timeout=max(1, min(180, deadline - time.time())))
        record['exit_code'] = r.returncode
        record['status'] = json.loads((dest / 'control.json').read_text())['status'] if (dest / 'control.json').exists() else 'adapter_unavailable'
        stop(arm)
        record['elapsed_seconds'] = time.time() - record['started_unix']
        if r.returncode or record['status'] != 'qualified':
            raise RuntimeError('Ordinary arm failed: ' + arm)

    try:
        cmd(['docker', 'network', 'create', '--internal', '--subnet', '172.30.79.0/24', NET])
        net = json.loads(cmd(['docker', 'network', 'inspect', NET]))
        if not net[0]['Internal']:
            raise RuntimeError('Runtime network is not isolated')
        (out / 'gotify-network.json').write_text(json.dumps(net, indent=2) + '\n')
        run_arm('ui-ui', workspace / 'native')
        producer = workspace / 'producer'
        run_arm('producer', producer)
        fixture = out / 'producer/fixture.json'
        snapshot = workspace / 'snapshot'
        shutil.copytree(producer, snapshot)
        fingerprint = inventory(snapshot)
        if inventory(producer) != fingerprint:
            raise RuntimeError('Snapshot copy mismatch')
        state = read_state(snapshot / 'gotify.db')
        Path(str(fixture) + '.database.json').write_text(json.dumps(state, sort_keys=True) + '\n')
        (out / 'snapshot-inventory.json').write_text(json.dumps(fingerprint, indent=2) + '\n')
        summary['snapshots'].append({'source': 'producer', 'files': fingerprint})
        for arm in ['api', 'ui']:
            branch = workspace / arm
            shutil.copytree(snapshot, branch)
            if inventory(branch) != fingerprint or inventory(snapshot) != fingerprint:
                raise RuntimeError('Restored persistence differs')
            run_arm(arm, branch, fixture)
        if inventory(snapshot) != fingerprint:
            raise RuntimeError('Immutable snapshot changed')
        summary['status'] = 'qualified'
    except Exception as exc:
        summary.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        # Best-effort cleanup also covers adapter timeouts. Preserve logs first.
        for action in ['logs', 'inspect']:
            try:
                r = subprocess.run(['docker', action, NAME], capture_output=True, text=True, timeout=20)
                (out / ('final-' + action + '.txt')).write_text(r.stdout + r.stderr)
            except subprocess.TimeoutExpired:
                pass
        subprocess.run(['docker', 'rm', '-f', NAME], capture_output=True, timeout=20)
        subprocess.run(['docker', 'network', 'rm', NET], capture_output=True, timeout=20)
        (out / 'gotify-controls-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    raise SystemExit(0 if summary['status'] == 'qualified' else 1)


if __name__ == '__main__':
    main()
