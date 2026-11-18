#!/usr/bin/env python3
"""Bounded official registry metadata only; never pull or run image layers."""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/browser-image-metadata-v1'
ACCEPT = ', '.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])


def main():
    OUT.mkdir(exist_ok=False)
    started = time.monotonic()
    result = {'kind': 'fixed_browser_image_metadata', 'tag': 'mcr.microsoft.com/playwright:v1.62.1-noble', 'rows': [], 'status': 'failed'}
    def fetch(path, expected=None):
        remaining = 90 - (time.monotonic() - started)
        if remaining <= 0 or len(result['rows']) >= 3:
            raise ValueError('Metadata acquisition bound')
        row = {'path': path}; result['rows'].append(row)
        request = urllib.request.Request('https://mcr.microsoft.com/v2/playwright/' + path, headers={'Accept': ACCEPT})
        with urllib.request.urlopen(request, timeout=min(30, remaining)) as response:
            raw = response.read(1024*1024+1)
            row.update(http_status=response.status, registry_digest=response.headers.get('Docker-Content-Digest'))
        if len(raw) > 1024*1024:
            raise ValueError('Metadata byte bound')
        digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
        row.update(bytes=len(raw), digest=digest)
        if expected is not None and expected != digest:
            raise ValueError('Referenced digest mismatch')
        if row['registry_digest'] is not None and row['registry_digest'] != digest:
            raise ValueError('Registry digest mismatch')
        name = str(len(result['rows'])) + '.json'; (OUT/name).write_bytes(raw); row['file'] = name
        return json.loads(raw), digest
    try:
        package = json.loads((ROOT/'scripts/ci/package.json').read_text())
        if package['dependencies']['playwright'] != '1.62.1':
            raise ValueError('Unexpected existing Playwright version')
        manifest, digest = fetch('manifests/v1.62.1-noble')
        result['tag_digest'] = digest
        if 'manifests' in manifest:
            matches = [m for m in manifest['manifests'] if m.get('platform',{}).get('os')=='linux' and m.get('platform',{}).get('architecture')=='amd64']
            if len(matches) != 1:
                raise ValueError('Ambiguous amd64 platform')
            manifest, digest = fetch('manifests/' + matches[0]['digest'], matches[0]['digest'])
        result['image_digest'] = digest
        result['declared_compressed_layer_bytes'] = sum(r['size'] for r in manifest['layers'])
        config, _ = fetch('blobs/' + manifest['config']['digest'], manifest['config']['digest'])
        if config.get('architecture') != 'amd64' or config.get('os') != 'linux':
            raise ValueError('Image platform mismatch')
        result.update(status='metadata_resolved_runtime_unqualified', architecture=config['architecture'], os=config['os'], image_environment=config.get('config',{}).get('Env',[]))
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result['elapsed_seconds'] = time.monotonic() - started
    result['image_pulled'] = False; result['application_executions'] = 0
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
