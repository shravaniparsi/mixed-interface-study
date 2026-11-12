#!/usr/bin/env python3
"""Independent standards-based validation of the frozen OpenAPI experiment input."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from jsonschema.exceptions import ValidationError
from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]


def build():
    spec_path = ROOT / 'evidence/openapi-adapter-inputs-v1/openapi.json'
    inputs_path = ROOT / 'manifests/openapi-adapter-input-inventory-v1.json'
    spec = json.loads(spec_path.read_text()); inputs = json.loads(inputs_path.read_text())
    validate_spec(spec)
    operations = {}
    for item in spec['paths'].values():
        for method, operation in item.items():
            if method not in ['post', 'patch']:
                continue
            assert operation['operationId'] not in operations
            operations[operation['operationId']] = operation
    validated = []; expected_objects = 0
    for row in inputs['cases']:
        operation = operations[row['operation_id']]
        schemas = [v['schema'] for v in operation['requestBody']['content'].values()]
        for schema in schemas:
            OAS30Validator(schema).validate(row['body'])
        response = next(iter(operation['responses'].values()))['content']['application/json']['schema']
        for identity, data in row['expected_records'].items():
            OAS30Validator(response).validate({'id': identity, 'data': data})
            expected_objects += 1
        validated.append(row['id'])
    # These controls must fail independently of the study's own generator/checker.
    negatives = [
        {'quota': False}, {'quota': -1}, {'unexpected': 1}, {'tags': ['ok', 7]},
        {'metadata': {'flags': {'pinned': 'false'}}}, {'label': 0},
    ]
    negative_results = []
    for name, operation in sorted(operations.items()):
        schema = operation['requestBody']['content']['application/json']['schema']
        for value in negatives:
            try:
                OAS30Validator(schema).validate(value)
            except ValidationError:
                negative_results.append({'operation_id': name, 'body': value, 'rejected': True})
            else:
                raise AssertionError(('validator accepted invalid control', name, value))
    return {'kind': 'openapi_adapter_input_validation_v1', 'specification_valid': True,
            'source_valid_case_count': len(validated), 'source_valid_case_ids': validated,
            'expected_state_objects_validated': expected_objects, 'negative_validator_controls': negative_results,
            'versions': {name: importlib.metadata.version(name) for name in ['openapi-spec-validator', 'openapi-schema-validator', 'jsonschema']},
            'input_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [spec_path, inputs_path]},
            'application_executions': 0, 'converter_compatibility_established': False}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(); path = ROOT / 'manifests/openapi-adapter-input-validation-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        assert not path.exists(); path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ['source_valid_case_ids', 'negative_validator_controls']}, indent=2))


if __name__ == '__main__':
    main()
