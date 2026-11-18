#!/usr/bin/env python3
"""Source build for the future registered qualification job, never a local probe.

This file does not dispatch a job. The complete qualification registration must
exist and bind this script before execution; preparation alone is insufficient.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
REVISION = '20016b9d91d49c9133f1b4d26ab5a289c72ec1db'
REPOSITORY = 'nginxproxymanager/nginx-proxy-manager'
BASE = 'nginxproxymanager/nginx-full@sha256:e8971bb81500750b867e9800c0419c6d743d5c233f6781d65d03e8bad49da7eb'
CA = 'nginxproxymanager/testca@sha256:872386a37de28a278782b9fa5b997d932bdb7b0b4b8974d54ba50ba92b3de767'
IMAGE = 'study-nginx-original:qualification-v1'
MAX_BUILD_SECONDS = 1080


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def verify_checkout(checkout, revision, tree_entries, rows):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(checkout), *args], timeout=20, text=True).strip()
    assert git('rev-parse', 'HEAD') == revision, 'Checkout revision mismatch'
    expected_tree = {r['path']: (r['mode'], r['type'], r['sha']) for r in tree_entries}
    assert len(expected_tree) == len(tree_entries), 'Duplicate retained tree path'
    raw_tree = subprocess.check_output(['git', '-C', str(checkout), 'ls-tree', '-r', '-t', '-z', 'HEAD'], timeout=20)
    actual_tree = {}
    for record in raw_tree.split(b'\0'):
        if not record:
            continue
        metadata, path = record.decode('utf8').split('\t', 1)
        mode, kind, sha = metadata.split(' ')
        actual_tree[path] = (mode, kind, sha)
    assert actual_tree == expected_tree, 'Checkout recursive tree differs from retained metadata'
    verified = []
    seen = set()
    for row in rows:
        assert row['path'] not in seen, 'Duplicate acquired source path'
        seen.add(row['path'])
        path = checkout / row['path']
        assert path.resolve().is_relative_to(checkout.resolve()), 'Source escapes checkout'
        assert path.is_file() and not path.is_symlink(), 'Acquired source must be a regular file'
        assert path.stat().st_size == row['bytes']
        assert digest(path) == row['sha256'], f"Source mismatch: {row['path']}"
        verified.append({'path': row['path'], 'sha256': row['sha256'], 'bytes': row['bytes']})
    return verified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Hosted qualification only'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    assert os.environ.get('RUNNER_OS') == 'Linux'
    registration = json.loads(args.registration.read_text())
    assert registration['status'] == 'qualification_registered'
    assert registration['application_revision'] == REVISION
    assert registration['max_job_minutes'] == 30
    assert registration['script_sha256'][str(Path(__file__).relative_to(ROOT))] == digest(__file__)
    # Verify the registration is part of this checkout, avoiding a self-referential
    # commit field inside a versioned registration document.
    study_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert study_commit == os.environ.get('GITHUB_SHA')
    registration_path = args.registration.resolve().relative_to(ROOT)
    published = subprocess.check_output(['git', 'show', f'{study_commit}:{registration_path}'], cwd=ROOT)
    assert published == args.registration.read_bytes(), 'Registration is not the published version'
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--'], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, timeout=20)
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    checkout = workspace / 'source'
    evidence = workspace / 'build-evidence'
    evidence.mkdir(mode=0o700)
    deadline = time.monotonic() + MAX_BUILD_SECONDS
    report = {'status': 'in_progress', 'application_revision': REVISION, 'study_commit': study_commit, 'commands': [],
              'application_started': False, 'scientific_inputs_executed': 0}

    def save():
        (evidence / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, command, limit, cwd=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Shared build deadline exhausted')
        log = evidence / (name + '.log')
        row = {'name': name, 'command': command, 'timeout_seconds': min(limit, remaining)}
        report['commands'].append(row)
        start = time.monotonic()
        save()
        try:
            with log.open('wb') as output:
                result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                        timeout=row['timeout_seconds'], check=False)
            row['exit_code'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'{name} failed; retain original log, no retry')
        finally:
            row['elapsed_seconds'] = time.monotonic() - start
            if log.exists():
                row['log_sha256'] = digest(log)
                row['log_bytes'] = log.stat().st_size
            save()
        return log

    try:
        prepared = ROOT / 'results/catalog-nginx-source-build-preparation-v1'
        recipe = json.loads((prepared / 'manifest.json').read_text())
        assert digest(prepared / 'Dockerfile') == recipe['derived_dockerfile_sha256']
        assert digest(prepared / 'install-s6') == recipe['checked_installer_sha256']
        tree_response = json.loads((ROOT / 'results/catalog-application-metadata-v1/06/3.json').read_text())
        assert tree_response['truncated'] is False
        tree = tree_response['tree']
        rows = []
        for wave in range(1, 25):
            collection = json.loads((ROOT / f'results/catalog-source-wave{wave}-v1/collection.json').read_text())
            rows += [r for r in collection['rows'] if r['repository'] == REPOSITORY and r['status'] == 'collected_verified']
        assert len(rows) == 96
        run('git-init', ['git', 'init', str(checkout)], 20)
        run('git-fetch', ['git', '-C', str(checkout), 'fetch', '--depth=1', '--no-tags',
                         'https://github.com/nginxproxymanager/nginx-proxy-manager.git', REVISION], 120)
        run('git-checkout', ['git', '-C', str(checkout), 'checkout', '--detach', REVISION], 30)
        report['verified_source'] = verify_checkout(checkout, REVISION, tree, rows)
        report['source_tree'] = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
        report['retained_tree_response_sha'] = tree_response['sha']
        report['verified_tree_entries'] = len(tree)
        assert not subprocess.check_output(['git', '-C', str(checkout), 'diff', 'HEAD', '--name-only']).strip()
        for name, image, config in [
            ('base', BASE, 'sha256:f76b853e6a5b931380aa27cd0f8898fce6ab0d2a45feb753d56d63a9ee96b3b6'),
            ('testca', CA, 'sha256:d43c584544a645b7f65abb833f05f0463a0abb9d8884b7d21de2b17d2e70c967'),
        ]:
            run(name + '-pull', ['docker', 'pull', '--platform', 'linux/amd64', image], 180)
            info = run(name + '-inspect', ['docker', 'image', 'inspect', image], 15)
            item, = json.loads(info.read_text())
            assert item['Id'] == config and item['Architecture'] == 'amd64' and item['Os'] == 'linux'
        uid, gid = os.getuid(), os.getgid()
        frontend_command = (
            'node --version && yarn --version && yarn install --frozen-lockfile && '
            'yarn locale-compile && yarn build && '
            f'chown -R {uid}:{gid} /app/frontend'
        )
        run('frontend-build', ['docker', 'run', '--rm', '--name', 'study-nginx-builder',
                              '--platform', 'linux/amd64', '-e', 'CI=true',
                              '-e', 'NODE_OPTIONS=--openssl-legacy-provider',
                              '-v', f'{checkout}/frontend:/app/frontend', '-w', '/app/frontend',
                              BASE, 'sh', '-c', frontend_command], 420)
        # Generated locale/dist artifacts are expected; acquired source and locks
        # must still agree byte-for-byte with the frozen revision.
        verify_checkout(checkout, REVISION, tree, rows)
        assert not subprocess.check_output(['git', '-C', str(checkout), 'diff', 'HEAD', '--name-only']).strip(), 'Build modified tracked original source'
        assert (checkout / 'frontend/dist/index.html').is_file()
        run('frontend-installed-inventory', ['docker', 'run', '--rm', '--name', 'study-nginx-frontend-inventory', '--network', 'none',
                '--entrypoint', 'node', '-v', f'{ROOT}:{ROOT}:ro',
                '-v', f'{checkout}/frontend:/frontend:ro', BASE,
                str(ROOT / 'scripts/extension/inventory_nginx_build_v1.mjs'), 'frontend', '/frontend'], 120)
        run('application-build', ['docker', 'build', '--platform', 'linux/amd64',
                                 '--file', str(prepared / 'Dockerfile'), '--tag', IMAGE,
                                 '--build-arg', 'BUILD_VERSION=2.0.0',
                                 '--build-arg', f'BUILD_COMMIT={REVISION}',
                                 '--build-arg', 'BUILD_DATE=2026-11-18T00:00:00Z', str(checkout)], 480)
        info = run('application-inspect', ['docker', 'image', 'inspect', IMAGE], 15)
        application, = json.loads(info.read_text())
        assert application['Architecture'] == 'amd64' and application['Os'] == 'linux'
        assert f'NPM_BUILD_COMMIT={REVISION}' in application['Config']['Env']
        report['image_id'] = application['Id']
        run('installed-package-identities', ['docker', 'run', '--rm', '--name', 'study-nginx-package-inventory', '--network', 'none',
                                           '--entrypoint', 'sh', IMAGE, '-c',
                                           'node --version && yarn --version && dpkg-query -W'], 30)
        # Full installed app/artifact inventory is an independent gate before any
        # startup. The inspector does not import backend code or run entrypoint.
        run('installed-application-inventory', ['docker', 'run', '--rm', '--name', 'study-nginx-backend-inventory', '--network', 'none',
                '--entrypoint', 'node', '-v', f'{ROOT}:{ROOT}:ro', IMAGE,
                str(ROOT / 'scripts/extension/inventory_nginx_build_v1.mjs')], 120)
        report['status'] = 'source_build_prepared_runtime_unqualified'
        save()
    except Exception as error:
        report.update(status='build_failed_no_retry', error_type=type(error).__name__, error=str(error))
        save()
        raise
    finally:
        # Only this dedicated ephemeral builder. The parent qualification workflow
        # owns all further cleanup, the 30-minute job bound and result retention.
        subprocess.run(['docker', 'rm', '-f', 'study-nginx-builder', 'study-nginx-frontend-inventory',
                        'study-nginx-package-inventory', 'study-nginx-backend-inventory'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)


if __name__ == '__main__':
    main()
