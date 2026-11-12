#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'manifests/openapi-adapter-execution-v1.json').read_text())
assert manifest['scientific_execution_authorized']
for name, digest in manifest['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
print('Frozen adapter execution files verified')
