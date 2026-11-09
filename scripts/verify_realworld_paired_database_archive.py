#!/usr/bin/env python3
"""Reopen the retained v7 paired database diagnostic and verify its complete inventory."""
from pathlib import Path
import json
from validate_realworld_paired_database_v7 import validate
from realworld_identity_db_state_v1 import sha
ROOT=Path(__file__).resolve().parents[1]


def verify():
    manifest=json.loads((ROOT/'manifests/realworld-paired-database-integration.json').read_bytes())
    directory=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(manifest['input_sha256']):raise ValueError('Archive inventory differs')
    for name,path in files.items():
        if sha(path)!=manifest['input_sha256'][name]:raise ValueError('Archive bytes differ: '+name)
    observed=validate(directory)
    if observed!=manifest['verification'] or observed!=json.loads((directory/'verification.json').read_bytes()):
        raise ValueError('Independent paired reconstruction differs')
    if observed['source_commit']!=manifest['source_commit'] or manifest['new_primary_samples']!=0 or manifest['primary_freeze_complete'] is not False:
        raise ValueError('Execution identity or diagnostic scope differs')
    return observed


if __name__=='__main__':
    observed=verify()
    print('Verified',observed['pairs'],'paired diagnostics,',observed['branches'],'branches and',observed['database_backups'],'branch-local backups; primary freeze remains open.')
