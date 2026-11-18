#!/usr/bin/env python3
"""Freeze nine prospective producer inputs; performs no application requests."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '20016b9d91d49c9133f1b4d26ab5a289c72ec1db'
OUTPUT = ROOT / 'manifests/catalog-nginx-input-schedule-v1.json'
PROPERTIES = ['/clients/0/address', '/items/0/password', '/items/0/username', '/name']
ORDINARY = {
    'name': 'Study Control', 'satisfy_any': False, 'pass_auth': False,
    'items': [{'username': 'studycontrol', 'password': 'Study-Only-Control-2026'}],
    'clients': [{'directive': 'allow', 'address': '192.0.2.10'}],
}
EDITS = {
    '/clients/0/address': '192.0.2.11',
    '/items/0/password': 'Study-Only-Edited-2026',
}


def mutate(pointer, operation):
    assert pointer in PROPERTIES and operation in ('omit', 'null')
    body = deepcopy(ORDINARY)
    parts = pointer.lstrip('/').split('/')
    parent = body
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    assert parts[-1] in parent
    if operation == 'omit':
        del parent[parts[-1]]
    else:
        parent[parts[-1]] = None
    return body


def source_identity(wave, sequence):
    directory = ROOT / f'results/catalog-source-wave{wave}-v1'
    rows = json.loads((directory / 'collection.json').read_text())['rows']
    row, = [r for r in rows if r['sequence'] == sequence]
    assert row['revision'] == REVISION
    digest = hashlib.sha256((directory / row['file']).read_bytes()).hexdigest()
    assert digest == row['sha256']
    return {'artifact': str((directory / row['file']).relative_to(ROOT)), 'sha256': digest}


def build():
    assert PROPERTIES == sorted(PROPERTIES, key=lambda s: s.encode('utf-8'))
    edit_for = {p: next(q for q in PROPERTIES if q != p) for p in PROPERTIES}
    ordinary_edits = [{'path': p, 'value': EDITS[p]} for p in sorted(set(edit_for.values()))]
    cases = [{'case': 'ordinary', 'mutation': None, 'producer_body': deepcopy(ORDINARY),
              'independent_continuations': ordinary_edits}]
    for pointer in PROPERTIES:
        for operation in ('omit', 'null'):
            edit = edit_for[pointer]
            cases.append({
                'case': pointer.strip('/').replace('/', '-') + '-' + operation,
                'mutation': {'pointer': pointer, 'operation': operation},
                'producer_body': mutate(pointer, operation),
                'independent_continuations': [{'path': edit, 'value': EDITS[edit]}],
            })
    assert len(cases) == 9 and len({c['case'] for c in cases}) == 9
    return {
        'repository': 'nginxproxymanager/nginx-proxy-manager', 'revision': REVISION,
        'status': 'inputs_frozen_runtime_not_authorized',
        'candidate': 'frontend/src/modals/AccessListModal.tsx',
        'workflow_runtime_qualified': False,
        'supported_properties': PROPERTIES,
        'excluded_controls': {
            '/clients/0/directive': 'categorical select, not a text input',
            '/satisfy_any': 'boolean toggle', '/pass_auth': 'boolean toggle',
            'clients[last]': 'disabled display-only deny/all row',
        },
        'source_identities': [source_identity(w, s) for w, s in
                              [(2, 33), (3, 25), (3, 26), (3, 28), (18, 6)]],
        'producer': {'method': 'POST', 'path': '/api/nginx/access-lists'},
        'cases': cases,
        'max_scientific_jobs': 9, 'max_minutes_per_scientific_job': 15,
        'ordinary_policy': 'Both edits independently from the same checkpoint; one producer input/job.',
        'schema_policy': 'Original schema/engine/settings; validate a clone, preserve coercions.',
        'password_policy': 'Masked readback retained unless password is the explicit unrelated edit.',
        'counting': 'Nine correlated inputs in one workflow; not independent defects.',
        'outcome_based_replacement_or_retry': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    content = json.dumps(build(), indent=2) + '\n'
    if args.verify:
        assert OUTPUT.read_text() == content, 'Frozen input schedule differs'
    else:
        assert not OUTPUT.exists(), 'Do not overwrite a frozen input schedule'
        OUTPUT.write_text(content)
    print('Nine prospective inputs verified; no application or schema executed.')


if __name__ == '__main__':
    main()
