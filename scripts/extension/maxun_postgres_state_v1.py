"""Read-only logical state export; callers must freeze comparison coverage.

Physical volume snapshots remain authoritative for sequences/schema/files.
This exports all user-table row values in one repeatable-read transaction.
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path

SQL = Path(__file__).with_suffix('.sql')


def exact_value(value):
    """Type-tag every JSON node; decimal tokens never pass through binary float."""
    if isinstance(value, Decimal):
        return ['number', str(value)]
    if value is None:
        return ['null']
    if isinstance(value, bool):
        return ['boolean', value]
    if isinstance(value, str):
        return ['string', value]
    if isinstance(value, list):
        return ['array', [exact_value(v) for v in value]]
    if isinstance(value, dict):
        return ['object', [[key, exact_value(value[key])] for key in sorted(value)]]
    raise ValueError('Unexpected JSON value')


def invalid_constant(value):
    raise ValueError('Non-JSON numeric constant: ' + value)


def parse_state(raw):
    tables = {}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip():
            continue
        exact = json.loads(line, parse_float=Decimal, parse_int=Decimal, parse_constant=invalid_constant)
        value = json.loads(line, parse_constant=invalid_constant)
        if set(value) != {'schema', 'table', 'rows'}:
            raise ValueError('Unexpected table-state record')
        if not isinstance(value['schema'], str) or not isinstance(value['table'], str):
            raise ValueError('Invalid relation identity')
        if not isinstance(value['rows'], list) or any(not isinstance(row, dict) for row in value['rows']):
            raise ValueError('Incomplete row-value export')
        key = (value['schema'], value['table'])
        if key in tables:
            raise ValueError('Duplicate relation export')
        value['exact_rows'] = exact_value(exact['rows'])
        tables[key] = value
    if not tables:
        raise ValueError('No application tables exported')
    return {'source_sha256': hashlib.sha256(raw).hexdigest(),
            'comparison_field': 'exact_rows',
            'rows_are_diagnostic_only': True,
            'tables': [tables[key] for key in sorted(tables)],
            'schema_and_sequences_included': False,
            'comparison_coverage_qualified': False}


def read_state(command, container):
    # command is the harness deadline-bound subprocess runner. No shell or
    # interpolated SQL; values and identifiers are quoted by PostgreSQL format.
    result = command(['docker', 'exec', '-i', container, 'psql', '--no-psqlrc',
                      '--quiet', '--tuples-only', '--no-align',
                      '--username=study', '--dbname=study', '--file=-'],
                     input=SQL.read_bytes(), capture_output=True)
    return parse_state(result.stdout)
