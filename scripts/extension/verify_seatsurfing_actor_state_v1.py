"""Coordinator actor acquisition and offline verification, without login/refresh."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
from capture_seatsurfing_actor_database_v1 import capture_actor_database, actor_query
from seatsurfing_postgres_checkpoint_v2 import bind_build

ROOT = Path(__file__).resolve().parents[2]


def sha(raw): return hashlib.sha256(raw).hexdigest()


def bind_actor_inputs(storage_raw, storage_sha256, public_key_raw, provision, build_raw):
    if sha(storage_raw) != storage_sha256: raise ValueError('Original browser storage hash mismatch')
    if sha(public_key_raw) != provision.get('public_key_sha256'): raise ValueError('Public key differs from provisioned key')
    if sha(build_raw) != provision.get('build_report_sha256'): raise ValueError('Provisioning used another build report')
    storage = json.loads(storage_raw)
    if len(storage['origins']) != 1 or storage['origins'][0]['origin'] != 'http://127.0.0.1:8080':
        raise ValueError('Unexpected actor storage origin')
    rows = storage['origins'][0]['localStorage']
    if len({row['name'] for row in rows}) != len(rows): raise ValueError('Duplicate actor storage key')
    values = {row['name']: row['value'] for row in rows}
    token = values['accessToken']
    if not isinstance(token, str) or len(token) >= 16384 or len(token.split('.')) != 3:
        raise ValueError('Invalid token envelope')
    part = token.split('.')[1]
    claims = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))
    # Unverified claims select rows only. The offline signature/identity verifier
    # must subsequently pass; decoding does not authenticate these selectors.
    query = actor_query(claims['userID'], claims['sid'], values['refreshToken'])
    return values, claims, query


def verify_actor_state(*, build_report, provision_report, storage, storage_sha256, events,
                       public_key, organization_id, private_directory, expected_continuity=None, node_binary='node'):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'shravaniparsi/mixed-interface-study':
        raise RuntimeError('Require registered CI repository')
    build_raw = Path(build_report).read_bytes(); build = json.loads(build_raw); bind_build(build)
    if build.get('study_commit') != os.environ.get('GITHUB_SHA'): raise RuntimeError('Study commit mismatch')
    provision = json.loads(Path(provision_report).read_text())
    if provision.get('status') != 'isolated_fixture_ready_browser_and_actor_unqualified': raise ValueError('Require original provision evidence')
    storage_path, key_path = Path(storage), Path(public_key)
    if storage_path.is_symlink() or key_path.is_symlink() or storage_path.stat().st_size > 1048576 or key_path.stat().st_size > 16384:
        raise ValueError('Bounded original actor files required')
    storage_raw, key_raw = storage_path.read_bytes(), key_path.read_bytes()
    values, claims, query = bind_actor_inputs(storage_raw, storage_sha256, key_raw, provision, build_raw)
    os.umask(0o077)
    private = Path(private_directory); private.mkdir(parents=True, mode=0o700, exist_ok=False)
    report = {'status': 'actor_verification_pending', 'storage_sha256': storage_sha256,
              'public_key_sha256': sha(key_raw), 'runtime_qualified': False}
    try:
        acquired = capture_actor_database(user=claims['userID'], session=claims['sid'], refresh=values['refreshToken'],
                                          build_report=build_report, output=private/'database.json')
        if acquired['query_sha256'] != sha(query.encode()) or acquired['build_report_sha256'] != sha(build_raw):
            raise ValueError('Actor database acquisition differs from bound inputs')
        if acquired['raw_result_sha256'] != sha(acquired['raw_result'].encode()) or json.loads(acquired['raw_result']) != acquired['data']:
            raise ValueError('Raw database evidence binding mismatch')
        if acquired['application_container_id'] != provision['application_container_id'] or acquired['database_container_id'] != provision['database_container_id']:
            raise ValueError('Application/database container changed since provisioning')
        evidence = {'accessToken': values['accessToken'], 'refreshToken': values['refreshToken'],
                    'publicKey': key_raw.decode(), 'organizationId': organization_id,
                    'events': events, 'database': acquired['data'], 'expectedContinuity': expected_continuity}
        raw = json.dumps(evidence).encode()
        if len(raw) > 32 * 1024 * 1024: raise ValueError('Actor input evidence bound')
        input_path, output_path = private/'input.json', private/'identity.json'
        fd = os.open(input_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(raw)
        command = [node_binary, str(ROOT/'scripts/extension/verify_seatsurfing_actor_file_v1.mjs'), str(input_path.absolute()), str(output_path.absolute())]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        (private/'stdout.bin').write_bytes(result.stdout); (private/'stderr.bin').write_bytes(result.stderr)
        if result.returncode or result.stdout or result.stderr: raise RuntimeError('Offline identity verification failed')
        if output_path.is_symlink() or output_path.stat().st_size > 1048576: raise ValueError('Actor result observation bound')
        verified = json.loads(output_path.read_text())
        if verified.get('status') != 'actor_identity_verified' or verified.get('inputSha256') != sha(raw):
            raise ValueError('Actor verifier input/result mismatch')
        if verified['result'].get('identityConsistent') is not True: raise ValueError('Actor identity unavailable')
        report.update(status='actor_acquisition_and_identity_verified', verification=verified,
                      database_acquisition_provenance_verified=True, continuity=verified['result']['continuity'])
    except Exception as error:
        report.update(status='actor_verification_unavailable', error_type=type(error).__name__)
    fd = os.open(private/'actor-result.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: json.dump(report, stream)
    return report
