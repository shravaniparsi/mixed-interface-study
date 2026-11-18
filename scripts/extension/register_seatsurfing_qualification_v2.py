#!/usr/bin/env python3
"""Freeze the single permitted root-tree instrumentation correction."""
import argparse
import hashlib
import json
from pathlib import Path
from register_seatsurfing_qualification_v1 import registration as original_registration, ROOT

OUT=ROOT/'manifests/catalog-seatsurfing-qualification-v2.json'


def registration():
    value=original_registration()
    value['script_sha256'].pop(str(OUT.relative_to(ROOT)),None)
    value.update(qualification_attempt=2,workflow='.github/workflows/catalog_seatsurfing_ordinary_v2.yml',
        correction='root_tree_identity_from_frozen_recursive_entries_not_metadata_locator',
        previous_attempt_run_id=44347763330,remaining_attempts_after_this_job=0)
    paths=[ROOT/'.github/workflows/catalog_seatsurfing_ordinary_v2.yml',
           ROOT/'manifests/catalog-seatsurfing-qualification-v1.json']
    paths+=list((ROOT/'results/catalog-seatsurfing-ordinary-v1-ci-44347763330').rglob('*.json'))
    for path in paths:
        if path.is_file():value['script_sha256'][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    value['script_sha256']=dict(sorted(value['script_sha256'].items()))
    return value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    raw=(json.dumps(registration(),indent=2)+'\n').encode()
    if args.verify:
        if OUT.read_bytes()!=raw:raise ValueError('Second-attempt frozen inputs differ')
        print('Second and final SeatSurfing registration verified; no application executed.')
    else:OUT.write_bytes(raw)


if __name__=='__main__':main()
