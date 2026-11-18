#!/usr/bin/env python3
"""Build the frozen Maxun sources inside a separately registered control job.

No standalone build job is authorized. Both builds and dependency extraction
share 900 seconds and leave at least 600 seconds of the parent job for controls.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

REVISION = '81ad253702820e336eb1abfafff1d224dbada0bb'
RECIPES = {
    'backend': ('a9d2f0d7ea61ba0d00d5d6163f3ebc13aa92521508ffba1722ff01e4e5cf606f', ['node:22', 'node:22-slim']),
    'frontend': ('912ac7acde9f33d7c276de6425837210b4c38dc759bfd91f619e4bc8be2a260c', ['node:22-alpine', 'node:22-alpine']),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin_recipe(raw, expected_hash, expected_bases, bases):
    if sha(raw) != expected_hash:
        raise ValueError('Original Dockerfile differs from inspected source')
    text = raw.decode()
    found = re.findall(r'^FROM (\S+)', text, flags=re.M)
    if found != expected_bases:
        raise ValueError('Unexpected FROM declarations')
    for base in set(found):
        immutable = bases[base]['digest']
        if not re.fullmatch(r'node@sha256:[0-9a-f]{64}', immutable):
            raise ValueError('Unexpected base digest')
        text = re.sub(r'^FROM ' + re.escape(base) + r'(?=\s|$)',
                      'FROM ' + immutable, text, flags=re.M)
    return text.encode()


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Build restricted to separately registered CI control job')
    source = Path.cwd() / 'subject'
    out = Path(os.environ['RUNNER_TEMP']) / 'evidence'
    out.mkdir(exist_ok=True)
    record_path = out / 'maxun-build.json'
    if record_path.exists():
        raise SystemExit('Refusing repeat build')
    end = min(time.time() + 900, float(os.environ['STUDY_JOB_DEADLINE']) - 630)
    if end <= time.time():
        raise SystemExit('Insufficient shared job budget')
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        raise SystemExit('Unexpected or modified subject checkout')
    bases = json.loads((out / 'maxun-base-images.json').read_text())
    prepared = {}
    for kind, (expected_hash, expected_bases) in RECIPES.items():
        original = (source / ('Dockerfile.' + kind)).read_bytes()
        raw = pin_recipe(original, expected_hash, expected_bases, bases)
        path = out / ('maxun-' + kind + '-pinned.Dockerfile')
        path.write_bytes(raw)
        prepared[kind] = path
    record = dict(source_revision=revision, base_images=bases, status='started',
                  application_started=False, runtime_qualified=False,
                  started_unix=time.time(), build_deadline_unix=end, commands=[], artifacts={})
    record_path.write_text(json.dumps(record, indent=2) + '\n')

    def save():
        record_path.write_text(json.dumps(record, indent=2) + '\n')

    def run(args, name):
        seconds = int(end - time.time())
        if seconds <= 0:
            raise TimeoutError('Shared source-build deadline exhausted')
        entry = dict(command=args, started_unix=time.time(), timeout_seconds=seconds)
        record['commands'].append(entry)
        save()
        with (out / (name + '.log')).open('wb') as log:
            result = subprocess.run(['timeout', '--signal=TERM', '--kill-after=10', str(seconds)] + args,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    env=dict(os.environ, BUILDX_METADATA_PROVENANCE='max'))
        entry.update(exit_code=result.returncode, finished_unix=time.time())
        save()
        if result.returncode:
            raise RuntimeError(name + ' failed with exit ' + str(result.returncode))

    try:
        for kind in RECIPES:
            image = 'study-maxun-' + kind + ':' + REVISION[:8]
            builder = image + '-builder'
            common = ['docker', 'buildx', 'build', '--load', '--platform', 'linux/amd64',
                      '--progress=plain', '--label', 'org.opencontainers.image.revision=' + REVISION,
                      '-f', str(prepared[kind])]
            run(common + ['--target', 'builder', '--metadata-file', str(out / (kind + '-builder-metadata.json')),
                          '-t', builder, str(source)], kind + '-builder')
            container = 'study-maxun-' + kind + '-dependency-export'
            try:
                # Creating a stopped container permits file export without running its CMD.
                run(['docker', 'create', '--name', container, builder], kind + '-export-create')
                for filename, container_path in [('package-lock.json', '/app/package-lock.json'),
                                                  ('installed-lock.json', '/app/node_modules/.package-lock.json')]:
                    destination = out / (kind + '-' + filename)
                    run(['docker', 'cp', container + ':' + container_path, str(destination)], kind + '-export-' + filename)
                    record['artifacts'][destination.name] = sha(destination.read_bytes())
            finally:
                subprocess.run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10, check=False)
            run(common + ['--metadata-file', str(out / (kind + '-runner-metadata.json')),
                          '-t', image, str(source)], kind + '-runner')
            run(['docker', 'image', 'inspect', image], kind + '-image-inspect')
            raw = (out / (kind + '-image-inspect.log')).read_bytes()
            record['artifacts'][kind + '-image-inspect.log'] = sha(raw)
            record[kind + '_image_id'] = json.loads(raw)[0]['Id']
            record['artifacts'][prepared[kind].name] = sha(prepared[kind].read_bytes())
        record['status'] = 'built'
    except Exception as exc:
        record.update(status='build_unavailable', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        record['finished_unix'] = time.time()
        save()


if __name__ == '__main__':
    main()
