#!/usr/bin/env python3
"""SeatSurfing paused-capture/stopped-restore database checkpoint helper; run only inside a registered CI job.

Raw dumps and inventory are private runner artifacts. Public reports contain hashes.
This does not establish process/cache equivalence or authorize an application run.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PG = 'study-seatsurfing-postgres'
APP = 'study-seatsurfing'
BROWSER = 'study-seatsurfing-browser'
DB = 'seatsurfing'
PG_IMAGE_ID = 'sha256:3cccc725163a95947178f4da5e9bf16add75cb286170ac5a2cd2f6513534955d'
BROWSER_IMAGE_ID = 'sha256:fee853fafa59550d162cef52bca02d907694b44ebf6ef9fb075bcc0c65d8dedb'
APP_IMAGE_ID = None
EXPECTED_VERSION = '180007'
CAPTURE_PAUSED = False


def run(args, data=None):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=120)
    if result.returncode:
        # Keep stderr private: database errors can quote record values.
        raise RuntimeError(f'{args[0]} failed with exit {result.returncode}; '
                           f'stderr_sha256={digest(result.stderr)}')
    if result.stderr:
        raise RuntimeError(f'Unexpected command warning; stderr_sha256={digest(result.stderr)}')
    return result.stdout


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pg(program, *args, data=None):
    return run(['docker', 'exec', '-i', PG, program, '--username', 'seatsurfing', *args], data)


def sql(query, database=DB):
    return pg('psql', '--no-psqlrc', '--no-align', '--tuples-only',
              '--set', 'ON_ERROR_STOP=1', '--dbname', database,
              '--command', query).decode()


def ident(value):
    return '"' + value.replace('"', '""') + '"'


def guard():
    app = json.loads(run(['docker', 'inspect', APP]))[0]
    service = json.loads(run(['docker', 'inspect', PG]))[0]
    if not service['State']['Running'] or service['State'].get('Paused'):
        raise RuntimeError('Require running, unpaused database')
    if service['HostConfig']['NetworkMode'] != 'none':
        raise RuntimeError('Database must have no external network')
    browser = json.loads(run(['docker', 'inspect', BROWSER]))[0]
    for item in (app, service, browser):
        if item.get('Config', {}).get('Labels', {}).get('org.mixed-interface.study') != 'seatsurfing-qualification-v1':
            raise RuntimeError('Container is not the disposable SeatSurfing fixture')
    for label, item in [('application', app), ('browser', browser)]:
        state = item['State']
        if state.get('Restarting'):
            raise RuntimeError('Restarting ' + label + ' is unsupported')
        if CAPTURE_PAUSED:
            if state.get('Running') is not True or state.get('Paused') is not True:
                raise RuntimeError('Capture requires paused running ' + label)
        elif state.get('Running') or state.get('Paused'):
            raise RuntimeError('Require stopped ' + label + ' for restore/inspection')
    if APP_IMAGE_ID is None or app['Image'] != APP_IMAGE_ID or service['Image'] != PG_IMAGE_ID:
        raise RuntimeError('App/database image identity mismatch')
    if browser['Image'] != BROWSER_IMAGE_ID:
        raise RuntimeError('Browser image identity mismatch')
    if browser['HostConfig']['NetworkMode'] not in ('container:' + PG, 'container:' + service['Id']):
        raise RuntimeError('Browser must share isolated database network namespace')
    if app['HostConfig']['NetworkMode'] not in ('container:' + PG, 'container:' + service['Id']):
        raise RuntimeError('Application must share the isolated database network namespace')
    if EXPECTED_VERSION is None or sql('SHOW server_version_num').strip() != EXPECTED_VERSION:
        raise RuntimeError('Server differs from inspected pinned-image PostgreSQL version')
    databases = sql("SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname", 'postgres').splitlines()
    if databases != ['postgres', DB]:
        raise RuntimeError('Additional databases outside checkpoint scope')
    session_query = "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
    if CAPTURE_PAUSED:
        session_query += " AND NOT COALESCE(state='idle' AND xact_start IS NULL AND usename='seatsurfing' AND client_addr IN ('127.0.0.1'::inet,'::1'::inet), FALSE)"
    if sql(session_query).strip() != '0':
        raise RuntimeError('Other database sessions remain active or outside the allowed paused idle pool')
    if sql('SELECT count(*) FROM pg_largeobject_metadata').strip() != '0':
        raise RuntimeError('Large objects require separately qualified state comparison')


def fingerprint():
    """Complete user-table rows and sequence states; no field exclusions."""
    guard()
    names = json.loads(sql("""SELECT COALESCE(json_agg(x ORDER BY schema_name, relation_name), '[]')
        FROM (SELECT n.nspname AS schema_name,c.relname AS relation_name,c.relkind
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
        AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','S','m','f')) x"""))
    result = {'tables': [], 'sequences': []}
    for item in names:
        name = ident(item['schema_name']) + '.' + ident(item['relation_name'])
        if item['relkind'] in ('m', 'f'):
            raise RuntimeError('Materialized/foreign relation requires separate restoration support')
        if item['relkind'] == 'S':
            state = sql('SELECT row_to_json(t)::text FROM (SELECT last_value,is_called FROM ' + name + ') t')
            result['sequences'].append({**item, 'state': json.loads(state)})
        else:
            # ONLY avoids counting inherited/partition rows twice; all children
            # are independently enumerated. JSON escapes embedded newlines.
            rows = sql('SELECT row_to_json(t)::text FROM ONLY ' + name + ' t').splitlines()
            canonical = ('\n'.join(sorted(rows)) + ('\n' if rows else '')).encode()
            result['tables'].append({**item, 'rows': len(rows), 'sha256': digest(canonical)})
    schema = pg('pg_dump', '--dbname', DB, '--schema-only')
    # pg_dump's paired psql restrict tokens are random transport guards, not
    # application state. No database values/timestamps are removed.
    lines = schema.splitlines(keepends=True)
    guards = [line for line in lines if re.match(rb'^\\(?:un)?restrict ', line)]
    if guards and (len(guards) != 2 or guards[0].split()[1] != guards[1].split()[1]):
        raise RuntimeError('Unexpected pg_dump restrict guard format')
    schema = b''.join(line for line in lines if line not in guards)
    result['schema_sha256'] = digest(schema)
    for key, query in {
        'roles': 'SELECT row_to_json(t)::text FROM pg_authid t',
        'memberships': 'SELECT row_to_json(t)::text FROM pg_auth_members t',
        'role_database_settings': 'SELECT row_to_json(t)::text FROM pg_db_role_setting t',
        'database_configuration': 'SELECT row_to_json(t)::text FROM (SELECT datname,pg_get_userbyid(datdba) AS owner,encoding,datcollate,datctype,datacl,datconnlimit,datallowconn FROM pg_database ORDER BY datname) t',
        'tablespaces': 'SELECT row_to_json(t)::text FROM pg_tablespace t',
        'settings': 'SELECT row_to_json(t)::text FROM (SELECT name,setting,unit,source FROM pg_settings ORDER BY name) t',
    }.items():
        result[key + '_sha256'] = digest('\n'.join(sorted(sql(query).splitlines())).encode())
    return result


def main():
    global APP_IMAGE_ID, CAPTURE_PAUSED
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'restore', 'inspect'])
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    CAPTURE_PAUSED = args.action == "capture"
    build = json.loads(args.build_report.read_text())
    if build.get('status') != 'source_build_verified_and_inventory_complete':
        raise RuntimeError('Require complete source-build/inventory verification')
    if build.get('source_revision') != '9953f452324bab6fb8f7106dd8965cc401aa456c':
        raise RuntimeError('Unexpected built source revision')
    root = Path(__file__).resolve().parents[2]
    preparation = root / 'results/catalog-seatsurfing-source-build-preparation-v2/manifest.json'
    if build.get('source_preparation_sha256') != digest(preparation.read_bytes()):
        raise RuntimeError('Build does not bind the current source preparation')
    APP_IMAGE_ID = build.get('application_image_id')
    if not isinstance(APP_IMAGE_ID, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', APP_IMAGE_ID):
        raise RuntimeError('Missing exact application image identity')
    os.umask(0o077)
    if args.report.exists():
        raise RuntimeError('Refuse report overwrite')
    if args.action == 'capture':
        args.private.mkdir(parents=True, exist_ok=False)
        before = fingerprint()
        raw = pg('pg_dump', '--dbname', DB, '--format', 'custom')
        after = fingerprint()
        if before != after:
            raise RuntimeError('Persisted state changed during paused checkpoint')
        (args.private / 'database.dump').write_bytes(raw)
        baseline = {'dump_sha256': digest(raw), 'state': before}
        (args.private / 'baseline.json').write_text(json.dumps(baseline, sort_keys=True))
        report = {'status': 'checkpoint_captured', **baseline}
    elif args.action == 'restore':
        guard()
        baseline = json.loads((args.private / 'baseline.json').read_text())
        raw = (args.private / 'database.dump').read_bytes()
        if digest(raw) != baseline['dump_sha256']:
            raise RuntimeError('Checkpoint archive hash mismatch')
        # Restore objects in the existing database; its OID and cluster-role
        # settings remain stable. --single-transaction is atomic and implies
        # exit-on-error; explicitly specify it as well for readability.
        pg('pg_restore', '--dbname', DB, '--clean', '--if-exists',
           '--single-transaction', '--exit-on-error', data=raw)
        state = fingerprint()
        report = {'status': 'restore_matches' if state == baseline['state'] else 'restore_mismatch',
                  'dump_sha256': baseline['dump_sha256'], 'state': state}
    else:
        report = {'status': 'state_inspected', 'state': fingerprint()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    if report['status'] == 'restore_mismatch':
        raise RuntimeError('Restored persisted state differs from checkpoint')


if __name__ == '__main__':
    main()
