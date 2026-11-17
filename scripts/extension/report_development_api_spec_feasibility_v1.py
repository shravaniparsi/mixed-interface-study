#!/usr/bin/env python3
"""Verify the closed collection and retain literal build-file evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path('/private/tmp/development-api-spec-feasibility-v1')
OUTPUT = ROOT / 'manifests/development-api-spec-feasibility-v1.json'
PATTERN = re.compile(r'openapi|swagger|springdoc|springfox', re.I)


def build():
    schedule_raw = (ROOT / 'manifests/development-api-spec-feasibility-schedule-v1.json').read_bytes()
    schedule = json.loads(schedule_raw)
    collection_raw = (PRIVATE / 'collection.json').read_bytes()
    collection = json.loads(collection_raw)
    partition_raw = (ROOT / 'manifests/project-family-partition-v1.json').read_bytes()
    assert hashlib.sha256(partition_raw).hexdigest() == schedule['partition_sha256']
    allowed = {r['full_name'] for r in json.loads(partition_raw)['rows'] if r['partition'] == 'development'}
    assert len(collection['rows']) == len(schedule['files']) == 4
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
            row['literal_keyword_lines'] = [dict(line=i, text=line.strip())
                for i, line in enumerate(raw.decode().splitlines(), 1) if PATTERN.search(line)]
            row['finding'] = ('build_spec_tooling_text_present' if row['literal_keyword_lines']
                              else 'no_selected_keywords_in_this_build_file')
        else:
            row['finding'] = 'source_unavailable'
        row['specification_obtained'] = False
        row['baseline_qualified'] = False
        rows.append(row)
    return dict(kind='development_api_spec_build_feasibility', freeze='6f60b10',
                schedule_sha256=hashlib.sha256(schedule_raw).hexdigest(),
                collection_sha256=hashlib.sha256(collection_raw).hexdigest(),
                elapsed_seconds=collection['elapsed_seconds'], rows=rows,
                reserved_source_reads=0, independent_evaluation_cases=0,
                interpretation='Literal matches are setup leads, not dependency resolution or API contracts.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    output = json.dumps(build(), indent=2) + '\n'
    if args.verify:
        assert OUTPUT.read_text() == output
        print('Closed collection hashes and derived report verified')
    else:
        OUTPUT.write_text(output)
        print(OUTPUT)
