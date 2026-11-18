#!/usr/bin/env python3
"""Verify runtime materialization against the frozen revision and reviewed blobs."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '3833c3ae5714f164dd6870f4d28865e78d60a4cc'
REPOSITORY = 'mathesar-foundation/mathesar'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    def git(*argv):
        return subprocess.check_output(['git', '-C', str(args.source), *argv]).decode().strip()
    assert git('rev-parse', 'HEAD') == REVISION
    assert git('status', '--porcelain', '--untracked-files=all') == ''
    verified = []
    for wave in range(1, 7):
        collection = json.loads((ROOT / f'results/catalog-source-wave{wave}-v1/collection.json').read_text())
        for row in collection['rows']:
            if row['repository'] != REPOSITORY:
                continue
            assert row['status'] == 'collected_verified'
            raw = (args.source / row['path']).read_bytes()
            sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            assert sha == row['blob_sha']
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            verified.append({'path': row['path'], 'git_blob': sha, 'sha256': row['sha256']})
    assert len(verified) == 67
    extra = {}
    for name in ['mathesar_ui/package-lock.json', 'requirements.txt', 'requirements-dev.txt', 'Dockerfile']:
        raw = (args.source / name).read_bytes()
        extra[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    result = {'repository': REPOSITORY, 'revision': REVISION, 'clean_checkout': True,
              'verified_previously_acquired_blobs': verified, 'build_inputs': extra,
              'scope': 'Full checkout for original build only; not additional manual source screening.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
