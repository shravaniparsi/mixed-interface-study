#!/usr/bin/env python3
"""Full private row evidence bracketed by exact paused-state fingerprints."""
import argparse
import json
import os
from pathlib import Path
import seatsurfing_postgres_checkpoint_v2 as checkpoint


def capture_state(build):
    checkpoint.bind_build(build)
    checkpoint.CAPTURE_PAUSED = True
    checkpoint.guard()
    if checkpoint.sql('SHOW TimeZone').strip() not in ('UTC', 'Etc/UTC'):
        raise RuntimeError('Require original fixture database timestamps in UTC')
    before = checkpoint.fingerprint()
    rows = []
    total = 0
    for table in before['tables']:
        name = checkpoint.ident(table['schema_name']) + '.' + checkpoint.ident(table['relation_name'])
        raw = checkpoint.sql('SELECT row_to_json(t)::text FROM ONLY ' + name + ' t')
        total += len(raw.encode())
        if total > 64 * 1024 * 1024:
            raise RuntimeError('Private comparison-state observation bound')
        lines = raw.splitlines()
        if len(lines) != table['rows']:
            raise RuntimeError('Rows changed during capture')
        canonical = ('\n'.join(sorted(lines)) + ('\n' if lines else '')).encode()
        if checkpoint.digest(canonical) != table['sha256']:
            raise RuntimeError('Raw rows differ from fingerprint')
        rows.append({'schema_name': table['schema_name'], 'relation_name': table['relation_name'], 'rows': lines})
    after = checkpoint.fingerprint()
    if before != after:
        raise RuntimeError('Database changed during paused row capture')
    return {'status':'paused_comparison_state_captured', 'state':before, 'row_data':rows,
            'raw_row_bytes':total, 'field_exclusions':[]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    assert not args.output.exists(), 'No evidence overwrite'
    result = capture_state(json.loads(args.build_report.read_text()))
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd,'w') as stream: json.dump(result,stream,indent=2);stream.write('\n')


if __name__ == '__main__': main()
