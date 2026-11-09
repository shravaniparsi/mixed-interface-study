#!/usr/bin/env python3
"""Reconstruct separate write measurements from independently verified backups."""
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_observations import measure
from verify_realworld_identity_database_archive import main as verify_archive


def replay():
    # Verification reopens all databases, validates trace ordering and source hashes.
    with redirect_stdout(sys.stderr):
        verify_archive()
    manifest = json.loads((ROOT / 'manifests/realworld-identity-database-integration.json').read_bytes())
    records = []
    for case in manifest['verification']['cases']:
        def observed(key):
            return {'state': 'observed', 'projection': {'username': case[key]}}
        intended = None if case['candidate_id'].endswith('null') else 'u' * int(case['candidate_id'].split('length')[1])
        result = measure(case['prefix_status'], observed('before_username'),
                         observed('immediate_username'), observed('after_restart_username'),
                         {'username': intended},
                         {phase + ':' + endpoint: {'state': 'response', 'status': status}
                          for phase, endpoints in case['readback_statuses'].items()
                          for endpoint, status in endpoints.items()})
        records.append({'candidate_id': case['candidate_id'], 'measurement': result,
                        'requirement_policy': case['requirement_policy']})
    return {'schema_version': 1, 'source_manifest': 'manifests/realworld-identity-database-integration.json',
            'source_commit': manifest['source_commit'], 'projection': ['username'],
            'scope': 'derived diagnostic replay; no dispatch, channel comparison or primary samples',
            'records': records}


if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))
