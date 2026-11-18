#!/usr/bin/env python3
"""Build pinned Traduora only inside a separately registered ordinary-control job."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REVISION = '0eac8b7daba8caa6b86041dc037a36a84c49535c'
IMAGE = 'study-traduora:0eac8b7d'
BASE = 'node:26.12.1-alpine3.23'
DOCKERFILE_SHA256 = '9c0e170c2d660946b731349f0de376205b5f5950ee2c75d0c252d90275546cf8'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Build restricted to registered CI runner')
    source = Path.cwd() / 'subject'
    out = Path(os.environ['RUNNER_TEMP']) / 'evidence'
    out.mkdir(exist_ok=True)
    destination = out / 'traduora-build.json'
    if destination.exists():
        raise SystemExit('Refusing repeated build')
    deadline = float(os.environ['STUDY_JOB_DEADLINE'])
    seconds = min(900, int(deadline - time.time()) - 600)
    if seconds <= 0:
        raise SystemExit('Insufficient shared job budget')
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        raise SystemExit('Unexpected or modified subject checkout')
    original = source / 'Dockerfile'
    if digest(original) != DOCKERFILE_SHA256:
        raise SystemExit('Original Dockerfile differs from inspected source')
    bases = json.loads((out / 'traduora-base-images.json').read_text())
    base_digest = bases[BASE]['digest']
    if not base_digest.startswith('node@sha256:') or len(base_digest.split(':')[-1]) != 64:
        raise SystemExit('Unexpected base digest')
    text = original.read_text()
    if text.count('FROM ' + BASE) != 2:
        raise SystemExit('Unexpected original FROM declarations')
    prepared = out / 'traduora-pinned.Dockerfile'
    prepared.write_text(text.replace('FROM ' + BASE, 'FROM ' + base_digest))
    command = ['timeout', '--signal=TERM', '--kill-after=15', str(seconds),
               'docker', 'buildx', 'build', '--load', '--platform', 'linux/amd64',
               '--progress=plain', '--metadata-file', str(out / 'traduora-buildkit.json'),
               '--build-arg', 'VERDACCIO_REGISTRY=',
               '--label', 'org.opencontainers.image.revision=' + REVISION,
               '-t', IMAGE, '-f', str(prepared), str(source)]
    record = dict(source_revision=revision, dockerfile_sha256=digest(original),
                  prepared_dockerfile_sha256=digest(prepared), base_images=bases,
                  application_started=False, native_ui_serving_verified=False,
                  status='started', command=command, time_limit_seconds=seconds,
                  started_unix=time.time())
    destination.write_text(json.dumps(record, indent=2) + '\n')
    started = time.monotonic()
    with (out / 'traduora-build.log').open('wb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, BUILDX_METADATA_PROVENANCE='max'))
    record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic() - started,
                  status='built' if result.returncode == 0 else 'build_unavailable')
    if result.returncode == 0:
        raw = subprocess.check_output(['docker', 'image', 'inspect', IMAGE])
        (out / 'traduora-image.json').write_bytes(raw)
        record['image_id'] = json.loads(raw)[0]['Id']
        record['image_inspection_sha256'] = hashlib.sha256(raw).hexdigest()
    destination.write_text(json.dumps(record, indent=2) + '\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
