#!/usr/bin/env python3
"""Registered CI-only original SeatSurfing build; starts no application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from seatsurfing_tree_identity_v2 import root_tree_sha

ROOT = Path(__file__).resolve().parents[2]
REVISION = '9953f452324bab6fb8f7106dd8965cc401aa456c'
IMAGE = 'study-seatsurfing-original:qualification-v1'
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


def schema_dockerfile(final_base):
    assert re.fullmatch(r'gcr.io/distroless/base-debian13@sha256:[0-9a-f]{64}', final_base)
    return ("FROM study-seatsurfing-server-builder:qualification-v1 AS schema-builder\n"
            "WORKDIR /go/src/app\n"
            "COPY main.go /study-schema/main.go\n"
            "COPY original-go.mod original-go.sum /study-schema/\n"
            "RUN --network=none --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build "
            "CGO_ENABLED=1 go build -mod=readonly -o /study-schema/probe /study-schema/main.go "
            "&& cmp go.mod /study-schema/original-go.mod && cmp go.sum /study-schema/original-go.sum\n"
            f"FROM {final_base}\n"
            "COPY --from=schema-builder /study-schema/probe /study-schema/probe\n"
            "USER 65532:65532\n"
            'ENTRYPOINT ["/study-schema/probe"]\n'
            "CMD []\n")


def inventory(directory):
    rows = []
    total = 0
    for path in sorted(directory.rglob('*')):
        assert len(rows) < 50000, 'Application inventory entry bound'
        row = {'path': str(path.relative_to(directory)), 'mode': path.lstat().st_mode & 0o7777}
        if path.is_symlink():
            rows.append({**row, 'kind': 'symlink', 'target': os.readlink(path)})
        elif path.is_file():
            total += path.stat().st_size
            assert total <= 1024 ** 3 and len(rows) < 50000, 'Application inventory bound'
            rows.append({**row, 'kind': 'file', 'bytes': path.stat().st_size, 'sha256': digest(path)})
        else:
            assert path.is_dir(), 'Unsupported application file kind'
    assert rows
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    assert os.environ.get('RUNNER_OS') == 'Linux'
    registration = json.loads(args.registration.read_text())
    assert registration['status'] == 'qualification_registered'
    assert registration['application_revision'] == REVISION
    assert registration['max_job_minutes'] == 30
    for path in [Path(__file__), ROOT / 'scripts/extension/inventory_seatsurfing_ui_build_v1.mjs', ROOT / 'scripts/extension/seatsurfing_original_schema_v1.go']:
        assert registration['script_sha256'][str(path.relative_to(ROOT))] == digest(path)
    study_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert study_commit == os.environ.get('GITHUB_SHA')
    published = subprocess.check_output(['git', 'show', f'{study_commit}:{args.registration.resolve().relative_to(ROOT)}'], cwd=ROOT)
    assert published == args.registration.read_bytes()
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, timeout=20)
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False, mode=0o700)
    checkout, evidence = workspace / 'source', workspace / 'build-evidence'
    evidence.mkdir(mode=0o700)
    deadline = time.monotonic() + MAX_BUILD_SECONDS
    report = {'status': 'in_progress', 'application_revision': REVISION, 'study_commit': study_commit,
              'commands': [], 'application_started': False, 'scientific_inputs_executed': 0}
    containers = []

    def save():
        (evidence / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, command, limit):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Shared build deadline exhausted')
        log = evidence / (name + '.log')
        row = {'name': name, 'command': command, 'timeout_seconds': min(limit, remaining)}
        assert not log.exists(), 'No repeated build command'
        report['commands'].append(row)
        start = time.monotonic()
        save()
        try:
            with log.open('xb') as output:
                result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT,
                                        timeout=row['timeout_seconds'], check=False)
            row['exit_code'] = result.returncode
            if result.returncode:
                raise RuntimeError(f'{name} failed; retain evidence, no retry')
        finally:
            row['elapsed_seconds'] = time.monotonic() - start
            if log.exists():
                row.update(log_sha256=digest(log), log_bytes=log.stat().st_size)
            save()
        return log

    def inspect(name, image, expected=None):
        item, = json.loads(run(name, ['docker', 'image', 'inspect', image], 15).read_text())
        assert item['Architecture'] == 'amd64' and item['Os'] == 'linux'
        assert re.fullmatch(r'sha256:[0-9a-f]{64}', item['Id'])
        if expected:
            assert item['Id'] == expected
        return item

    def offline_run(name, image, entrypoint, arguments, limit, mounts=()):
        container = 'study-seatsurfing-' + name
        containers.append(container)
        command = ['docker', 'run', '--rm', '--name', container, '--network', 'none', '--read-only', '--entrypoint', entrypoint]
        for mount in mounts:
            command.extend(['-v', mount])
        return run(name, command + [image, *arguments], limit)

    def stopped_copy(name, image, source, destination):
        containers.append(name)
        run(name + '-create', ['docker', 'create', '--name', name, '--network', 'none', image], 15)
        run(name + '-copy', ['docker', 'cp', name + ':' + source, str(destination)], 60)

    try:
        prepared = ROOT / 'results/catalog-seatsurfing-source-build-preparation-v4'
        recipe = json.loads((prepared / 'manifest.json').read_text())
        assert recipe['application_revision'] == REVISION
        assert digest(prepared / 'Dockerfile') == recipe['generated_dockerfile_sha256']
        report['source_preparation_sha256'] = digest(prepared / 'manifest.json')
        tree_response = json.loads((ROOT / 'results/catalog-application-metadata-v1/09/3.json').read_text())
        assert tree_response['truncated'] is False
        assert all(row['type'] != 'commit' for row in tree_response['tree']), 'Submodules require separately registered identities'
        rows = recipe['source_files_to_verify_at_runtime']
        assert len(rows) == 56
        run('git-init', ['git', 'init', str(checkout)], 20)
        run('git-fetch', ['git', '-C', str(checkout), 'fetch', '--depth=1', '--no-tags',
                         'https://github.com/seatsurfing/seatsurfing.git', REVISION], 120)
        run('git-checkout', ['git', '-C', str(checkout), 'checkout', '--detach', REVISION], 30)
        report['verified_source'] = verify_checkout(checkout, REVISION, tree_response['tree'], rows)
        report['metadata_tree_locator'] = tree_response['sha']
        report['source_tree'] = root_tree_sha(tree_response['tree'])
        assert subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == report['source_tree']
        version = (checkout / 'version.txt').read_text().strip()
        assert re.fullmatch(r'[0-9A-Za-z.+_-]{1,80}', version)
        report['ci_version'] = version
        assert not subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=all']).strip(), 'Checkout is not clean before build'
        report['original_lock_hashes'] = {p: digest(checkout / p) for p in ['ui/package-lock.json', 'server/go.mod', 'server/go.sum', 'healthcheck/go.mod']}
        report['base_images'] = {}
        for name in ['tonistiigi/xx', 'library/node', 'library/golang']:
            base = recipe['bases'][name]
            image = 'docker.io/' + base['reference']
            label = name.replace('/', '-')
            run(label + '-pull', ['docker', 'pull', '--platform', 'linux/amd64', image], 180)
            report['base_images'][name] = inspect(label + '-inspect', image, base['config_digest'])['Id']
        final_base = recipe['final_base_original_reference']
        run('final-base-pull', ['docker', 'pull', '--platform', 'linux/amd64', final_base], 180)
        report['base_images']['final'] = inspect('final-base-inspect', final_base)['Id']
        build = ['docker', 'build', '--platform', 'linux/amd64', '--file', str(prepared / 'Dockerfile'), '--build-arg', 'CI_VERSION=' + version]
        stage_images = {}
        for stage in ['ui-builder', 'server-builder', 'healthcheck-builder']:
            tag = 'study-seatsurfing-' + stage + ':qualification-v1'
            run(stage + '-build', build + ['--target', stage, '--tag', tag, str(checkout)], 600)
            stage_images[stage] = inspect(stage + '-inspect', tag)['Id']
        run('application-build', build + ['--tag', IMAGE, str(checkout)], 300)
        application = inspect('application-inspect', IMAGE)
        assert application['Config']['User'] == '65532:65532'
        assert application['Config']['WorkingDir'] == '/app'
        assert application['Config']['Cmd'] == ['./main']
        report['application_image_id'] = application['Id']
        report['build_stage_image_ids'] = stage_images
        # Inspect installed artifacts offline. No application entrypoint is run.
        ui_inventory = offline_run('ui-installed-inventory', stage_images['ui-builder'], 'node', ['/inspector.mjs'], 120,
            [f'{ROOT / "scripts/extension/inventory_seatsurfing_ui_build_v1.mjs"}:/inspector.mjs:ro'])
        parsed = json.loads(ui_inventory.read_text())
        assert parsed['lockSha256'] == report['original_lock_hashes']['ui/package-lock.json']
        report['ui_dependency_inventory_sha256'] = digest(ui_inventory)
        for stage in ['server-builder', 'healthcheck-builder']:
            offline_run(stage + '-os-packages', stage_images[stage], 'dpkg-query', ['-W'], 30)
        offline_run('ui-os-packages', stage_images['ui-builder'], 'apk', ['info', '-v'], 30)
        stopped_copy('study-seatsurfing-app-inspect', application['Id'], '/app', evidence / 'application')
        stopped_copy('study-seatsurfing-ui-inspect', stage_images['ui-builder'], '/app/build', evidence / 'ui-stage')
        assert inventory(evidence / 'application/ui') == inventory(evidence / 'ui-stage'), 'Final UI differs from inventoried stage'
        for stage, name, source in [('server-builder', 'main', '/go/src/app/main'), ('healthcheck-builder', 'healthcheck', '/go/src/healthcheck/healthcheck')]:
            stopped_copy('study-seatsurfing-' + name + '-inspect', stage_images[stage], source, evidence / (name + '-stage'))
            assert digest(evidence / 'application' / name) == digest(evidence / (name + '-stage'))
            go_info = offline_run(name + '-go-build-info', stage_images[stage], 'go', ['version', '-m', '/inventory/' + name], 30,
                [f'{evidence / "application"}:/inventory:ro'])
            assert '\tpath\t' in go_info.read_text() and ': go1.27.' in go_info.read_text(), 'Missing original Go binary build metadata'
        artifact_rows = inventory(evidence / 'application')
        (evidence / 'application-inventory.json').write_text(json.dumps(artifact_rows, indent=2) + '\n')
        report['application_inventory_sha256'] = digest(evidence / 'application-inventory.json')
        # Verify module metadata inside the actual stage, not just the host
        # checkout: original Docker build commands could otherwise alter copies.
        for stage, paths in [('server-builder', ['server/go.mod', 'server/go.sum']), ('healthcheck-builder', ['healthcheck/go.mod'])]:
            internal_root = '/go/src/app/' if stage == 'server-builder' else '/go/src/healthcheck/'
            module_hashes = offline_run(stage + '-module-hashes', stage_images[stage], 'sha256sum',
                [internal_root + Path(path).name for path in paths], 15).read_text().splitlines()
            assert len(module_hashes) == len(paths)
            for line, path in zip(module_hashes, paths):
                assert line.split()[0] == report['original_lock_hashes'][path], 'Build-stage original module metadata changed'
        # Compile S in a separate image. Never change the application image,
        # request type, validator or dependency declarations to make S pass.
        schema_context = workspace / 'schema-build'
        schema_context.mkdir(mode=0o700)
        probe = ROOT / 'scripts/extension/seatsurfing_original_schema_v1.go'
        (schema_context / 'main.go').write_bytes(probe.read_bytes())
        for name in ['go.mod', 'go.sum']:
            (schema_context / ('original-' + name)).write_bytes((checkout / 'server' / name).read_bytes())
        (schema_context / 'Dockerfile').write_text(schema_dockerfile(final_base))
        inspect('schema-parent-identity', 'study-seatsurfing-server-builder:qualification-v1', stage_images['server-builder'])
        schema_tag = 'study-seatsurfing-schema:qualification-v1'
        run('original-schema-build', ['docker', 'build', '--platform', 'linux/amd64', '--network', 'none',
            '--tag', schema_tag, str(schema_context)], 180)
        schema_image = inspect('original-schema-image', schema_tag)
        assert schema_image['Config']['User'] == '65532:65532'
        assert schema_image['Config']['Entrypoint'] == ['/study-schema/probe']
        stopped_copy('study-seatsurfing-schema-inspect', schema_image['Id'], '/study-schema/probe', evidence / 'schema-probe')
        schema_info = offline_run('schema-go-build-info', stage_images['server-builder'], 'go',
            ['version', '-m', '/inventory/schema-probe'], 30, [f'{evidence}:/inventory:ro'])
        assert '\tpath\tcommand-line-arguments' in schema_info.read_text()
        report['original_schema'] = {'status': 'compiled_not_executed', 'image_id': schema_image['Id'],
            'probe_source_sha256': digest(probe), 'binary_sha256': digest(evidence / 'schema-probe'),
            'dockerfile_sha256': digest(schema_context / 'Dockerfile'), 'runtime_qualified': False}
        verify_checkout(checkout, REVISION, tree_response['tree'], rows)
        assert not subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=all']).strip(), 'Build altered original checkout'
        assert all(digest(checkout / p) == expected for p, expected in report['original_lock_hashes'].items())
        report['status'] = 'source_build_verified_and_inventory_complete'
        report['runtime_qualified'] = False
        save()
    except Exception as error:
        report.update(status='build_failed_no_retry', error_type=type(error).__name__, error=str(error))
        save()
        raise
    finally:
        if containers:
            subprocess.run(['docker', 'rm', '-f', *containers], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)


if __name__ == '__main__':
    main()
