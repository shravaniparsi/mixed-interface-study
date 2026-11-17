#!/usr/bin/env python3
"""Verify bounded setup collection; publish only selected nonsecret evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path('/private/tmp/development-generated-spec-setup-v1')
OUT = ROOT / 'manifests/development-generated-spec-setup-v1.json'
# Fixed nonsecret setup excerpts. No credential-bearing config is copied.
LINES = {1: [2, 5, 8], 2: [10], 3: [10, 14, 31], 4: [3],
         5: list(range(19, 26)) + list(range(96, 105)) + [163, 164],
         6: [40, 67], 7: [83, 87, 91, 92]}


def build():
    schedule_raw = (ROOT / 'manifests/development-generated-spec-setup-schedule-v1.json').read_bytes()
    schedule = json.loads(schedule_raw)
    collection_raw = (PRIVATE / 'collection.json').read_bytes()
    collection = json.loads(collection_raw)
    partition_raw = (ROOT / 'manifests/project-family-partition-v1.json').read_bytes()
    assert hashlib.sha256(partition_raw).hexdigest() == schedule['partition_sha256']
    allowed = {r['full_name'] for r in json.loads(partition_raw)['rows'] if r['partition'] == 'development'}
    assert len(collection['rows']) == len(schedule['files']) == 7
    rows = []
    for index, (item, result) in enumerate(zip(schedule['files'], collection['rows']), 1):
        assert item['full_name'] in allowed
        assert all(item[k] == result[k] for k in item)
        assert result['index'] == index
        row = dict(result)
        if result['status'] == 'verified':
            raw = (PRIVATE / (str(index) + '.txt')).read_bytes()
            assert len(raw) == result['bytes'] <= 256 * 1024
            assert hashlib.sha256(raw).hexdigest() == result['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['blob_sha']
            lines = raw.decode().splitlines()
            row['setup_excerpts'] = [dict(line=i, text=lines[i-1]) for i in LINES[index]]
        rows.append(row)
    return dict(kind='development_generated_spec_setup', freeze='5936774',
                schedule_sha256=hashlib.sha256(schedule_raw).hexdigest(),
                collection_sha256=hashlib.sha256(collection_raw).hexdigest(),
                elapsed_seconds=collection['elapsed_seconds'], rows=rows,
                reserved_source_reads=0, independent_evaluation_cases=0,
                application_builds=0, specifications_obtained=0,
                interpretation='Declared configuration only; no dependency resolution or runtime qualification.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    output = json.dumps(build(), indent=2) + '\n'
    if args.verify:
        assert OUT.read_text() == output
        print('Setup collection provenance and nonsecret excerpts verified')
    else:
        OUT.write_text(output)
        print(OUT)
