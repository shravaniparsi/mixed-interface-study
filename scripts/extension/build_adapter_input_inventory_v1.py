#!/usr/bin/env python3
"""Freeze source-defined inputs independently of converter implementation/schema."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'evidence/openapi-adapter-inputs-v1'
DEFAULTS = {'label': 'new', 'enabled': True, 'quota': 7, 'tags': ['default'], 'metadata': {'owner': 'new', 'flags': {}}}
SEED = {'label': 'seed', 'enabled': True, 'quota': 7, 'tags': ['seed', 'tail'], 'metadata': {'owner': 'seed', 'flags': {'pinned': True, 'audit': False}}}
SIBLING = {'label': 'untouched', 'enabled': False, 'quota': 99, 'tags': [], 'metadata': {}}


def merge_patch(target, patch):
    # Independently written implementation of the declared RFC 7396 object rules.
    if not isinstance(patch, dict):
        return deepcopy(patch)
    result = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def build():
    boolean = {'type': 'boolean', 'nullable': True}
    props = {
        'label': {'type': 'string', 'nullable': True},
        'enabled': deepcopy(boolean),
        'quota': {'type': 'integer', 'nullable': True, 'minimum': 0, 'maximum': 100},
        'tags': {'type': 'array', 'nullable': True, 'items': {'type': 'string'}},
        'metadata': {'type': 'object', 'nullable': True, 'additionalProperties': False, 'properties': {
            'owner': {'type': 'string', 'nullable': True},
            'flags': {'type': 'object', 'nullable': True, 'additionalProperties': False,
                      'properties': {'pinned': deepcopy(boolean), 'audit': deepcopy(boolean)}}}},
    }
    patch_schema = {'type': 'object', 'additionalProperties': False, 'properties': props}
    create_schema = deepcopy(patch_schema)
    for name, value in DEFAULTS.items():
        create_schema['properties'][name]['default'] = deepcopy(value)
    response = {'description': 'Persisted resource and stable identifier.', 'content': {'application/json': {'schema': {'type': 'object', 'required': ['id', 'data'], 'properties': {'id': {'type': 'string'}, 'data': deepcopy(patch_schema)}, 'additionalProperties': False}}}}
    spec = {'openapi': '3.0.3', 'info': {'title': 'Controlled write-preservation feasibility fixture', 'version': '1.0.0'},
            'servers': [{'url': 'http://127.0.0.1:8765'}], 'paths': {
        '/records': {'post': {'operationId': 'create_record', 'description': 'Create a new record. Omitted top-level fields receive declared server defaults. Present values including null, false, zero, empty containers and empty strings are preserved. Nested objects are not populated with additional defaults.',
                             'requestBody': {'required': True, 'content': {'application/json': {'schema': create_schema}}}, 'responses': {'201': deepcopy(response)}}},
        '/records/{record_id}': {'parameters': [{'name': 'record_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
            'patch': {'operationId': 'patch_record', 'description': 'Update an existing record using JSON Merge Patch object semantics. Missing members are unchanged; null removes a member; objects merge recursively; arrays and scalars replace. No default values are inserted. This fixture accepts the same algorithm under both declared media types.',
                      'requestBody': {'required': True, 'content': {mime: {'schema': deepcopy(patch_schema)} for mime in ['application/merge-patch+json', 'application/json']}}, 'responses': {'200': deepcopy(response)}},
            'get': {'operationId': 'read_record', 'description': 'Read the persisted resource.', 'responses': {'200': deepcopy(response)}}},
    }}
    payloads = [
        ('empty', {}), ('label-null', {'label': None}), ('label-empty', {'label': ''}), ('label-ordinary', {'label': 'ordinary'}),
        ('enabled-null', {'enabled': None}), ('enabled-false', {'enabled': False}), ('enabled-true', {'enabled': True}),
        ('quota-null', {'quota': None}), ('quota-zero', {'quota': 0}), ('quota-positive', {'quota': 3}),
        ('tags-null', {'tags': None}), ('tags-empty', {'tags': []}), ('tags-ordered', {'tags': ['first', 'second']}), ('tags-reversed', {'tags': ['second', 'first']}),
        ('metadata-null', {'metadata': None}), ('metadata-empty', {'metadata': {}}),
        ('nested-owner-null', {'metadata': {'owner': None}}), ('nested-owner-ordinary', {'metadata': {'owner': 'ordinary'}}),
        ('nested-flags-empty', {'metadata': {'flags': {}}}), ('nested-flags-null', {'metadata': {'flags': None}}),
        ('nested-pinned-false', {'metadata': {'flags': {'pinned': False}}}), ('nested-audit-true', {'metadata': {'flags': {'audit': True}}}),
        ('mixed-falsy', {'label': '', 'enabled': False, 'quota': 0, 'tags': [], 'metadata': {}}),
        ('all-ordinary', {'label': 'ordinary', 'enabled': True, 'quota': 3, 'tags': ['one'], 'metadata': {'owner': 'ordinary', 'flags': {'pinned': False, 'audit': True}}}),
    ]
    cases = []
    for operation in ['create_record', 'patch_record']:
        for name, payload in payloads:
            initial = {'seed': deepcopy(SEED), 'sibling': deepcopy(SIBLING)}
            final = deepcopy(initial)
            target = 'created' if operation == 'create_record' else 'seed'
            final[target] = {**deepcopy(DEFAULTS), **deepcopy(payload)} if operation == 'create_record' else merge_patch(SEED, payload)
            cases.append({'id': operation + ':' + name, 'operation_id': operation, 'body': payload,
                          'path_parameters': {} if operation == 'create_record' else {'record_id': 'seed'},
                          'initial_records': initial, 'target_id': target, 'expected_records': final})
    assert len(cases) == 48 and len({r['id'] for r in cases}) == 48
    value = {'kind': 'openapi_adapter_source_input_inventory_v1', 'source_fixture': 'synthetic_author_controlled',
             'converter_outcomes_observed': False, 'pinned_converter_source_inspected': False,
             'selection': 'Complete fixed purposive value-family enumeration; not production-distribution sampling.',
             'independent_real_application_evidence': False, 'application_execution_authorized': False,
             'standard_schema_validator_check': 'pending independent validation before application dispatch',
             'operation_count': 2, 'source_case_count': len(cases), 'selected_converters': 3,
             'potential_initial_scientific_pairs': 144, 'qualification_and_repeat_schedule_frozen': False,
             'schema_sha256': hashlib.sha256((json.dumps(spec, indent=2) + '\n').encode()).hexdigest(), 'cases': cases}
    return spec, value


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    spec, inventory = build()
    for path, value in [(BASE / 'openapi.json', spec), (ROOT / 'manifests/openapi-adapter-input-inventory-v1.json', inventory)]:
        if args.verify:
            assert json.loads(path.read_text()) == value
        else:
            assert not path.exists(); path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in inventory.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
