#!/usr/bin/env python3
"""Build the fixed Gotify source on an isolated CI runner; never start the app.

Not independently dispatched: the ordinary-control registration must authorize
this phase within the same 30-minute job as the controls.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REVISION = '01086b95a8b69ee87383f6e8bcae601d8c33384b'
IMAGE = 'study-gotify:01086b95'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Build is restricted to the registered CI runner')
    source = Path.cwd() / 'subject'
    out = Path(os.environ['RUNNER_TEMP']) / 'evidence'
    out.mkdir(exist_ok=True)
    destination = out / 'gotify-build.json'
    if destination.exists():
        raise SystemExit('Refusing repeated build')
    # The parent job supplies a common deadline, including browser installation,
    # image pulls, build, controls and artifact preparation.
    deadline = float(os.environ['STUDY_JOB_DEADLINE'])
    seconds = min(900, int(deadline - time.time()) - 600)
    if seconds <= 0:
        raise SystemExit('Insufficient shared budget; no build attempted')
    revision = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise SystemExit('Unexpected source revision')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        raise SystemExit('Source checkout is not clean')
    dockerfile = source / 'docker/Dockerfile'
    if sha256(dockerfile) != 'd44475844a812eaa5010b91554086eb97910b7000b97558f121e70d142de2e05':
        raise SystemExit('Dockerfile differs from inspected source')
    if (source / 'GO_VERSION').read_text().strip() != '1.27.2':
        raise SystemExit('Unexpected toolchain version')
    flags = '-w -s -X main.Version=study-01086b95 -X main.Commit=' + REVISION + ' -X main.Mode=prod'
    command = ['timeout', '--signal=TERM', '--kill-after=15', str(seconds),
               'docker', 'buildx', 'build', '--load', '--platform', 'linux/amd64',
               '--progress=plain', '--metadata-file', str(out / 'gotify-buildkit.json'),
               '--build-arg', 'GO_VERSION=1.27.2', '--build-arg', 'BUILD_JS=1',
               '--build-arg', 'RUN_TESTS=0', '--build-arg', 'LD_FLAGS=' + flags,
               '--label', 'org.opencontainers.image.revision=' + REVISION,
               '-t', IMAGE, '-f', str(dockerfile), str(source)]
    record = {'source_revision': revision, 'dockerfile_sha256': sha256(dockerfile),
              'command': command, 'application_started': False,
              'native_ui_build_requested': True, 'native_ui_serving_verified': False,
              'status': 'started', 'time_limit_seconds': seconds,
              'started_unix': time.time()}
    destination.write_text(json.dumps(record, indent=2) + '\n')
    started = time.monotonic()
    with (out / 'gotify-build.log').open('wb') as log:
        environment = dict(os.environ, BUILDX_METADATA_PROVENANCE='max')
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
    record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic() - started,
                  status='built' if result.returncode == 0 else 'build_unavailable')
    if result.returncode == 0:
        raw = subprocess.check_output(['docker', 'image', 'inspect', IMAGE])
        (out / 'gotify-image.json').write_bytes(raw)
        record['image_id'] = json.loads(raw)[0]['Id']
        record['image_inspection_sha256'] = hashlib.sha256(raw).hexdigest()
    destination.write_text(json.dumps(record, indent=2) + '\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
