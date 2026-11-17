#!/usr/bin/env python3
"""Compose candidate syntax paths, never promote them into API obligations."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ['development-reactive-form-inventory-v1',
          'development-reactive-payload-inventory-v1',
          'development-service-http-inventory-v1', 'project-family-partition-v1']
OUTPUT = ROOT / 'manifests/development-lineage-v1.json'


def identity(row):
    return tuple(row[k] for k in ('full_name', 'commit', 'path', 'source_sha256'))


def compose(forms, payloads, services, allowed):
    rows = []
    for component in payloads['rows']:
        if component['full_name'] not in allowed:
            raise ValueError('Non-development input')
        matches = [r for r in forms['rows'] if identity(r) == identity(component)]
        if len(matches) != 1:
            raise ValueError('Component source identity absent or ambiguous')
        form_row = matches[0]
        calls = []
        for call in component['calls']:
            candidates = [(s, m) for s in services['rows']
                          if (s['full_name'], s['commit'], s['class_name']) ==
                          (component['full_name'], component['commit'], call['service_type'])
                          for m in s['methods'] if m['method'] == call['method']]
            result = {'component_call': call, 'service_candidate_count': len(candidates),
                      'status': 'service_candidate_absent_or_ambiguous', 'arguments': []}
            method = None
            if len(candidates) == 1:
                service, method = candidates[0]
                result.update(service_source={k: service[k] for k in
                              ('full_name', 'commit', 'path', 'source_sha256')},
                              service_method=method,
                              status='same_project_revision_class_name_candidate_only')
            for index, argument in enumerate(call['arguments']):
                direct = (method is not None and method['status'] ==
                          'direct_httpclient_parameter_syntax' and
                          method['body_parameter_index'] == index)
                fields, omitted = [], []
                def bind(source, payload_field):
                    fs = [f for f in form_row['forms'] if
                          f['binding'].removeprefix('this.') == source.get('form')]
                    cs = [c for f in fs for c in f['controls']
                          if c['field'] == source.get('field')]
                    bound = len(fs) == 1 and len(cs) == 1
                    return {'payload_field': payload_field, 'source': source,
                            'status': 'control_candidate' if bound else 'unresolved_control',
                            'control': cs[0] if bound else None,
                            'direct_body_parameter_candidate': direct and bound}
                if argument['kind'] == 'literal_payload':
                    fields = [bind(f['source'], f['payload_field']) for f in argument['fields']]
                    referenced = {f['source'].get('form') for f in fields}
                    used = {(f['source'].get('form'), f['source'].get('field')) for f in fields}
                    for form in form_row['forms']:
                        name = form['binding'].removeprefix('this.')
                        if name in referenced:
                            omitted.extend({'form': name, 'control': c,
                                            'meaning': 'absent_from_this_literal_not_irrelevant_to_guard'}
                                           for c in form['controls'] if (name, c['field']) not in used)
                elif argument['kind'] == 'form_snapshot':
                    fs = [f for f in form_row['forms'] if
                          f['binding'].removeprefix('this.') == argument['form']]
                    if len(fs) == 1:
                        fields = [bind(dict(argument, kind='form_field_read', field=c['field']),
                                       c['field']) for c in fs[0]['controls']]
                result['arguments'].append({'index': index, 'argument': argument,
                    'fields': fields, 'controls_absent_from_literal': omitted,
                    'snapshot_membership': 'runtime_activity_and_materialization_unresolved'
                    if argument['kind'] == 'form_snapshot' else 'not_a_snapshot'})
            calls.append(result)
        rows.append({'component_source': {k: component[k] for k in
                     ('full_name', 'commit', 'path', 'source_sha256')}, 'calls': calls,
                     'no_calls_meaning': 'extractor_coverage_not_absence_of_submission',
                     'unresolved': sorted(set(form_row.get('unqualified', []) +
                                             component.get('unqualified', [])))})
    return {'kind': 'development_candidate_syntax_lineage', 'rows': rows,
            'limits': ['Class-name match does not resolve imports or runtime injection.',
                       'Lexical guards are retained, not proved preconditions.',
                       'Snapshot controls need not be materialized or enabled.',
                       'Body object fields need not survive JSON serialization.',
                       'Frontend declarations are not independent API contracts.'],
            'complete_api_rules': 0, 'independent_evaluation_cases': 0}


def build():
    raw = [(ROOT / ('manifests/' + name + '.json')).read_bytes() for name in INPUTS]
    forms, payloads, services, partition = map(json.loads, raw)
    allowed = {r['full_name'] for r in partition['rows'] if r['partition'] == 'development'}
    if any(r['full_name'] not in allowed for d in (forms, payloads, services) for r in d['rows']):
        raise ValueError('Reserved or unknown project input')
    result = compose(forms, payloads, services, allowed)
    result['inputs'] = {name: hashlib.sha256(data).hexdigest() for name, data in zip(INPUTS, raw)}
    return json.dumps(result, indent=2) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    output = build()
    if args.verify:
        if OUTPUT.read_text() != output:
            raise SystemExit('Lineage differs from inputs')
        print('Lineage verified')
    else:
        OUTPUT.write_text(output)
        print(OUTPUT)
