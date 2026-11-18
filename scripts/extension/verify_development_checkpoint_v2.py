#!/usr/bin/env python3
"""Recompute checkpoint comparisons from retained runtime observations."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(path):
    record = json.loads(path.read_text())
    if record['kind'] != 'ordinary_development_checkpoint_qualification':
        raise ValueError('Wrong measurement kind')
    if record['independent_evaluation_cases'] != 0:
        raise ValueError('Development observations cannot add independent cases')
    if record['status'] != 'measurement_complete':
        return {'status': 'qualification_failed', 'error_type': record.get('error_type'),
                'error': record.get('error'), 'phases_started': [p['phase'] for p in record.get('phases', [])],
                'continuation_equivalence_qualified': False}
    phases = record['phases']
    if [p['phase'] for p in phases] != ['seed', 'restore1', 'restore2']:
        raise ValueError('Incorrect phase coverage')
    if record['snapshot']['snapshot']['state'] != 'SUCCESS' or record['snapshot']['snapshot']['shards']['failed'] != 0:
        raise ValueError('Incomplete snapshot')
    if len(record['restores']) != 2 or not record['checkpoint_relational_files']:
        raise ValueError('Checkpoint coverage missing')
    for restoration in record['restores']:
        if not restoration['relational_bytes_match_before_startup'] or restoration['response']['snapshot']['shards']['failed'] != 0:
            raise ValueError('Restore failed')
    for phase in phases:
        raw = json.loads((path.parent / (phase['phase'] + '-browser.json')).read_text())
        if raw != phase['browser'] or raw['status'] != 'observed':
            raise ValueError('Browser observation mismatch')
        expected = {'authenticate': 1, 'create': int(phase['phase'] == 'seed')}
        if raw['write_counts'] != expected or not raw['save_enabled']:
            raise ValueError('Unexpected browser writes or editor observation')
        if not all(r['method'] == 'GET' and r['origin'] == 'https://fonts.googleapis.com' and r['path'] == '/css2' for r in raw['blocked']):
            raise ValueError('Unexpected blocked request')
        if phase['shutdown_code'] not in (0, 143, -15):
            raise ValueError('Unexpected shutdown')
    seed = phases[0]
    comparisons = []
    for phase in phases[1:]:
        comparisons.append({'phase': phase['phase'],
            'full_admin_record_equal': phase['browser']['record'] == seed['browser']['record'],
            'actor_equal': phase['browser']['actor'] == seed['browser']['actor'],
            'native_form_equal': phase['browser']['loaded'] == seed['browser']['loaded'],
            'save_availability_equal': phase['browser']['save_enabled'] == seed['browser']['save_enabled'],
            'logical_search_contents_equal': phase['search'] == seed['search']})
    if comparisons != record['comparisons']:
        raise ValueError('Saved comparisons do not match observations')
    if record['continuation_equivalence_qualified'] is not False:
        raise ValueError('Read-only observations cannot qualify edit outcomes')
    return {'status': 'read_only_checkpoint_observations_verified', 'comparisons': comparisons,
            'continuation_equivalence_qualified': False,
            'independent_evaluation_cases': 0,
            'measurement_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('measurement', type=Path)
    args = p.parse_args()
    print(json.dumps(verify(args.measurement), indent=2))
