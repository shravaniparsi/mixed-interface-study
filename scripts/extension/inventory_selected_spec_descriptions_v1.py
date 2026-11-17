#!/usr/bin/env python3
"""Inventory existing spec evidence; never infer correctness from missing prose."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/development-spec-startup-v2-ci-44089249914/openapi.body'
EXPECTED = '2c8546ccc3d04eb7166aec4a10aea1434a89a25ea3f78188bd3df5d0b8231af1'

def inventory():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    spec = json.loads(raw)
    def resolve(ref):
        assert ref.startswith('#/'), 'External reference not permitted'
        node = spec
        for key in ref[2:].split('/'):
            node = node[key.replace('~1', '/').replace('~0', '~')]
        return node
    def walk(node, pointer, seen, descriptions):
        if isinstance(node, dict):
            if 'description' in node:
                descriptions.append({'location': pointer + '/description', 'value': node['description']})
            if '$ref' in node and node['$ref'] not in seen:
                ref = node['$ref']
                walk(resolve(ref), ref, seen | {ref}, descriptions)
            for key, value in node.items():
                if key != '$ref':
                    walk(value, pointer + '/' + key.replace('~', '~0').replace('/', '~1'), seen, descriptions)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, pointer + '/' + str(i), seen, descriptions)
    rows = []
    for path, method in [('/api/register','post'),('/api/admin/users','post'),('/api/admin/users','put')]:
        operation = spec['paths'][path][method]
        request_descriptions, response_descriptions = [], []
        walk(operation.get('requestBody', {}), 'requestBody', set(), request_descriptions)
        walk(operation.get('responses', {}), 'responses', set(), response_descriptions)
        rows.append({'path': path, 'method': method, 'operationId': operation['operationId'],
                     'request_descriptions': request_descriptions, 'response_descriptions': response_descriptions,
                     'response_content': {status: list(response.get('content', {})) for status,response in operation['responses'].items()}})
    return {'kind': 'selected_spec_description_inventory', 'spec_sha256': EXPECTED, 'operations': rows,
            'baseline_executed': False, 'model_calls': 0, 'independent_evaluation_cases': 0}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'manifests/selected-spec-description-inventory-v1.json'
    result = inventory()
    if args.verify:
        assert json.loads(output.read_text()) == result
        print('Selected specification description inventory verified.')
    else:
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
