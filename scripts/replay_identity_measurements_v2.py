#!/usr/bin/env python3
"""Verify the halted archive, then replay separate paired branch measurements."""
import json
import sys
from pathlib import Path
from contextlib import redirect_stdout
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from verify_realworld_identity_halted_archive import main as verify_archive
from realworld_identity_campaign import read
from realworld_identity_measurement_loader_v2 import read_job


def replay():
    with redirect_stdout(sys.stderr):
        verify_archive()
    manifest = read(ROOT / 'manifests/realworld-identity-halted-integration.json')
    directory = ROOT / manifest['evidence_directory']
    registry = read(directory / 'sources/manifests/realworld-identity-controls-v1.json')
    rows = []
    for path in sorted(directory.glob('initial-*')):
        row = read_job(path, read(path / 'job.json'), registry, read(path / 'execution.json'))
        if row['legacy_result'] != read(path / 'observations.json'):
            raise ValueError('Replay changed an archived terminal result')
        if set(row['measurements']) != {'api', 'ui'} or not all(m['qualified'] for m in row['measurements'].values()):
            raise ValueError('Branch measurement qualification failed: ' + json.dumps(row['measurements']))
        rows.append(row)
    return {'schema_version': 2, 'source_commit': manifest['source_commit'],
            'source_manifest': 'manifests/realworld-identity-halted-integration.json',
            'application_executions_added': 0, 'new_primary_samples': 0,
            'dispatch_authorized': False, 'pairs': rows}


if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))
