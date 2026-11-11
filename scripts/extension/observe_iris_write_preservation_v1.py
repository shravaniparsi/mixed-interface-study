#!/usr/bin/env python3
"""Real Iris dispatcher/ASGI/SQLite observations; no mocked responses."""
import argparse
import asyncio
import base64
import json
import inspect
import os
import secrets
import tempfile
from pathlib import Path

import httpx
from jsonschema.validators import validator_for
from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.sets.models import SetUpdate
from app.startup import initialize_databases
from iris_client import IrisClient
from iris_mcp import tools

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def encode(value):
    return {'base64': base64.b64encode(value).decode()} if isinstance(value, bytes) else value

async def snapshot(db, set_id):
    cursor = await db.execute('PRAGMA table_info(sets)')
    columns = [r[1] for r in await cursor.fetchall()]
    cursor = await db.execute('SELECT * FROM sets WHERE id = ?', (set_id,))
    row = await cursor.fetchone()
    assert row is not None and len(row) == len(columns)
    return dict(zip(columns, map(encode, row)))

class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, application, log):
        self.transport = httpx.ASGITransport(app=application)
        self.log = log

    async def handle_async_request(self, request):
        response = await self.transport.handle_async_request(request)
        await response.aread()
        # Authentication bodies/tokens and headers are never recorded.
        if request.url.path.startswith(('/api/sets', '/api/collections')):
            self.log.append({'method': request.method, 'path': request.url.path,
                             'query': request.url.query.decode(),
                             'body': json.loads(request.content) if request.content else None,
                             'status': response.status_code, 'response': response.json()})
        return response

    async def aclose(self):
        await self.transport.aclose()

