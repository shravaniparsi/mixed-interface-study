#!/usr/bin/env python3
"""Resolve public image metadata only; never pull layers or run containers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/agentcompany-service-capability-v1/source/servers/docker-compose.yml'
BASE = ROOT / 'results/agentcompany-service-images-v1'
ACCEPT = ', '.join(['application/vnd.oci.image.index.v1+json',
                    'application/vnd.docker.distribution.manifest.list.v2+json',
                    'application/vnd.oci.image.manifest.v1+json',
                    'application/vnd.docker.distribution.manifest.v2+json'])


def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def image_references():
    refs = re.findall(r'^    image: (\S+)$', SOURCE.read_text(), re.M)
    # Use the exact Compose default; no alternative database release.
    refs = [r.replace('${MONGODB_VERSION:-5.0}', '5.0') for r in refs]
    assert all('$' not in r for r in refs)
    return sorted(set(refs))


def collect():
    BASE.mkdir(parents=True, exist_ok=True)
    if (BASE / 'collection.json').exists():
        raise RuntimeError('Existing collection must not be overwritten')
    images = image_references()
    assert len(images) == 7
    rows = []
    transferred = 0
    def bounded(url, headers):
        nonlocal transferred
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=40) as response:
            raw = response.read(1024 * 1024 + 1)
            assert len(raw) <= 1024 * 1024
            transferred += len(raw)
            assert transferred <= 16 * 1024 * 1024
            return raw, response.headers.get('Docker-Content-Digest')
    for n, image in enumerate(images):
        row = {'image': image}
        try:
            first, sep, tail = image.partition('/')
            if sep and ('.' in first or ':' in first):
                registry, reference = first, tail
                if registry == 'docker.io':
                    registry = 'registry-1.docker.io'
            else:
                registry, reference = 'registry-1.docker.io', image
                if '/' not in reference:
                    reference = 'library/' + reference
            repository, tag = reference.rsplit(':', 1)
            headers = {'Accept': ACCEPT}
            url = f'https://{registry}/v2/{repository}/manifests/{tag}'
            try:
                raw, reported = bounded(url, headers)
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise
                challenge = error.headers.get('WWW-Authenticate', '')
                fields = dict(re.findall(r'(\w+)="([^"]+)"', challenge))
                realm = fields['realm']
                assert urllib.parse.urlparse(realm).hostname in ('ghcr.io', 'auth.docker.io', 'registry.rocket.chat')
                query = urllib.parse.urlencode({k: fields[k] for k in ('service', 'scope') if k in fields})
                auth_raw, _ = bounded(realm + '?' + query, {})
                auth = json.loads(auth_raw)
                headers['Authorization'] = 'Bearer ' + (auth.get('token') or auth['access_token'])
                raw, reported = bounded(url, headers)
            def save(raw, suffix, reported=None):
                computed = digest(raw)
                assert reported in (None, computed)
                path = f'{n:02d}-{suffix}.json'
                (BASE / path).write_bytes(raw)
                return {'file': path, 'digest': computed, 'bytes': len(raw)}
            row['tag_manifest'] = save(raw, 'tag', reported)
            manifest = json.loads(raw)
            if 'manifests' in manifest:
                options = [m for m in manifest['manifests'] if m.get('platform', {}).get('os') == 'linux'
                           and m.get('platform', {}).get('architecture') == 'amd64']
                assert len(options) == 1, 'Expected one linux/amd64 child'
                expected = options[0]['digest']
                raw, reported = bounded(f'https://{registry}/v2/{repository}/manifests/{expected}', headers)
                assert digest(raw) == expected and len(raw) == options[0]['size']
                row['platform_manifest'] = save(raw, 'amd64', reported)
                manifest = json.loads(raw)
            else:
                # A single manifest alone does not establish its architecture.
                config = manifest['config']
                config_raw, _ = bounded(f'https://{registry}/v2/{repository}/blobs/{config["digest"]}', headers)
                assert digest(config_raw) == config['digest'] and len(config_raw) == config['size']
                row['platform_config'] = save(config_raw, 'config')
                platform = json.loads(config_raw)
                assert platform['os'] == 'linux' and platform['architecture'] == 'amd64'
                row['platform_manifest'] = row['tag_manifest']
            row['compressed_layer_bytes'] = sum(layer['size'] for layer in manifest['layers'])
            row['layer_count'] = len(manifest['layers'])
            row['immutable_reference'] = image.rsplit(':', 1)[0] + '@' + row['platform_manifest']['digest']
            row['status'] = 'resolved'
        except Exception as error:
            row['status'] = 'unresolved'
            row['error_type'] = type(error).__name__
            if isinstance(error, urllib.error.HTTPError):
                row['http_status'] = error.code
        rows.append(row)
    value = {'kind': 'agentcompany_service_image_metadata_v1', 'source_sha256': digest(SOURCE.read_bytes()),
             'images': rows, 'metadata_bytes_transferred': transferred,
             'layer_bytes_downloaded': 0, 'containers_started': 0}
    (BASE / 'collection.json').write_text(json.dumps(value, indent=2) + '\n')
    return verify()


def verify():
    value = json.loads((BASE / 'collection.json').read_text())
    assert value['source_sha256'] == digest(SOURCE.read_bytes())
    assert sorted(r['image'] for r in value['images']) == image_references()
    layers = {}
    # Follow-up diagnostics are kept separate; the initial snapshot is immutable.
    diagnostic_path = BASE / 'rocketchat-availability-diagnostic.json'
    if diagnostic_path.exists():
        diagnostic = json.loads(diagnostic_path.read_text())
        raw = (BASE / diagnostic['body_file']).read_bytes()
        assert len(raw) == diagnostic['bytes']
        assert hashlib.sha256(raw).hexdigest() == diagnostic['sha256']
        followup = json.loads((BASE / 'rocketchat-authenticated-followup.json').read_text())
        for item in followup['files']:
            raw = (BASE / item['file']).read_bytes()
            assert digest(raw) == item['digest'] and len(raw) == item['bytes']
        assert followup['status'] == 'unresolved' and followup['http_status'] == 429
    for row in value['images']:
        for key in ('tag_manifest', 'platform_manifest', 'platform_config'):
            if key in row:
                item = row[key]
                raw = (BASE / item['file']).read_bytes()
                assert digest(raw) == item['digest'] and len(raw) == item['bytes']
        if row['status'] != 'resolved':
            continue
        manifest = json.loads((BASE / row['platform_manifest']['file']).read_text())
        tag = json.loads((BASE / row['tag_manifest']['file']).read_text())
        if 'manifests' in tag:
            selected = [m for m in tag['manifests'] if m.get('platform', {}).get('os') == 'linux' and m.get('platform', {}).get('architecture') == 'amd64']
            assert len(selected) == 1 and selected[0]['digest'] == row['platform_manifest']['digest']
        else:
            config = json.loads((BASE / row['platform_config']['file']).read_text())
            assert config['os'] == 'linux' and config['architecture'] == 'amd64'
            assert manifest['config']['digest'] == row['platform_config']['digest']
        assert row['compressed_layer_bytes'] == sum(l['size'] for l in manifest['layers'])
        assert row['layer_count'] == len(manifest['layers'])
        assert row['immutable_reference'] == row['image'].rsplit(':', 1)[0] + '@' + row['platform_manifest']['digest']
        for layer in manifest['layers']:
            assert layer['digest'] not in layers or layers[layer['digest']] == layer['size']
            layers[layer['digest']] = layer['size']
    return {'resolved': sum(r['status'] == 'resolved' for r in value['images']),
            'total_images': len(value['images']), 'distinct_compressed_layer_bytes': sum(layers.values()),
            'interpretation': 'Registry metadata, not measured disk/memory, image-source equivalence or runtime qualification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    print(json.dumps(collect() if args.collect else verify(), indent=2))
