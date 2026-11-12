"""Execute under NetBox manage.py shell; no production endpoints or model calls."""
import json
import os
import traceback
from pathlib import Path
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from ipam.models import Prefix

out = Path(os.environ['PROBE_OUTPUT'])
report = {'kind': 'netbox_config_defaults_calibration_v1', 'upstream_commit': os.environ['UPSTREAM_COMMIT'], 'transport': 'django_rest_api_client', 'events': [], 'cases': [], 'terminal': 'started'}

def save():
    out.write_text(json.dumps(report, indent=2, default=str) + '\n')

client = APIClient()

def call(method, path, payload=None):
    response = getattr(client, method)(path, data=payload, format='json')
    try:
        body = response.json()
    except Exception:
        body = {'non_json_body': response.content.decode(errors='replace')}
    report['events'].append({'method': method, 'path': path, 'payload': payload, 'status': response.status_code, 'body': body})
    save()
    return response.status_code, body


def differences(actual, expected):
    return {k: {'missing': k not in actual, 'actual': actual.get(k), 'expected': v} for k, v in expected.items() if k not in actual or type(actual[k]) is not type(v) or actual[k] != v}

try:
    user = get_user_model().objects.create_superuser(username='study_admin', email='study@example.invalid', password='local-disposable-study-only')
    client.force_authenticate(user=user)
    fields = [
        {'name': 'study_text', 'type': 'text', 'default': 'alpha'},
        {'name': 'study_bool', 'type': 'boolean', 'default': True},
        {'name': 'study_int', 'type': 'integer', 'default': 7},
        {'name': 'study_sibling', 'type': 'text'},
    ]
    ids = {}
    for field in fields:
        status, body = call('post', '/api/extras/custom-fields/', {**field, 'object_types': ['ipam.prefix'], 'required': False})
        assert status == 201, ('field_setup', field['name'], status)
        ids[field['name']] = body['id']
    cases = [
        ('omitted_map', None), ('empty_map', {}),
        ('sibling_only', {'study_sibling': 'preserve-me'}),
        ('explicit_overrides', {'study_text': 'override', 'study_bool': False, 'study_int': 9}),
        ('explicit_null_false_zero', {'study_text': None, 'study_bool': False, 'study_int': 0}),
        ('partial_override', {'study_text': 'override'}),
    ]
    for phase in range(2):
        if phase:
            for name, value in [('study_text', 'beta'), ('study_bool', False), ('study_int', 0)]:
                status, body = call('patch', f'/api/extras/custom-fields/{ids[name]}/', {'default': value})
                assert status == 200, ('config_update', name, status)
        defaults = {}
        for name in ['study_text', 'study_bool', 'study_int']:
            status, body = call('get', f'/api/extras/custom-fields/{ids[name]}/')
            assert status == 200 and 'default' in body, ('metadata_read', name, status)
            defaults[name] = body['default']
        for number, (label, supplied) in enumerate(cases):
            payload = {'prefix': f'10.{phase}.{number}.0/24', 'status': 'active', 'description': label}
            if supplied is not None:
                payload['custom_fields'] = supplied
            expected = {**defaults, **(supplied or {})}
            row = {'phase': phase, 'case': label, 'payload': payload, 'metadata_defaults': defaults.copy(), 'expected': expected, 'qualified': False}
            report['cases'].append(row)
            status, body = call('post', '/api/ipam/prefixes/', payload)
            row.update(create_status=status, create_body=body)
            if status != 201 or 'id' not in body:
                row['reason'] = 'creation_not_successful'; save(); continue
            read_status, read_body = call('get', f"/api/ipam/prefixes/{body['id']}/")
            row.update(read_status=read_status, read_body=read_body)
            if read_status != 200:
                row['reason'] = 'readback_not_successful'; save(); continue
            db = Prefix.objects.get(pk=body['id']).custom_field_data
            row.update(qualified=True, database_custom_fields=db, status_baseline_pass=True,
                       differences={'response': differences(body.get('custom_fields', {}), expected),
                                    'readback': differences(read_body.get('custom_fields', {}), expected),
                                    'database': differences(db, expected)})
            save()
    report['terminal'] = 'completed'
except Exception as error:
    report.update(terminal='failed', exception=repr(error), traceback=traceback.format_exc())
    raise
finally:
    save()
