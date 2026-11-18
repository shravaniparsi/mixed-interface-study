#!/usr/bin/env python3
"""Registered ordinary qualification; original app only, no altered inputs."""
import argparse
import hashlib
import json
import os
import secrets
import signal
import subprocess
import time
from pathlib import Path

PG_IMAGE = 'postgres@sha256:99d1a998c76487d3abb48b141505bda5dcf8089c0c4cd7be40f75de314fa32f0'
BROWSER_IMAGE = 'mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac'
PG = 'study-mathesar-postgres'
APP = 'study-mathesar'


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
    fixture = {'admin_password': 'Study-A!' + secrets.token_hex(16),
               'target_password': 'Study-T!' + secrets.token_hex(16)}
    (private / 'fixture.json').write_text(json.dumps(fixture))
    secret_key, db_password = secrets.token_hex(32), secrets.token_hex(24)
    secret_values = [*fixture.values(), secret_key, db_password]
    app_env = {'POSTGRES_DB': 'study', 'POSTGRES_USER': 'study',
               'POSTGRES_PASSWORD': db_password, 'POSTGRES_HOST': '127.0.0.1',
               'POSTGRES_PORT': '5432', 'POSTGRES_SSLMODE': 'disable',
               'SECRET_KEY': secret_key, 'PER_USER_DATABASES_ENABLED': 'false',
               'ALLOWED_HOSTS': '127.0.0.1,localhost'}
    env_file = private / 'application.env'
    env_file.write_text(''.join(k + '=' + v + '\n' for k, v in app_env.items()))
    pg_env = private / 'postgres.env'
    pg_env.write_text('POSTGRES_USER=study\nPOSTGRES_DB=study\nPOSTGRES_PASSWORD=' + db_password + '\n')
    result = {'status': 'qualification_failed', 'phases': [], 'scientific_cases': 0}
    started = time.monotonic()
    stage = 'initialization'

    def clean(raw):
        value = raw.decode(errors='replace')
        for secret in secret_values:
            value = value.replace(secret, '<private>')
        return value

    def command(argv, label, timeout=120, required=True):
        proc = subprocess.run(argv, capture_output=True, timeout=timeout)
        (out / (label + '.log')).write_text(clean(proc.stdout) + clean(proc.stderr))
        (out / (label + '-exit.json')).write_text(json.dumps({'exit_code': proc.returncode}) + '\n')
        if required and proc.returncode:
            raise RuntimeError(label + ' failed')
        return proc

    def database_ready():
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            p = subprocess.run(['docker', 'exec', PG, 'pg_isready', '-U', 'study', '-d', 'study'], capture_output=True, timeout=5)
            if p.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError('Database readiness deadline')

    def app_ready(label):
        # Run inside the original application container's isolated namespace.
        code = "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/complete_installation/',timeout=2); assert r.status==200"
        deadline = time.monotonic() + 45
        attempts = []
        while time.monotonic() < deadline:
            p = subprocess.run(['docker', 'exec', APP, 'python', '-c', code], capture_output=True, timeout=5)
            attempts.append(p.returncode)
            if p.returncode == 0:
                (out / (label + '-readiness.json')).write_text(json.dumps(attempts))
                return
            time.sleep(1)
        (out / (label + '-readiness.json')).write_text(json.dumps(attempts))
        raise RuntimeError('Application readiness deadline')

    def fresh(label):
        command(['docker', 'rm', '-f', '-v', APP, PG], label + '-remove-old', required=False)
        command(['docker', 'run', '-d', '--name', PG, '--network', 'none', '--env-file', str(pg_env), PG_IMAGE], label + '-postgres')
        database_ready()
        command(['docker', 'run', '--rm', '--network', 'container:' + PG,
                 '--env-file', str(env_file), 'study-mathesar:qualification-v1',
                 'python', '-m', 'mathesar.install'], label + '-migrate', timeout=90)
        command(['docker', 'run', '-d', '--name', APP, '--network', 'container:' + PG,
                 '--env-file', str(env_file), 'study-mathesar:qualification-v1'], label + '-application')
        app_ready(label)

    def settings(label):
        code = """import django,json;django.setup()
from django.conf import settings
from mathesar.analytics import is_analytics_enabled
from mathesar.models import InstallationID
result={'test':settings.TEST,'per_user_databases':settings.PER_USER_DATABASES_ENABLED,'analytics_enabled':is_analytics_enabled(),'installation_ids':InstallationID.objects.count()}
print(json.dumps(result))
assert result=={'test':False,'per_user_databases':False,'analytics_enabled':False,'installation_ids':0}
"""
        command(['docker', 'exec', APP, 'python', '-c', code], label + '-settings')

    def browser(phase):
        command(['docker', 'run', '--name', 'study-mathesar-browser', '--network', 'container:' + PG,
                 '--user', str(os.getuid()) + ':' + str(os.getgid()),
                 '--shm-size=1g', '-v', args.node + ':/study/node:ro',
                 '-v', str(args.tools.resolve()) + ':/study/tools:ro',
                 '-v', str(root) + ':' + str(root) + ':ro', '-v', str(out) + ':' + str(out),
                 '-e', 'PLAYWRIGHT_MODULE_PATH=/study/tools/node_modules/playwright', BROWSER_IMAGE,
                 '/study/node', str(root / 'scripts/extension/run_mathesar_browser_phase_v1.mjs'),
                 '--phase', phase, '--out', str(out), '--private', str(private)], phase + '-browser-process', timeout=100)
        command(['docker', 'rm', 'study-mathesar-browser'], phase + '-browser-remove')
        row = json.loads((out / (phase + '-browser.json')).read_text())
        assert row['status'] == 'ordinary_phase_passed'
        result['phases'].append(phase)
        storage = private / 'seed-storage.json'
        if storage.exists():
            secret_values.extend(c['value'] for c in json.loads(storage.read_text())['cookies'])
        settings(phase)

    def stop(label):
        command(['docker', 'stop', '--time', '20', APP], label + '-stop')
        command(['docker', 'logs', APP], label + '-application-log')

    def checkpoint(action, label):
        command(['python3', str(root / 'scripts/extension/mathesar_postgres_checkpoint_v1.py'),
                 action, '--private', str(private / 'checkpoint'),
                 '--report', str(out / (label + '-state.json'))], label + '-checkpoint', timeout=90)

    def fail_timeout(*_):
        raise TimeoutError('600-second runtime envelope')

    signal.signal(signal.SIGALRM, fail_timeout)
    signal.alarm(600)
    try:
        for phase in ['producer', 'warm', 'seed']:
            stage = phase
            fresh(phase)
            browser(phase)
            stop(phase)
            checkpoint('capture' if phase == 'seed' else 'inspect', phase)
        for phase in ['native', 'api']:
            stage = phase
            checkpoint('restore', phase + '-before')
            command(['docker', 'start', APP], phase + '-restart')
            app_ready(phase)
            browser(phase)
            stop(phase)
            checkpoint('inspect', phase + '-after')
        stage = 'comparison'
        load = lambda p: json.loads((out / p).read_text())
        native, api = (load(p + '-browser.json') for p in ['native', 'api'])
        for key in ['actor', 'before', 'after', 'request']:
            assert native['continuation'][key] == api['continuation'][key], key
        assert native['restored_storage_sha256'] == api['restored_storage_sha256']
        assert load('native-before-state.json')['state'] == load('api-before-state.json')['state']
        assert load('native-after-state.json')['state'] == load('api-after-state.json')['state']
        warm = load('warm-browser.json')['continuation']
        # Fresh DB credentials/timestamps differ and are not equated. The complete
        # API user representations and ordinary request/outcome still must match.
        for key in ['before', 'after', 'request']:
            assert warm[key] == native['continuation'][key], 'warm ' + key
        assert load('producer-browser.json')['producer']['target'] == warm['before']
        result.update(status='ordinary_qualification_passed', restored_full_state_equal=True,
                      warm_semantic_control_equal=True, fresh_full_state_equivalence_claimed=False)
    except Exception as error:
        result.update(failed_stage=stage, error_type=type(error).__name__, error=clean(str(error).encode()))
        raise
    finally:
        signal.alarm(0)
        result['elapsed_seconds'] = time.monotonic() - started
        (out / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
        command(['docker', 'logs', PG], 'final-postgres-log', required=False)
        command(['docker', 'logs', APP], 'final-application-log', required=False)
        command(['docker', 'rm', '-f', '-v', 'study-mathesar-browser', APP, PG], 'cleanup', required=False)


if __name__ == '__main__':
    main()
