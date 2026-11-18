#!/usr/bin/env python3
"""Offline integrity verification of the frozen source acquisition."""
import base64
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def main():
    out = ROOT / 'results/redesign-development-source-wave3-v1'
    data = json.loads((out / 'collection.json').read_text())
    assert data['status'] == 'source_wave_closed' and data['application_executed'] is False
    for name, digest in data['input_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    scheduled = json.loads((ROOT / 'manifests/redesign-development-source-wave3-v1.json').read_text())['rows']
    assert len(data['rows']) == len(scheduled) == 9
    total = 0
    for expected, row in zip(scheduled, data['rows']):
        assert all(row[k] == v for k, v in expected.items())
        assert row['status'] == 'collected_verified'
        raw = (out / row['file']).read_bytes()
        envelope = (out / row['envelope']).read_bytes()
        assert hashlib.sha256(envelope).hexdigest() == row['envelope_sha256']
        assert base64.b64decode(json.loads(envelope)['content']) == raw
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['blob_sha']
        assert len(raw) == row['bytes'] == row['declared_bytes']
        total += len(raw)
    prior = json.loads((ROOT / 'results/redesign-development-source-wave2-v1/collection.json').read_text())
    assert total + sum(prior['decoded_bytes'].values()) == sum(data['decoded_bytes'].values())
    result = {'status': 'verified', 'files': 9, 'decoded_bytes': total, 'scientific_cases': 0, 'application_executed': False}
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
if __name__ == '__main__':
    main()
