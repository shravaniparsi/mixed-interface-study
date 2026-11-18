"""Qualify only the observed Swagger 2 ApplicationParams keyword subset.

No business-input variants are evaluated here. Calibration uses an unrelated
synthetic schema; the unchanged ordinary request is checked against original
source. Unsupported keywords fail closed instead of being silently discarded.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from jsonschema import Draft4Validator, FormatChecker

SOURCE_HASH = '0c6c716af3498ca26b06a03e1a96dff79ec98c56d2e2da2e79ff6bf191533b6c'
checker = FormatChecker()


@checker.checks('int64')
def int64(value):
    return not isinstance(value, int) or isinstance(value, bool) or -(2**63) <= value < 2**63


def original_schema(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_HASH:
        raise ValueError('Original schema identity mismatch')
    document = json.loads(raw)
    assert document['swagger'] == '2.0'
    body = [p for p in document['paths']['/application']['post']['parameters'] if p['in'] == 'body']
    assert len(body) == 1 and body[0]['required'] is True
    assert body[0]['schema'] == {'$ref': '#/definitions/ApplicationParams'}
    schema = document['definitions']['ApplicationParams']
    assert set(schema) <= {'description', 'type', 'title', 'required', 'properties', 'x-go-package'}
    assert schema['type'] == 'object'
    for property_schema in schema['properties'].values():
        assert set(property_schema) <= {'description', 'type', 'format', 'x-go-name', 'example'}
        assert property_schema['type'] in {'string', 'integer'}
        if 'format' in property_schema:
            assert property_schema['type'] == 'integer' and property_schema['format'] == 'int64'
    Draft4Validator.check_schema(schema)
    return schema


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit('Refusing repeated qualification output')
    assert importlib.metadata.version('jsonschema') == '4.26.0'
    schema = original_schema(args.source)
    calibration = {'type': 'object', 'required': ['text'], 'properties': {
        'text': {'type': 'string'}, 'count': {'type': 'integer', 'format': 'int64'}}}
    cases = [({'text': ''}, True), ({}, False), ({'text': None}, False),
             ({'text': 'x', 'count': True}, False), ({'text': 'x', 'count': 0}, True),
             ({'text': 'x', 'count': 2**63}, False),
             ({'text': 'x', 'count': -(2**63)}, True),
             ({'text': 'x', 'extra': 'allowed'}, True)]
    validator = Draft4Validator(calibration, format_checker=checker)
    outcomes = []
    for value, expected in cases:
        observed = validator.is_valid(value)
        outcomes.append({'input': value, 'expected': expected, 'observed': observed})
        assert observed == expected
    ordinary = {'name': 'Study application', 'description': 'Study description', 'defaultPriority': 0}
    Draft4Validator(schema, format_checker=checker).validate(ordinary)
    result = {'status': 'qualified_for_observed_keyword_subset', 'source_sha256': SOURCE_HASH,
              'version': importlib.metadata.version('jsonschema'), 'dialect': 'Swagger 2 observed Draft4-compatible subset',
              'body_reference': '#/definitions/ApplicationParams', 'schema': schema,
              'calibration': outcomes, 'ordinary_valid': True, 'scientific_variants_evaluated': 0,
              'limitations': 'Not a general Swagger 2 validator; unknown validation keywords or reference shapes fail closed.'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
