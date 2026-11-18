#!/usr/bin/env python3
"""Bounded original-application qualification; no altered scientific inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

IMAGE = 'roflcoopter/amd64-viseron@sha256:91c9ffb15859ce05b62792acfacec61c6eaf0de14f9fbe88780c5a8aee2d9a43'
BROWSER = 'mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac'
PG, APP, CONFIG = 'study-viseron-postgres', 'study-viseron', 'study-viseron-config'


def canonical_files(rows):
    result = []
    for item in rows:
        row = dict(item)
        # Capture/restore preserves these values. Only post-operation comparison
        # treats known log contents and write-time metadata separately.
        if row['path'] == 'viseron.log':
            for key in ['sha256', 'bytes', 'mtime_ns']:
                row.pop(key, None)
        elif row['path'] in ['.viseron', '.viseron/auth']:
            row.pop('mtime_ns', None)
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--tools', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    private = out / 'private'
    private.mkdir(mode=0o700, exist_ok=False)
    os.umask(0o077)
    result = {'status': 'qualification_failed', 'phases': [], 'scientific_cases': 0}
    stage = 'initialization'
    started = time.monotonic()

    def command(argv, label, timeout=90, required=True):
        p = subprocess.run(argv, capture_output=True, timeout=timeout)
        # All raw process output stays private; errors can include auth material.
        (private / (label + '.stdout')).write_bytes(p.stdout)
        (private / (label + '.stderr')).write_bytes(p.stderr)
        (out / (label + '-exit.json')).write_text(json.dumps({'exit_code': p.returncode,
            'stdout_sha256': hashlib.sha256(p.stdout).hexdigest(),
            'stderr_sha256': hashlib.sha256(p.stderr).hexdigest()}) + '\n')
        if required and p.returncode:
            raise RuntimeError(label + ' failed')
        return p

    def load(path):
        return json.loads((out / path).read_text())

    def ready(label):
        code = "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8888/api/v1/auth/enabled',timeout=2); assert r.status==200"
        deadline = time.monotonic() + 90
        attempts = []
        while time.monotonic() < deadline:
            p = subprocess.run(['docker', 'exec', APP, 'python3', '-c', code], capture_output=True, timeout=5)
            attempts.append(p.returncode)
            if p.returncode == 0:
                (out / (label + '-readiness.json')).write_text(json.dumps(attempts))
                return
            time.sleep(1)
        (out / (label + '-readiness.json')).write_text(json.dumps(attempts))
        raise RuntimeError('Application readiness deadline')

    def containment(label):
        containers = json.loads(command(['docker', 'inspect', APP, PG], label + '-inspect').stdout)
        app, database = containers
        assert database['HostConfig']['NetworkMode'] == 'none'
        assert app['HostConfig']['NetworkMode'] in ['container:' + PG, 'container:' + database['Id']]
        assert all(c['Image'] == 'sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7' for c in containers)
        assert all(not c['HostConfig']['PortBindings'] for c in containers)
        (out / (label + '-containment.json')).write_text(json.dumps({
            'status': 'isolated_loopback_namespace', 'database_network_mode': 'none',
            'application_network_mode': app['HostConfig']['NetworkMode'],
            'image_ids': [c['Image'] for c in containers], 'published_ports': False}) + '\n')

    def fresh(label):
        command(['docker', 'rm', '-f', '-v', APP, PG], label + '-remove', required=False)
        command(['docker', 'volume', 'rm', CONFIG], label + '-remove-volume', required=False)
        command(['docker', 'volume', 'create', CONFIG], label + '-volume')
        # Supporting PostgreSQL uses the original image's installed binaries;
        # only the database service bypasses /init. Viseron uses original /init.
        pg_script = r'''set -eu
version=$(psql --version | sed -E 's/.* ([0-9]+)\..*/\1/')
bin=/usr/lib/postgresql/$version/bin
mkdir -p /study-pg /var/run/postgresql
chown postgres:postgres /study-pg /var/run/postgresql
s6-setuidgid postgres "$bin/initdb" -D /study-pg --auth-local=trust --auth-host=trust
exec s6-setuidgid postgres "$bin/postgres" -D /study-pg -c listen_addresses=127.0.0.1
'''
        command(['docker', 'run', '-d', '--name', PG, '--network', 'none', '--entrypoint', '/bin/bash', IMAGE, '-c', pg_script], label + '-database')
        deadline = time.monotonic() + 45
        while True:
            p = subprocess.run(['docker', 'exec', PG, 'pg_isready', '-U', 'postgres'], capture_output=True, timeout=5)
            if p.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('Database readiness deadline')
            time.sleep(1)
        command(['docker', 'exec', PG, 'createdb', '-U', 'postgres', 'viseron'], label + '-createdb')
        config_code = "from pathlib import Path; Path('/config/config.yaml').write_text('webserver:\\n  auth: {}\\n')"
        command(['docker', 'run', '--rm', '--network', 'none', '-v', CONFIG + ':/config', '--entrypoint', 'python3', IMAGE, '-c', config_code], label + '-configuration')
        command(['docker', 'run', '-d', '--name', APP, '--network', 'container:' + PG,
                 '-v', CONFIG + ':/config', '-e', 'POSTGRES_DATABASE_URL=postgresql://postgres@127.0.0.1/viseron',
                 '-e', 'TZ=UTC', IMAGE], label + '-application')
        containment(label)
        ready(label)

    def stop(label):
        command(['docker', 'stop', '--time', '25', APP], label + '-stop', timeout=35)
        state = json.loads(command(['docker', 'inspect', APP], label + '-stopped-inspect').stdout)[0]
        assert state['State']['Running'] is False
        command(['docker', 'logs', APP], label + '-app-log', required=False)

    def browser(phase):
        command(['docker', 'run', '--name', 'study-viseron-browser', '--network', 'container:' + PG,
            '--user', f'{os.getuid()}:{os.getgid()}', '--shm-size=1g',
            '-v', args.node + ':/study/node:ro', '-v', str(args.tools.resolve()) + ':/study/tools:ro',
            '-v', str(root) + ':' + str(root) + ':ro', '-v', str(out) + ':' + str(out),
            '-e', 'PLAYWRIGHT_MODULE_PATH=/study/tools/node_modules/playwright', BROWSER,
            '/study/node', str(root / 'scripts/extension/run_viseron_browser_phase_v1.mjs'),
            '--phase', phase, '--out', str(out), '--private', str(private)], phase + '-browser', timeout=150)
        browser_state = json.loads(command(['docker', 'inspect', 'study-viseron-browser'], phase + '-browser-inspect').stdout)[0]
        pg_id = json.loads(command(['docker', 'inspect', PG], phase + '-browser-database-inspect').stdout)[0]['Id']
        assert browser_state['HostConfig']['NetworkMode'] in ['container:' + PG, 'container:' + pg_id]
        (out / (phase + '-browser-containment.json')).write_text(json.dumps({'network_mode': browser_state['HostConfig']['NetworkMode'], 'database_id': pg_id, 'image_id': browser_state['Image'], 'same_isolated_namespace': True}) + '\n')
        assert browser_state['Image'] == 'sha256:fee853fafa59550d162cef52bca02d907694b44ebf6ef9fb075bcc0c65d8dedb'
        command(['docker', 'rm', 'study-viseron-browser'], phase + '-browser-remove')
        assert load(phase + '-browser.json')['status'] == 'ordinary_phase_passed'
        code = "from pathlib import Path; import json; paths=['/tmp/downloads','/config/public_images']; counts={p:sum(x.is_file() for x in Path(p).rglob('*')) for p in paths}; print(json.dumps(counts)); assert not any(counts.values())"
        empty = command(['docker', 'exec', APP, 'python3', '-c', code], phase + '-empty-storage')
        (out / (phase + '-empty-storage.json')).write_bytes(empty.stdout)
        result['phases'].append(phase)

    def database(action, label):
        command(['python3', str(root / 'scripts/extension/viseron_postgres_checkpoint_v1.py'), action,
            '--package-report', str(out / 'packaged-source.json'), '--private', str(private / 'database-checkpoint'),
            '--report', str(out / (label + '-database.json'))], label + '-database-checkpoint', timeout=150)

        state = load(label + '-database.json')['state']
        for name in ['recordings', 'motion']:
            rows = [t for t in state['tables'] if t['schema_name'] == 'public' and t['relation_name'] == name]
            assert len(rows) == 1 and rows[0]['rows'] == 0, 'Nonempty startup-mutated camera state'

    def filesystem(action, label):
        report = out / (label + '-filesystem.json')
        script = str(root / 'scripts/extension/viseron_filesystem_checkpoint_v1.py')
        # No shell interpolation of data: bash positional arguments carry paths.
        command(['docker', 'run', '--rm', '--network', 'none', '-v', CONFIG + ':/state',
            '-v', str(root) + ':' + str(root) + ':ro', '-v', str(out) + ':' + str(out),
            '--entrypoint', '/bin/bash', IMAGE, '-c',
            'set -eu; python3 "$1" "$2" --checkpoint "$3" --report "$4"; chown "$5" "$4"', '_',
            script, action, str(private / 'filesystem-checkpoint'), str(report), f'{os.getuid()}:{os.getgid()}'], label + '-filesystem-checkpoint')
        code = "import sys,json; sys.path.insert(0,sys.argv[1]); from viseron_filesystem_checkpoint_v1 import inventory; print(json.dumps(inventory('/state')))"
        p = command(['docker', 'run', '--rm', '--network', 'none', '-v', CONFIG + ':/state:ro',
            '-v', str(root) + ':' + str(root) + ':ro', '--entrypoint', 'python3', IMAGE, '-c', code,
            str(root / 'scripts/extension')], label + '-filesystem-inventory')
        rows = json.loads(p.stdout)
        assert not any(row['path'].startswith('postgresql') for row in rows)
        assert not any(row['kind'] == 'file' and row['path'].startswith('public_images/') for row in rows)
        (out / (label + '-filesystem-inventory.json')).write_text(json.dumps(rows, indent=2) + '\n')

    def timeout(*_):
        raise TimeoutError('1200-second original-runtime envelope')

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(1200)
    try:
        for phase in ['producer', 'warm', 'seed']:
            stage = phase
            fresh(phase)
            browser(phase)
            stop(phase)
            database('capture' if phase == 'seed' else 'inspect', phase)
            filesystem('capture' if phase == 'seed' else 'inspect', phase)
        for phase in ['native', 'api']:
            stage = phase
            database('restore', phase + '-before')
            filesystem('restore', phase + '-before')
            command(['docker', 'start', APP], phase + '-start')
            containment(phase)
            ready(phase)
            browser(phase)
            stop(phase)
            database('inspect', phase + '-after')
            filesystem('inspect', phase + '-after')
        stage = 'comparison'
        native, api = [load(p + '-browser.json') for p in ['native', 'api']]
        for key in ['actor', 'before', 'after', 'request']:
            assert native['continuation'][key] == api['continuation'][key], key
        assert native['restored_storage_sha256'] == api['restored_storage_sha256']
        assert load('native-before-database.json')['state'] == load('api-before-database.json')['state']
        assert load('native-after-database.json')['state'] == load('api-after-database.json')['state']
        assert load('native-before-filesystem.json')['state_sha256'] == load('api-before-filesystem.json')['state_sha256']
        assert canonical_files(load('native-after-filesystem-inventory.json')) == canonical_files(load('api-after-filesystem-inventory.json'))
        warm = load('warm-browser.json')['continuation']
        # Independent creations generate UUIDs; compare all other fields and
        # exact body, retaining IDs in the raw reports rather than overwriting.
        for key in ['before', 'after', 'actor']:
            assert {k: v for k, v in warm[key].items() if k != 'id'} == {k: v for k, v in native['continuation'][key].items() if k != 'id'}
        assert warm['request']['body'] == native['continuation']['request']['body']
        producer = load('producer-browser.json')['producer']['target']
        assert {k: v for k, v in producer.items() if k != 'id'} == {k: v for k, v in warm['before'].items() if k != 'id'}
        result.update(status='ordinary_qualification_passed', restored_pair_state_equal=True,
                      warm_semantics_equal=True, independent_creation_full_state_equivalence_claimed=False)
    except Exception as error:
        result.update(failed_stage=stage, error_type=type(error).__name__, error_message_sha256=hashlib.sha256(str(error).encode()).hexdigest())
        (private / 'qualification-error.txt').write_text(repr(error))
        raise RuntimeError('Qualification failed at ' + stage) from None
    finally:
        signal.alarm(0)
        result['elapsed_seconds'] = time.monotonic() - started
        (out / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
        command(['docker', 'logs', APP], 'final-app-log', required=False)
        command(['docker', 'logs', PG], 'final-database-log', required=False)
        command(['docker', 'rm', '-f', '-v', 'study-viseron-browser', APP, PG], 'cleanup', required=False)
        command(['docker', 'volume', 'rm', CONFIG], 'cleanup-volume', required=False)


if __name__ == '__main__':
    main()
