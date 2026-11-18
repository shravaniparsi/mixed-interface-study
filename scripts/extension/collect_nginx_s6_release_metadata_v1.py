#!/usr/bin/env python3
"""Retain one original dependency release metadata response; no archives."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/catalog-nginx-s6-release-metadata-v1'
NAMES = ['s6-overlay-noarch.tar.xz', 's6-overlay-x86_64.tar.xz']

def main():
    p = argparse.ArgumentParser(); p.add_argument('--freeze', required=True); args = p.parse_args()
    hashes = {}
    for name in ['protocol/catalog-nginx-s6-release-metadata-v1.md', 'scripts/extension/collect_nginx_s6_release_metadata_v1.py']:
        raw = (ROOT / name).read_bytes()
        assert raw == subprocess.check_output(['git', 'show', args.freeze + ':' + name], cwd=ROOT)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    OUT.mkdir(exist_ok=False)
    result = {'freeze': args.freeze, 'artifact_hashes': hashes, 'status': 'unavailable', 'assets': [], 'archives_downloaded': False}
    try:
        raw = subprocess.check_output(['gh', 'api', 'repos/just-containers/s6-overlay/releases/tags/v3.2.3.2'], timeout=30)
        assert len(raw) <= 2 * 1024 * 1024
        (OUT / 'release.json').write_bytes(raw)
        result['response_sha256'] = hashlib.sha256(raw).hexdigest()
        body = json.loads(raw); assert body['tag_name'] == 'v3.2.3.2'
        for name in NAMES:
            matches = [a for a in body['assets'] if a['name'] == name]
            assert len(matches) == 1
            a = matches[0]; digest = a.get('digest')
            result['assets'].append({k: a.get(k) for k in ['id', 'name', 'size', 'digest', 'browser_download_url']})
            assert isinstance(digest, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
        result['status'] = 'declared_archive_digests_available_no_archives_downloaded'
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    (OUT / 'collection.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'assets_recorded': len(result['assets'])}))

if __name__ == '__main__': main()
