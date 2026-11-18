#!/usr/bin/env python3
"""CI-only isolated fixture provisioning; no study record or browser action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
from seatsurfing_postgres_checkpoint_v2 import PG, APP, BROWSER, PG_IMAGE_ID, BROWSER_IMAGE_ID

ROOT = Path(__file__).resolve().parents[2]
REVISION = '9953f452324bab6fb8f7106dd8965cc401aa456c'
LABEL = 'org.mixed-interface.study=seatsurfing-qualification-v1'
VOLUME = 'study-seatsurfing-postgres-data'
BROWSER_REF = 'mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac'
LOCK = ROOT / 'results/development-admin-control-v2-api-ci-44105779135/node-tools-package-lock.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def app_environment(database_password, admin_password, crypt_key):
    assert re.fullmatch(r'[a-f0-9]{48}', database_password)
    assert re.fullmatch(r'[a-f0-9]{48}', admin_password)
    assert re.fullmatch(r'[a-f0-9]{32}', crypt_key)
    return {
        'POSTGRES_URL': f'postgres://seatsurfing:{database_password}@127.0.0.1:5432/seatsurfing?sslmode=disable',
        'CRYPT_KEY': crypt_key,
        'JWT_PRIVATE_KEY': '/run/study-private.pem', 'JWT_PUBLIC_KEY': '/run/study-public.pem',
        'INIT_ORG_NAME': 'Study organization', 'INIT_ORG_USER': 'admin', 'INIT_ORG_PASS': admin_password,
        'INIT_ORG_LANGUAGE': 'en', 'INIT_ORG_DOMAIN': 'localhost',
        'PUBLIC_LISTEN_ADDR': '127.0.0.1:8080', 'PUBLIC_SCHEME': 'http', 'PUBLIC_PORT': '8080',
        'STATIC_UI_PATH': '/app/ui', 'CACHE_TYPE': 'default', 'DEV': '0',
        'MOCK_SENDMAIL': '1', 'PLUGINS_CONFIG': '', 'FEATURE_FLAGS': '',
        'DISABLE_VERSION_CHECK': '1', 'DISABLE_ANONYMOUS_USAGE_STATS': '1',
        'DISABLE_PASSWORD_LOGIN': '0', 'RATE_LIMIT': '250', 'RATE_LIMIT_PERIOD': '1-M',
    }


def verify_runtime_layout(app, postgres, image_id, private_key, public_key):
    for item, expected in [(app, image_id), (postgres, PG_IMAGE_ID)]:
        assert item['Image'] == expected
        assert item['Config']['Labels']['org.mixed-interface.study'] == 'seatsurfing-qualification-v1'
        assert not item['HostConfig'].get('Privileged')
        assert not item['HostConfig'].get('PortBindings')
        assert not item['HostConfig'].get('PublishAllPorts')
        assert item['HostConfig']['RestartPolicy']['Name'] in ('', 'no')
    assert postgres['HostConfig']['NetworkMode'] == 'none'
    assert app['HostConfig']['NetworkMode'] in ('container:' + PG, 'container:' + postgres['Id'])
    assert app['HostConfig']['ReadonlyRootfs'] is True
    assert not app['HostConfig'].get('Tmpfs')
    assert app['Config']['User'] == '65532:65532'
    mounts = app['Mounts']
    assert len(mounts) == 2
    expected = {'/run/study-private.pem': str(private_key.resolve()), '/run/study-public.pem': str(public_key.resolve())}
    for mount in mounts:
        assert mount['Type'] == 'bind' and mount['RW'] is False
        assert expected[mount['Destination']] == mount['Source']
    volume, = postgres['Mounts']
    assert volume['Type'] == 'volume' and volume['Name'] == VOLUME
    assert volume['Destination'] == '/var/lib/postgresql' and volume['RW'] is True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    assert os.environ.get('RUNNER_OS') == 'Linux'
    registration = json.loads(args.registration.read_text())
    assert registration['status'] == 'qualification_registered'
    assert registration['application_revision'] == REVISION and registration['max_job_minutes'] == 30
    assert registration['script_sha256'][str(Path(__file__).relative_to(ROOT))] == digest(__file__)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == os.environ.get('GITHUB_SHA')
    assert subprocess.check_output(['git', 'show', f'{head}:{args.registration.resolve().relative_to(ROOT)}'], cwd=ROOT) == args.registration.read_bytes()
    build = json.loads(args.build_report.read_text())
    assert build['study_commit'] == head and build['application_revision'] == REVISION
    assert build['status'] == 'source_build_verified_and_inventory_complete'
    prepared = ROOT / 'results/catalog-seatsurfing-source-build-preparation-v4/manifest.json'
    assert build['source_preparation_sha256'] == digest(prepared)
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', build['application_image_id'])
    recipe = json.loads(prepared.read_text())
    os.umask(0o077)
    private = args.private.resolve()
    private.mkdir(parents=True, mode=0o700, exist_ok=False)
    evidence = private / 'provision-evidence'
    evidence.mkdir(mode=0o700)
    report = {'status': 'in_progress', 'study_commit': head, 'commands': [], 'scientific_inputs_executed': 0,
              'build_report_sha256': digest(args.build_report), 'browser_started': False}
    tools_owned = False
    deadline = time.monotonic() + 300

    def save():
        (private / 'provision-report.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, command, limit=30, check=True):
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'Shared provisioning deadline exhausted'
        path = evidence / (name + '.log')
        assert not path.exists(), 'Repeated provisioning command'
        row = {'name': name, 'command': command, 'timeout_seconds': min(limit, remaining)}
        report['commands'].append(row); save()
        try:
            with path.open('xb') as stream:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=row['timeout_seconds'])
            row['exit_code'] = result.returncode
            if check and result.returncode:
                raise RuntimeError(name + ' failed; no automatic retry')
            return result.returncode, path
        finally:
            if path.exists(): row['sha256'] = digest(path)
            save()

    def inspect(name, target):
        _, path = run(name, ['docker', 'inspect', target])
        item, = json.loads(path.read_text())
        return item

    try:
        # Never remove/reuse pre-existing containers or volumes.
        for index, name in enumerate([PG, APP, BROWSER, 'study-seatsurfing-tools-install']):
            code, _ = run('absent-container-' + str(index), ['docker', 'container', 'inspect', name], check=False)
            assert code != 0, 'Existing named container; no overwrite'
        code, _ = run('absent-volume', ['docker', 'volume', 'inspect', VOLUME], check=False)
        assert code != 0, 'Existing database volume; no overwrite'
        pg_ref = 'docker.io/' + recipe['bases']['library/postgres']['reference']
        for name, reference, expected in [('postgres', pg_ref, PG_IMAGE_ID), ('browser', BROWSER_REF, BROWSER_IMAGE_ID)]:
            run(name + '-pull', ['docker', 'pull', '--platform', 'linux/amd64', reference], 180)
            info = inspect(name + '-image', reference)
            assert info['Id'] == expected and info['Architecture'] == 'amd64' and info['Os'] == 'linux'
        tools = private / 'node-tools'
        tools.mkdir()
        lock = json.loads(LOCK.read_text())
        shutil.copyfile(LOCK, tools / 'package-lock.json')
        (tools / 'package.json').write_text(json.dumps(lock['packages']['']))
        tools_owned = True
        run('tools-install', ['docker', 'run', '--rm', '--name', 'study-seatsurfing-tools-install',
            '--label', LABEL, '--platform', 'linux/amd64', '-e', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1',
            '-v', f'{tools}:/tools', '-w', '/tools', '--entrypoint', 'npm', BROWSER_IMAGE_ID,
            'ci', '--ignore-scripts', '--no-audit', '--no-fund'], 90)
        assert digest(tools / 'package-lock.json') == digest(LOCK)
        assert json.loads((tools / 'node_modules/playwright/package.json').read_text())['version'] == '1.62.1'
        report['tools_lock_sha256'] = digest(LOCK)
        keys = private / 'keys'; keys.mkdir(mode=0o700)
        private_key, public_key = keys / 'private.pem', keys / 'public.pem'
        run('private-key', ['openssl', 'genrsa', '-traditional', '-out', str(private_key), '2048'])
        run('public-key', ['openssl', 'rsa', '-in', str(private_key), '-pubout', '-out', str(public_key)])
        assert private_key.read_text().startswith('-----BEGIN RSA PRIVATE KEY-----')
        assert public_key.read_text().startswith('-----BEGIN PUBLIC KEY-----')
        # Readable through individual read-only mounts by app UID 65532; host
        # keys directory remains 0700 and is never mounted as a directory.
        private_key.chmod(0o644); public_key.chmod(0o644)
        database_password, admin_password, crypt_key = secrets.token_hex(24), secrets.token_hex(24), secrets.token_hex(16)
        env = app_environment(database_password, admin_password, crypt_key)
        (private / 'app.env').write_text(''.join(k + '=' + v + '\n' for k, v in env.items()))
        (private / 'postgres.env').write_text(f'POSTGRES_USER=seatsurfing\nPOSTGRES_DB=seatsurfing\nPOSTGRES_PASSWORD={database_password}\n')
        run('volume-create', ['docker', 'volume', 'create', '--label', LABEL, VOLUME])
        run('postgres-start', ['docker', 'run', '-d', '--name', PG, '--label', LABEL, '--network', 'none',
            '--restart', 'no', '--memory', '1g', '--cpus', '1', '--env-file', str(private / 'postgres.env'),
            '-v', VOLUME + ':/var/lib/postgresql', PG_IMAGE_ID])
        # Read-only readiness probes are not repeated initialization commands.
        for attempt in range(30):
            code, _ = run('postgres-ready-' + str(attempt), ['docker', 'exec', PG, 'pg_isready', '-h', '127.0.0.1', '-U', 'seatsurfing', '-d', 'seatsurfing'], 10, check=False)
            if code == 0: break
            state = inspect('postgres-state-' + str(attempt), PG)['State']
            assert state['Running'], 'PostgreSQL stopped during initialization'
            time.sleep(1)
        else: raise TimeoutError('PostgreSQL readiness not established')
        run('application-create', ['docker', 'create', '--name', APP, '--label', LABEL,
            '--network', 'container:' + PG, '--restart', 'no', '--read-only', '--memory', '2g', '--cpus', '2',
            '--env-file', str(private / 'app.env'),
            '-v', f'{private_key}:/run/study-private.pem:ro', '-v', f'{public_key}:/run/study-public.pem:ro', build['application_image_id']])
        app, postgres = inspect('application-before-start', APP), inspect('postgres-before-application', PG)
        verify_runtime_layout(app, postgres, build['application_image_id'], private_key, public_key)
        run('application-start', ['docker', 'start', APP])
        for attempt in range(90):
            app = inspect('application-health-' + str(attempt), APP)
            assert app['State']['Running'], 'Application exited during startup'
            health = app['State'].get('Health', {}).get('Status')
            if health == 'healthy': break
            assert health != 'unhealthy', 'Original application health check failed'
            time.sleep(1)
        else: raise TimeoutError('Original application health not established')
        _, path = run('organization-readback', ['docker', 'exec', PG, 'psql', '-U', 'seatsurfing', '-d', 'seatsurfing',
            '--no-psqlrc', '--no-align', '--tuples-only', '--set', 'ON_ERROR_STOP=1', '--command', 'SELECT id FROM organizations ORDER BY id'])
        ids = path.read_text().splitlines()
        assert len(ids) == 1 and re.fullmatch(r'[0-9a-f-]{36}', ids[0])
        (private / 'native-login-config.json').write_text(json.dumps({'origin': 'http://127.0.0.1:8080', 'mode': 'native_login',
            'login': {'email': 'admin@seatsurfing.local', 'password': admin_password, 'organizationId': ids[0]}}))
        _, log = run('application-startup-log', ['docker', 'logs', APP])
        assert 'Generating a temporary random private/public key pair' not in log.read_text()
        verify_runtime_layout(inspect('application-ready', APP), inspect('postgres-ready-final', PG), build['application_image_id'], private_key, public_key)
        report.update(status='isolated_fixture_ready_browser_and_actor_unqualified', application_container_id=app['Id'], database_container_id=postgres['Id'],
            private_key_sha256=digest(private_key), public_key_sha256=digest(public_key),
            node_tools=str(tools), native_login_config=str(private / 'native-login-config.json'))
        save()
    except Exception as error:
        report.update(status='provision_failed_no_retry', error_type=type(error).__name__, error=str(error))
        save()
        raise
    finally:
        # The parent owns evidence retention and teardown of app/database/volume.
        if tools_owned:
            subprocess.run(['docker', 'rm', '-f', 'study-seatsurfing-tools-install'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)


if __name__ == '__main__':
    main()
