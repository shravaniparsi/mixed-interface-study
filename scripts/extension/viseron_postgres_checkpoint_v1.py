#!/usr/bin/env python3
"""Viseron stopped-application database checkpoint helper; run only inside a registered CI job.

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

PG = 'study-viseron-postgres'
APP = 'study-viseron'
DB = 'viseron'
IMAGE_ID = 'sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7'
EXPECTED_VERSION = None


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
    return run(['docker', 'exec', '-i', PG, program, '--username', 'postgres', *args], data)


def sql(query, database=DB):
    return pg('psql', '--no-psqlrc', '--no-align', '--tuples-only',
              '--set', 'ON_ERROR_STOP=1', '--dbname', database,
              '--command', query).decode()


def ident(value):
    return '"' + value.replace('"', '""') + '"'


def guard():
    app = json.loads(run(['docker', 'inspect', APP]))[0]
    service = json.loads(run(['docker', 'inspect', PG]))[0]
    if app['State']['Running'] or not service['State']['Running']:
        raise RuntimeError('Require stopped application and running database')
    if service['HostConfig']['NetworkMode'] != 'none':
        raise RuntimeError('Database must have no external network')
    if app['Image'] != IMAGE_ID or service['Image'] != IMAGE_ID:
        raise RuntimeError('App and database must use the pinned Viseron image')
    if app['HostConfig']['NetworkMode'] not in ('container:' + PG, 'container:' + service['Id']):
        raise RuntimeError('Application must share the isolated database network namespace')
    if EXPECTED_VERSION is None or sql('SHOW server_version_num').strip() != EXPECTED_VERSION:
        raise RuntimeError('Server differs from inspected pinned-image PostgreSQL version')
    databases = sql("SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname", 'postgres').splitlines()
    if databases != ['postgres', DB]:
        raise RuntimeError('Additional databases outside checkpoint scope')
    if sql("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()").strip() != '0':
        raise RuntimeError('Other database sessions remain active')
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
    global EXPECTED_VERSION
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'restore', 'inspect'])
    parser.add_argument('--package-report', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    package = json.loads(args.package_report.read_text())
    if package.get('status') != 'packaged_source_checks_passed_pending_native_controls':
        raise RuntimeError('Require successful original-package inspection')
    if package.get('declared_revision') != '3d77e324d8316033f30acb83058736aa7e468d81':
        raise RuntimeError('Unexpected inspected revision')
    match = re.match(r'^psql \(PostgreSQL\) (\d+)\.(\d+)(?:\s|$)', package['postgres_client_version'])
    if not match or int(match[1]) < 10:
        raise RuntimeError('Unsupported PostgreSQL version format')
    EXPECTED_VERSION = str(int(match[1]) * 10000 + int(match[2]))
    os.umask(0o077)
    if args.report.exists():
        raise RuntimeError('Refuse report overwrite')
    if args.action == 'capture':
        args.private.mkdir(parents=True, exist_ok=False)
        before = fingerprint()
        raw = pg('pg_dump', '--dbname', DB, '--format', 'custom')
        after = fingerprint()
        if before != after:
            raise RuntimeError('Persisted state changed during stopped checkpoint')
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
