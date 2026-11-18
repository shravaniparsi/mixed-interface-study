#!/usr/bin/env python3
"""Materialize the prospective input schedule; never execute producer/schema/UI."""
import argparse
import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'manifests/catalog-seatsurfing-input-schedule-v1.json'

def expected():
    ordinary = {'name': 'Study area', 'description': 'Study description',
                'maxConcurrentBookings': 0, 'timezone': '', 'enabled': True,
                'mapScale': 1, 'mapType': '', 'allowedBookerGroupIds': [],
                'bookableDays': [], 'blockedFrom': '', 'blockedUntil': '',
                'announcement': 'Study notice'}
    paths = ['/announcement', '/description', '/name']
    edits = {'/announcement': 'Edit notice', '/description': 'Edit description'}
    cases = [{'id': 'ordinary', 'kind': 'ordinary', 'producer': copy.deepcopy(ordinary),
              'edit': {'path': '/description', 'value': edits['/description']}}]
    for path in paths:
        unrelated = next(p for p in paths if p != path)
        for kind in ['omit', 'null']:
            payload = copy.deepcopy(ordinary)
            if kind == 'omit': del payload[path[1:]]
            else: payload[path[1:]] = None
            cases.append({'id': path[1:] + '-' + kind, 'kind': kind, 'target_path': path,
                          'producer': payload, 'edit': {'path': unrelated, 'value': edits[unrelated]}})
    return {'repository': 'seatsurfing/seatsurfing', 'revision': '9953f452324bab6fb8f7106dd8965cc401aa456c',
            'workflow': 'admin_location_create_edit', 'status': 'prospective_inputs_only_runtime_unqualified',
            'selection_basis': 'first_mapped_supported_location_workflow_with_retained_candidate_dispositions_not_exhaustive_first_eligible_claim',
            'native_form_path': 'ui/src/pages/admin/locations/[id].tsx',
            'producer_method': 'POST', 'producer_path': '/location/', 'continuation_method': 'PUT', 'continuation_path': '/location/{persisted_id}',
            'eligible_scalar_text_paths_utf8': paths,
            'excluded_control_types': {'timezone': 'select', 'blockedFrom': 'date', 'blockedUntil': 'date', 'mapType': 'enum', 'allowedBookerGroupIds': 'entity_selection', 'bookableDays': 'day_selection'},
            'ordinary_required_edit_paths': ['/announcement', '/description'],
            'ordinary': ordinary, 'cases': cases, 'maximum_scientific_jobs_if_qualified': len(cases),
            'qualification_jobs_dispatched': 0, 'scientific_cases_executed': 0,
            'correlated_variants_are_independent_defects': False,
            'runtime_authorized': False}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    raw = json.dumps(expected(), indent=2) + '\n'
    if args.verify:
        assert OUT.read_text() == raw
        print('Seven prospective cases verified; no execution authorized.')
    else:
        if OUT.exists(): raise ValueError('Refuse schedule overwrite')
        OUT.write_text(raw)
        print('Prepared one ordinary and six correlated omit/null cases; none executed.')

if __name__ == '__main__': main()
