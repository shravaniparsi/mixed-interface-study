#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'manifests/openapi-adapter-correction-v2.json').read_text())
for name, digest in manifest['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
old = json.loads((ROOT / 'evidence/openapi-adapter-environments-v1/punkpeye/package-lock.json').read_text())['packages']
new = json.loads((ROOT / 'evidence/openapi-adapter-environments-v2/punkpeye/package-lock.json').read_text())['packages']
assert set(new) - set(old) == {'node_modules/openapi-types'}
assert new['node_modules/openapi-types']['version'] == '12.1.3'
for name, package in old.items():
    if name:
        assert new[name].get('version') == package.get('version')
        assert new[name].get('integrity') == package.get('integrity')
print('Single missing-peer correction verified; all existing versions unchanged')
