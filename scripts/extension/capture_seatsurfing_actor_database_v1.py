#!/usr/bin/env python3
"""Read-only actor evidence from the labelled isolated study database; PRIVATE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
from seatsurfing_postgres_checkpoint_v2 import PG, APP, PG_IMAGE_ID, bind_build


def actor_query(user_id, session_id, refresh_id):
    for value in (user_id, session_id, refresh_id):
        if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value, re.I):
            raise ValueError('Require UUID evidence selectors')
    return f"""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
'observedAtMs', EXTRACT(EPOCH FROM clock_timestamp())*1000,
'user', (SELECT row_to_json(u) FROM users u WHERE id='{user_id}'),
'session', (SELECT row_to_json(s) FROM sessions s WHERE id='{session_id}'),
'refreshToken', (SELECT row_to_json(r) FROM refresh_tokens r WHERE id='{refresh_id}'),
'banInactive', (SELECT ban_expiry IS NULL OR ban_expiry <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') FROM users WHERE id='{user_id}'),
'sessionExpiresAtMs', (SELECT EXTRACT(EPOCH FROM expires_at AT TIME ZONE 'UTC')*1000 FROM sessions WHERE id='{session_id}'),
'refreshExpiresAtMs', (SELECT EXTRACT(EPOCH FROM expiry AT TIME ZONE 'UTC')*1000 FROM refresh_tokens WHERE id='{refresh_id}'),
'assignments', (SELECT COALESCE(json_agg(a ORDER BY role_id,scope_type,scope_id), '[]') FROM user_roles a WHERE user_id='{user_id}'),
'roles', (SELECT COALESCE(json_agg(r ORDER BY id), '[]') FROM roles r WHERE id IN (SELECT role_id FROM user_roles WHERE user_id='{user_id}')),
'rolePermissions', (SELECT COALESCE(json_agg(p ORDER BY role_id,permission), '[]') FROM role_permissions p WHERE role_id IN (SELECT role_id FROM user_roles WHERE user_id='{user_id}'))
);
COMMIT;
"""


def capture_actor_database(*, user, session, refresh, build_report, output):
    args = SimpleNamespace(user=user, session=session, refresh=refresh,
                           build_report=Path(build_report), output=Path(output))
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    assert not args.output.exists(), 'Refuse actor evidence overwrite'
    query = actor_query(args.user, args.session, args.refresh)
    build = json.loads(args.build_report.read_text())
    bind_build(build)
    assert build['study_commit'] == os.environ.get('GITHUB_SHA')
    before = subprocess.check_output(['docker', 'inspect', APP, PG], timeout=15)
    app, pg = json.loads(before)
    for item in [app, pg]:
        assert item['Config']['Labels']['org.mixed-interface.study'] == 'seatsurfing-qualification-v1'
        assert item['State']['Running'] and not item['State']['Restarting']
    assert not pg['State']['Paused']
    assert pg['Image'] == PG_IMAGE_ID and app['Image'] == build['application_image_id']
    assert pg['HostConfig']['NetworkMode'] == 'none'
    assert app['HostConfig']['NetworkMode'] in ('container:' + PG, 'container:' + pg['Id'])
    command = ['docker', 'exec', '-i', PG, 'psql', '--username', 'seatsurfing', '--dbname', 'seatsurfing',
               '--no-psqlrc', '--no-align', '--tuples-only', '--quiet', '--set', 'ON_ERROR_STOP=1']
    def retain_query_streams(stdout, stderr):
        for suffix, raw in [('stdout', stdout), ('stderr', stderr)]:
            fd = os.open(str(args.output) + '.query-' + suffix, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream: stream.write(raw)
    try:
        result = subprocess.run(command, input=query.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except subprocess.TimeoutExpired as error:
        retain_query_streams(error.stdout or b'', error.stderr or b'')
        raise
    retain_query_streams(result.stdout, result.stderr)
    assert result.returncode == 0 and not result.stderr, 'Actor query failed; no retry authorized'
    assert len(result.stdout) <= 2 * 1024 * 1024
    data = json.loads(result.stdout)
    after = json.loads(subprocess.check_output(['docker', 'inspect', APP, PG], timeout=15))
    assert [x['Id'] for x in after] == [app['Id'], pg['Id']]
    assert all(x['State']['Running'] and not x['State']['Restarting'] for x in after)
    report = {'status': 'actor_database_observed_not_identity_verdict', 'data': data,
              'query_sha256': hashlib.sha256(query.encode()).hexdigest(),
              'raw_result_sha256': hashlib.sha256(result.stdout).hexdigest(),
              'raw_result': result.stdout.decode(),
              'build_report_sha256': hashlib.sha256(args.build_report.read_bytes()).hexdigest(),
              'application_container_id': app['Id'], 'database_container_id': pg['Id']}
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(report, output, indent=2); output.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    for name in ['user', 'session', 'refresh']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    capture_actor_database(**vars(parser.parse_args()))


if __name__ == '__main__': main()
