#!/usr/bin/env python3
"""Prepare pinned original build inputs; never install, pull or execute an app."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/catalog-seatsurfing-source-build-preparation-v1'
REVISION = '9953f452324bab6fb8f7106dd8965cc401aa456c'
REPOSITORY = 'seatsurfing/seatsurfing'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def prepare():
    identities = []
    dockerfile = None
    seen = set()
    for wave in range(1, 36):
        directory = ROOT / f'results/catalog-source-wave{wave}-v1'
        collection = json.loads((directory / 'collection.json').read_text())
        assert collection['status'] == 'source_wave_closed'
        for row in collection['rows']:
            if row['repository'] != REPOSITORY:
                continue
            assert row['revision'] == REVISION and row['path'] not in seen
            seen.add(row['path'])
            assert row['status'] == 'collected_verified'
            raw = (directory / row['file']).read_bytes()
            assert sha(raw) == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob_sha']
            identities.append({'path': row['path'], 'blob_sha': row['blob_sha'], 'sha256': sha(raw), 'bytes': len(raw)})
            if row['path'] == 'Dockerfile':
                dockerfile = raw
    assert len(identities) == 40 and dockerfile is not None
    directory = ROOT / 'results/catalog-seatsurfing-build-base-metadata-v1'
    collection = json.loads((directory / 'collection.json').read_text())
    assert collection['status'] == 'image_metadata_stage_closed'
    bases = {}
    for row in collection['images']:
        assert row['status'] == 'metadata_verified_no_layers_pulled'
        for request in row['requests']:
            if 'file' in request:
                assert sha((directory / request['file']).read_bytes()) == request['sha256']
        digest = row['manifest_digest']
        assert len(digest) == 71 and digest.startswith('sha256:')
        assert all(c in '0123456789abcdef' for c in digest[7:])
        bases[row['repository']] = {'reference': row['repository'] + '@' + digest, 'config_digest': row['config_digest'], 'compressed_layer_bytes': row['compressed_layer_bytes']}
    assert set(bases) == {'tonistiigi/xx', 'library/node', 'library/golang', 'library/postgres'}
    text = dockerfile.decode()
    replacements = [
        ('docker.io/tonistiigi/xx AS xx', 'docker.io/' + bases['tonistiigi/xx']['reference'] + ' AS xx', 1),
        ('node:24-alpine AS ui-builder', 'docker.io/' + bases['library/node']['reference'] + ' AS ui-builder', 1),
        ('docker.io/library/golang:1.27-bookworm AS ', 'docker.io/' + bases['library/golang']['reference'] + ' AS ', 2),
    ]
    for old, new, count in replacements:
        assert text.count(old) == count, old
        text = text.replace(old, new)
    final = 'gcr.io/distroless/base-debian13@sha256:0e48b9bcd868bce9fa872cee10b52961d9e32677823da4bf68eefb44f38e7b9d'
    assert text.count('FROM ' + final) == 1
    generated = text.encode()
    manifest = {
        'application_revision': REVISION,
        'application_repository': REPOSITORY,
        'application_executed': False,
        'status': 'preparation_only_runtime_unqualified',
        'original_dockerfile_sha256': sha(dockerfile),
        'generated_dockerfile_sha256': sha(generated),
        'base_metadata_sha256': sha((directory / 'collection.json').read_bytes()),
        'bases': bases,
        'final_base_original_reference': final,
        'changes': 'Only original cross-build, Node and two Go FROM references are pinned; PostgreSQL is recorded for the future runtime.',
        'source_files_to_verify_at_runtime': sorted(identities, key=lambda x: x['path']),
        'runtime_requirements': ['verify complete frozen source tree and every retained source blob', 'preserve original package-lock.json and go.sum; inventory downloaded dependencies', 'record CI_VERSION from original version.txt', 'verify actual base image/config and final application identities', 'publish isolated networking, persistent JWT keys and full database/browser restoration', 'qualify warm native, restored native and restored API ordinary controls before science'],
    }
    return {'Dockerfile': generated, 'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    expected = prepare()
    if args.verify:
        for name, raw in expected.items():
            assert (OUT / name).read_bytes() == raw, name
        print('Original source hashes and deterministic pinned build preparation verified; runtime remains unqualified.')
    else:
        OUT.mkdir(exist_ok=False)
        for name, raw in expected.items():
            (OUT / name).write_bytes(raw)
        print('Prepared pinned Dockerfile and forty-file source identity manifest; no build executed.')

if __name__ == '__main__':
    main()
