#!/usr/bin/env python3
"""Check retained document inventories and reconstruct available audit timestamps."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from checkpoint_field_diff_v1 import fingerprint, instant
from verify_development_checkpoint_v2 import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('measurement', type=Path)
    args = parser.parse_args()
    base = verify(args.measurement)
    if base['status'] != 'read_only_checkpoint_observations_verified':
        raise ValueError('Diagnostic did not complete')
    result = json.loads(args.measurement.read_text())
    phases = {r['phase']: r for r in result['phases']}
    verified = []
    reconstructed = []
    for first, second, name in [('seed','restore1','search_difference_from_seed'), ('seed','restore2','search_difference_from_seed'), ('restore1','restore2','search_difference_from_restore1')]:
        a = {(r['index'],r['id']):r['source'] for r in phases[first]['search_document_inventory']}
        b = {(r['index'],r['id']):r['source'] for r in phases[second]['search_document_inventory']}
        difference = phases[second][name]
        expected = {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
        reported = {(r['index'],r['id']) for r in difference['changed_documents']}
        if expected != reported or len(reported) != len(difference['changed_documents']):
            raise ValueError('Changed document coverage mismatch')
        if len(a)!=difference['before_documents'] or len(b)!=difference['after_documents']:
            raise ValueError('Document count mismatch')
        for row in difference['changed_documents']:
            key = row['index'],row['id']
            if key in a and row['before'] != a[key]:
                raise ValueError('Before document digest mismatch')
            if key in b and row['after'] != b[key]:
                raise ValueError('After document digest mismatch')
            if row['change']=='document_changed' and not row['fields']:
                raise ValueError('Missing field differences')
            for field in row.get('fields', []):
                target = field['path'].removeprefix('/')
                record = phases[second]['browser']['record']
                if row['index']!='user' or str(record['id'])!=row['id'] or target not in record or 'utc_instant_comparison' not in field:
                    continue
                after = record[target]
                if fingerprint(after)!=field['after']['sha256']:
                    raise ValueError('Timestamp differs from retained full admin record')
                parsed = instant(after)
                ns = parsed[0] - field['utc_instant_comparison']['after_minus_before_nanoseconds']
                seconds,fraction = divmod(ns,10**9)
                before = datetime.datetime.fromtimestamp(seconds,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
                digits = field['utc_instant_comparison']['before_fraction_digits']
                before += ('.'+str(fraction).zfill(9)[:digits] if digits else '')+'Z'
                if fingerprint(before)!=field['before']['sha256']:
                    raise ValueError('Reconstructed timestamp does not match source digest')
                reconstructed.append({'comparison':first+'->'+second,'index':row['index'],'id':row['id'],'path':field['path'],'both_hashes_reconstructed':True})
        verified.append({'comparison':first+'->'+second,'changed_documents':len(expected),'inventory_coverage_verified':True})
    print(json.dumps({'status':'retained_inventory_and_available_timestamp_hashes_verified', 'comparisons':verified,
                      'timestamp_hash_reconstructions':reconstructed,
                      'limits':'Raw search documents were not archived; other field differences retain the runtime comparator and tests as evidence.',
                      'measurement_sha256':hashlib.sha256(args.measurement.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':
    main()
