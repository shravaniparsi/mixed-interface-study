#!/usr/bin/env python3
"""Read-only package inspection, to run inside the pinned image in registered CI."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from pathlib import Path

REVISION = '3d77e324d8316033f30acb83058736aa7e468d81'
REPOSITORY = 'roflcoopter/viseron'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refuse package-report overwrite')
    result = {'status': 'unqualified', 'declared_revision': os.getenv('VISERON_GIT_COMMIT'),
              'expected_revision': REVISION, 'packaged_sources': [],
              'unpackaged_sources': [], 'frontend_assets': [],
              'frontend_source_byte_equivalence_claimed': False}
    try:
        if result['declared_revision'] != REVISION:
            raise RuntimeError('Packaged revision declaration mismatch')
        if platform.machine() != 'x86_64':
            raise RuntimeError('Unexpected architecture')
        seen = set()
        for wave in range(1, 11):
            collection = json.loads((args.study / f'results/catalog-source-wave{wave}-v1/collection.json').read_text())
            for row in collection['rows']:
                if row['repository'] != REPOSITORY:
                    continue
                if row['status'] != 'collected_verified' or row['path'] in seen:
                    raise RuntimeError('Unverified or duplicated source registration')
                seen.add(row['path'])
                original = row['path']
                if original.startswith('viseron/'):
                    packaged = Path('/src') / original
                elif original.startswith('rootfs/'):
                    packaged = Path('/') / original.removeprefix('rootfs/')
                else:
                    result['unpackaged_sources'].append(original)
                    continue
                item = {'source_path': original, 'image_path': str(packaged),
                        'expected_sha256': row['sha256'], 'actual_sha256': sha(packaged)}
                result['packaged_sources'].append(item)
                if item['expected_sha256'] != item['actual_sha256']:
                    raise RuntimeError('Packaged source differs: ' + original)
        if not result['packaged_sources']:
            raise RuntimeError('No packaged source checked')
        assets = Path('/src/viseron/frontend')
        if not (assets / 'index.html').is_file():
            raise RuntimeError('Original compiled frontend missing')
        for path in sorted(assets.rglob('*')):
            if path.is_symlink():
                raise RuntimeError('Unmapped frontend asset symlink')
            if path.is_file():
                result['frontend_assets'].append({'path': str(path.relative_to(assets)),
                                                  'bytes': path.stat().st_size, 'sha256': sha(path)})
        if not any(item['path'].endswith('.js') for item in result['frontend_assets']):
            raise RuntimeError('Compiled JavaScript asset inventory empty')
        result['python_version'] = platform.python_version()
        result['packages'] = {name: importlib.metadata.version(name)
                              for name in ['voluptuous', 'SQLAlchemy', 'pydantic', 'tornado']}
        if result['packages']['voluptuous'] != '0.16.0':
            raise RuntimeError('Original schema validator version mismatch')
        result['postgres_client_version'] = subprocess.check_output(
            ['psql', '--version'], timeout=10).decode().strip()
        result['status'] = 'packaged_source_checks_passed_pending_native_controls'
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
