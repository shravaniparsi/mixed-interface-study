#!/usr/bin/env python3
"""Generate a reviewable dependency-pinned Dockerfile; never build or execute."""
import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '20016b9d91d49c9133f1b4d26ab5a289c72ec1db'
ARCHIVES = ('s6-overlay-noarch.tar.xz', 's6-overlay-x86_64.tar.xz')

def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise ValueError('Expected complete SHA256 digest')
    return value

def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Original build contract changed: ' + old[:60])
    return text.replace(old, new, 1)

def derive(dockerfile, installer, base, testca, archives):
    digest(base); digest(testca)
    if set(archives) != set(ARCHIVES):
        raise ValueError('Exactly the two original amd64 supervisor archives are required')
    for value in archives.values(): digest(value)
    if 'S6_OVERLAY_VERSION=3.2.3.2\n' not in installer:
        raise ValueError('Original supervisor version changed')
    checks = [archives[name][7:] + '  /tmp/' + name for name in ARCHIVES]
    verification = "printf '%s\\n' " + ' '.join(shlex.quote(v) for v in checks) + ' | sha256sum -c -\n'
    installer = once(installer, "tar -C / -Jxpf '/tmp/s6-overlay-noarch.tar.xz'", verification + "tar -C / -Jxpf '/tmp/s6-overlay-noarch.tar.xz'")
    dockerfile = once(dockerfile, 'ARG BASE_IMAGE=nginxproxymanager/nginx-full:certbot-node', 'ARG BASE_IMAGE=nginxproxymanager/nginx-full@' + base)
    dockerfile = once(dockerfile, 'FROM nginxproxymanager/testca AS testca', 'FROM nginxproxymanager/testca@' + testca + ' AS testca')
    # Keep the original COPY and its executable mode. Replace installer content
    # using shell-quoted lines, adding only verification before original extraction.
    command = "printf '%s\\n' " + ' '.join(shlex.quote(line) for line in installer.splitlines()) + ' > /tmp/install-s6'
    dockerfile = once(dockerfile, 'RUN /tmp/install-s6 "${TARGETPLATFORM}" && rm -f /tmp/install-s6', 'RUN ' + command + ' && /tmp/install-s6 "${TARGETPLATFORM}" && rm -f /tmp/install-s6')
    dockerfile = once(dockerfile, 'RUN yarn install \\\n', 'RUN yarn install --frozen-lockfile \\\n')
    return dockerfile, installer

def acquired(wave, sequence):
    directory = ROOT / f'results/catalog-source-wave{wave}-v1'
    row = next(r for r in json.loads((directory / 'collection.json').read_text())['rows'] if r['sequence'] == sequence)
    raw = (directory / row['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert row['revision'] == REVISION
    return raw.decode(), row

def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    bases = json.loads((ROOT / 'results/catalog-nginx-build-base-metadata-v1/collection.json').read_text())
    assert bases['status'] == 'image_metadata_stage_closed'
    images = {r['repository']: r for r in bases['images']}
    assert all(r['status'] == 'metadata_verified_no_layers_pulled' for r in images.values())
    release = json.loads((ROOT / 'results/catalog-nginx-s6-release-metadata-v1/collection.json').read_text())
    assert release['status'] == 'declared_archive_digests_available_no_archives_downloaded'
    dockerfile, docker_row = acquired(1, 30)
    installer, installer_row = acquired(21, 7)
    base = images['nginxproxymanager/nginx-full']['manifest_digest']
    ca = images['nginxproxymanager/testca']['manifest_digest']
    derived, checked_installer = derive(dockerfile, installer, base, ca, {a['name']: a['digest'] for a in release['assets']})
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'Dockerfile').write_text(derived)
    (args.output / 'install-s6').write_text(checked_installer)
    manifest = {
        'status': 'build_recipe_prepared_not_executed', 'application_revision': REVISION,
        'original_dockerfile': docker_row, 'original_installer': installer_row,
        'base_manifest': base, 'testca_manifest': ca,
        'derived_dockerfile_sha256': hashlib.sha256(derived.encode()).hexdigest(),
        'checked_installer_sha256': hashlib.sha256(checked_installer.encode()).hexdigest(),
        'changes': ['pin original BASE_IMAGE default', 'pin original testca FROM', 'verify original supervisor archives before extraction', 'require unchanged backend dependency lock'],
        'runtime_authorized': False,
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'status': manifest['status'], 'output': str(args.output)}))

if __name__ == '__main__': main()
