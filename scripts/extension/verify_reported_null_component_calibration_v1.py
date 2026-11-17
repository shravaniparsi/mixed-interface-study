"""Recompute calibration coverage/comparison from saved rows; does not rerun applications."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / 'results/reported-null-component-calibration-v1'

def main():
    data = json.loads((DIR / 'measurement.json').read_text())
    execution = json.loads((DIR / 'execution.json').read_text())
    assert execution['returncode'] == 0 and execution['measurement_attempts'] == 1
    assert execution['freeze'].startswith('825ae87')
    assert data['node'] == 'v16.13.2' and data['mongoose'] == '4.7.1'
    assert data['dependency_lock_sha256'] == hashlib.sha256((DIR / 'package-lock.json').read_bytes()).hexdigest()
    admission = json.loads((ROOT / 'manifests/reported-interface-fault-admission-v1.json').read_text())
    for item in data['source_provenance']:
        source = next(x for x in admission['evidence'] if x['file'] == item['file'])
        assert item['response_sha256'] == source['sha256'] and item['endpoint'] == source['endpoint']
    assert {x['file'] for x in data['source_provenance']} == {'17.json', '21.json', '24.json', '25.json'}
    inputs = {'omitted', 'null', 'empty_array', 'one_array', 'empty_string', 'one_string'}
    rows = data['records']
    assert len(rows) == 12
    assert {(x['schema_version'], x['input']) for x in rows} == {(s, i) for s in ('before', 'after') for i in inputs}
    throws = {'before': 0, 'after': 0}
    escaped = {'nonnull': 0, 'array': 0}
    flags = {'nonnull': 0, 'array': 0}
    flags_without_exception = {'before': {'nonnull': 0, 'array': 0}, 'after': {'nonnull': 0, 'array': 0}}
    for row in rows:
        state = row['serialized']
        predicates = {'nonnull': 'setup' in state and state['setup'] is not None, 'array': isinstance(state.get('setup'), list)}
        assert row['predicates'] == predicates
        assert set(row['constructors']) == {'before', 'after'}
        for k, passed in predicates.items(): flags[k] += not passed
        for version, result in row['constructors'].items():
            assert isinstance(result['threw'], bool)
            throws[version] += result['threw']
            for k, passed in predicates.items():
                escaped[k] += result['threw'] and passed
                flags_without_exception[version][k] += not result['threw'] and not passed
    summary = dict(scope=data['scope'], schema_observations=12, constructor_combinations=24,
        reported_fault_clusters=1, independent_application_admissions=0,
        constructor_exceptions=throws, schema_predicate_flags=flags,
        constructor_exceptions_escaping_predicate=escaped,
        predicate_flags_without_constructor_exception=flags_without_exception,
        warning='Flags without exceptions are disagreement, not established false positives; constructor non-throw is not full correctness.')
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == '__main__':
    main()