async def execute(case, channel, output):
    record = {'case': case, 'channel': channel, 'status': 'incomplete', 'http': []}
    path = output / (case + '-' + channel + '.json')
    manager = None
    with tempfile.TemporaryDirectory(prefix='iris-study-') as temporary:
        try:
            config = AppConfig(debug=True, database=DatabaseConfig(data_dir=str(Path(temporary) / 'data')),
                               auth=AuthConfig(jwt_secret=secrets.token_urlsafe(40), argon2_time_cost=1,
                                               argon2_memory_cost=8192, argon2_parallelism=1))
            application = create_app(config)
            manager = DatabaseManager(config)
            await initialize_databases(manager)
            application.state.db_manager = manager
            transport = RecordingTransport(application, record['http'])
            async with httpx.AsyncClient(transport=transport, base_url='http://study.local') as api:
                password = secrets.token_urlsafe(24)
                setup = await api.post('/api/auth/setup', json={'username': 'study-admin', 'password': password})
                assert setup.status_code in (200, 201), 'Actor setup rejected'
                login = await api.post('/api/auth/login', json={'username': 'study-admin', 'password': password})
                assert login.status_code == 200, 'Actor login rejected'
                token = login.json()['access_token']
                api.headers['Authorization'] = 'Bearer ' + token
                collection = await api.post('/api/collections', json={'name': 'Study collection'})
                assert collection.status_code == 201, 'Collection fixture rejected'
                collection_id = collection.json()['id']
                grouped = case != 'ungrouped_edit'
                created = await api.post('/api/sets', json={'name': 'Study set',
                    'description': 'Original description', 'collection_id': collection_id if grouped else None})
                assert created.status_code == 201, 'Set fixture rejected'
                set_id = created.json()['id']
                initial = await api.get('/api/sets/' + set_id)
                assert initial.status_code == 200
                before = await snapshot(manager.main_db, set_id)
                assert before['collection_id'] == (collection_id if grouped else None)
                record.update(refs={'set_id': set_id, 'collection_id': collection_id,
                                    'actor_id': before['created_by']}, before=before,
                              api_before=initial.json())
                prior_members = await api.get('/api/sets', params={'collection_id': collection_id})
                assert prior_members.status_code == 200
                record['members_before'] = [s['id'] for s in prior_members.json()['items']]
                clear = case == 'explicit_clear'
                name = 'move_set' if clear else 'update_set'
                requested = {'set_id': set_id, **({'collection_id': None} if clear else {'description': 'Edited description'})}
                record.update(tool=name, intent=requested)
                definitions = {t.name: t for t in tools.tool_definitions()}
                schema = definitions[name].inputSchema
                record['tool_schema'] = schema
                model_schema = SetUpdate.model_json_schema()
                record['api_schema'] = model_schema
                effect_start = len(record['http'])
                if channel == 'mcp_dispatch':
                    record['input'] = requested
                    validator = validator_for(schema)
                    validator.check_schema(schema)
                    record['schema_errors'] = [e.message for e in validator(schema).iter_errors(requested)]
                    async with IrisClient(url='http://study.local', token=token,
                                          transport=RecordingTransport(application, record['http'])) as client:
                        result = await tools.dispatch(name, client, requested)
                    record['tool_result'] = [x.model_dump(mode='json') for x in result]
                    text = result[0].text if len(result) == 1 else ''
                    try:
                        body = json.loads(text)
                    except (TypeError, json.JSONDecodeError):
                        body = None
                    record['operation_success'] = isinstance(body, dict) and body.get('id') == set_id
                else:
                    payload = {k: initial.json()[k] for k in model_schema['properties'] if k in initial.json()}
                    payload.update({'collection_id': None} if clear else {'description': 'Edited description'})
                    record['input'] = payload
                    validator = validator_for(model_schema)
                    validator.check_schema(model_schema)
                    record['schema_errors'] = [e.message for e in validator(model_schema).iter_errors(payload)]
                    response = await api.put('/api/sets/' + set_id, json=payload)
                    record['direct_result'] = {'status': response.status_code, 'body': response.json()}
                    record['operation_success'] = response.status_code == 200 and response.json().get('id') == set_id
                record['effect_http'] = record['http'][effect_start:].copy()
                puts = [h for h in record['effect_http'] if h['method'] == 'PUT']
                assert len(puts) == 1, 'Expected exactly one business update'
                record['outgoing_put'] = puts[0]
                after_api = await api.get('/api/sets/' + set_id)
                assert after_api.status_code == 200
                record['api_after'] = after_api.json()
                after = await snapshot(manager.main_db, set_id)
                record['after'] = after
                after_members = await api.get('/api/sets', params={'collection_id': collection_id})
                assert after_members.status_code == 200
                record['members_after'] = [s['id'] for s in after_members.json()['items']]
                allowed = {'collection_id', 'updated_at'} if clear else {'description', 'updated_at'}
                changed = sorted(k for k in set(before) | set(after)
                                 if k not in before or k not in after or type(before[k]) != type(after[k]) or before[k] != after[k])
                record['scores'] = {'schema_valid': not record['schema_errors'],
                    'operation_success': record['operation_success'],
                    'requested_postcondition': after['collection_id'] is None if clear else after['description'] == 'Edited description',
                    'changed_columns': changed,
                    'frame_violations': sorted(set(changed) - allowed),
                    'naive_membership_preservation_alert': before['collection_id'] != after['collection_id']}
                record['status'] = 'observed'
        except BaseException as error:
            record.update(error_type=type(error).__name__, error=str(error))
        finally:
            if manager is not None:
                await manager.close()
            save(path, record)
    return record['status'] == 'observed'

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(os.environ['STUDY_APP_ROOT']).resolve()
    assert Path(inspect.getsourcefile(create_app)).resolve() == source / 'backend/app/main.py'
    assert Path(tools.__file__).resolve() == source / 'mcp/src/iris_mcp/tools.py'
    assert Path(inspect.getsourcefile(IrisClient)).resolve() == source / 'iris-client/src/iris_client/client.py'
    args.output.mkdir(exist_ok=False)
    for case in ['grouped_edit', 'ungrouped_edit', 'explicit_clear']:
        for channel in ['direct_complete', 'mcp_dispatch']:
            if not await execute(case, channel, args.output):
                return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
