#!/usr/bin/env python3
"""Verify retained diagnostic backups, independent projections, and the failed setup attempt."""
import json
from pathlib import Path
from validate_realworld_identity_database_diagnostic import validate,require
from realworld_identity_db_state_v1 import sha
ROOT=Path(__file__).resolve().parents[1]


def verify_inventory(manifest):
    d=ROOT/manifest['evidence_directory'];files={str(p.relative_to(d)):p for p in d.rglob('*') if p.is_file()}
    require(set(files)==set(manifest['input_sha256']),'Retained archive inventory differs')
    for name,p in files.items():require(sha(p)==manifest['input_sha256'][name],'Retained file hash differs: '+name)
    return d


def main():
    failure=json.loads((ROOT/'manifests/realworld-identity-db-fixture-failure.json').read_bytes());failed=verify_inventory(failure)
    require(failure['qualified'] is False and failure['candidate_prefix_writes']==0,'Failed setup qualification differs')
    require(json.loads((failed/'report.json').read_bytes())['cases']==[],'Unexpected candidate in failed setup')
    manifest=json.loads((ROOT/'manifests/realworld-identity-database-integration.json').read_bytes());directory=verify_inventory(manifest)
    observed=validate(directory)
    require(observed==manifest['verification'] and observed==json.loads((directory/'verification.json').read_bytes()),'Diagnostic reconstruction differs')
    require(observed['source_commit']==manifest['source_commit'],'Execution commit differs')
    require(manifest['primary_freeze_complete'] is False and manifest['new_primary_samples']==0,'Diagnostic promoted into primary evidence')
    print('Verified three isolated database diagnostics and thirteen retained SQLite backups; prior failed setup remains unqualified.')


if __name__=='__main__':main()
