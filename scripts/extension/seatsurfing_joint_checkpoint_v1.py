#!/usr/bin/env python3
"""Stopped-runtime DB/browser/key coordination; PRIVATE artifacts only.

No application/browser is started or stopped here. The enclosing runtime must
first settle and stop them, retaining live network/actor evidence. This is not
warm-state equivalence and does not authorize a runtime job.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
PG_HELPER = ROOT / 'scripts/extension/seatsurfing_postgres_checkpoint_v1.py'
APP = 'study-seatsurfing'
LABEL = 'org.mixed-interface.study'
VALUE = 'seatsurfing-qualification-v1'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def regular(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Require regular, non-symlink evidence file')
    if path.stat().st_size > limit:
        raise ValueError('Evidence file size bound')
    return path.read_bytes()

def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)

def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def validate_storage(raw, origin):
    address = urlparse(origin)
    if address.scheme not in ('http', 'https') or not address.hostname or address.username or address.password or address.path or address.query or address.fragment:
        raise ValueError('Require exact application origin')
    state = json.loads(raw)
    if not isinstance(state, dict) or set(state) != {'cookies', 'origins'}:
        raise ValueError('Require original Playwright storageState object')
    if not isinstance(state['cookies'], list) or not isinstance(state['origins'], list):
        raise ValueError('Malformed storage snapshot')
    if any(cookie.get('domain', '').lstrip('.') != address.hostname for cookie in state['cookies']):
        raise ValueError('Unexpected cookie domain')
    if any(item.get('origin') != origin for item in state['origins']):
        raise ValueError('Unexpected browser origin')
    if len(state['origins']) != 1:
        raise ValueError('Require one captured authenticated application origin')
    entries = state['origins'][0].get('localStorage', [])
    names = [x['name'] for x in entries]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate localStorage keys')
    values = {x['name']: x['value'] for x in entries}
    if not values.get('accessToken') or not values.get('refreshToken'):
        raise ValueError('Native credential snapshot missing')
    return state

def validate_observation(raw, storage_sha):
    proof = json.loads(raw)
    required = ['native_storage_capture', 'browser_requests_settled', 'application_operations_settled',
                'actor_verified', 'token_unchanged', 'refresh_outside_checkpoint_interval',
                'browser_and_application_stopped', 'no_unmapped_browser_state']
    if any(proof.get(k) is not True for k in required):
        raise ValueError('Live runtime observation prerequisites missing')
    if proof.get('storage_sha256') != storage_sha:
        raise ValueError('Observation does not bind native storage capture')
    if not re.fullmatch(r'[0-9a-f]{64}', proof.get('network_trace_sha256', '')):
        raise ValueError('Retained network trace identity missing')
    return proof

def inspect_app(build, keys):
    raw = subprocess.check_output(['docker', 'inspect', '--type', 'container', APP], timeout=15)
    if len(raw) > 1048576:
        raise ValueError('Container metadata bound')
    app, = json.loads(raw)
    if app['Config'].get('Labels', {}).get(LABEL) != VALUE:
        raise ValueError('Not the disposable study application')
    if app['State']['Running'] or app['State'].get('Restarting') or app['State'].get('Paused'):
        raise ValueError('Application not stopped')
    if app['Image'] != build.get('application_image_id'):
        raise ValueError('Application differs from bound build')
    if not app['HostConfig'].get('ReadonlyRootfs'):
        raise ValueError('Require read-only application root filesystem')
    if app['HostConfig'].get('Tmpfs'):
        raise ValueError('Unmapped writable application tmpfs')
    if app['HostConfig'].get('RestartPolicy', {}).get('Name') not in ('', 'no'):
        raise ValueError('Automatic restart is unsupported')
    expected = {'/run/study-private.pem': str(keys['private'].resolve()), '/run/study-public.pem': str(keys['public'].resolve())}
    mounts = app.get('Mounts', [])
    if len(mounts) != 2:
        raise ValueError('Unexpected application mount scope')
    for mount in mounts:
        if mount.get('Type') != 'bind' or mount.get('RW') is not False or expected.get(mount.get('Destination')) != mount.get('Source'):
            raise ValueError('Signing-key bind identity/mode mismatch')
    env = dict(item.split('=', 1) for item in app['Config'].get('Env', []) if '=' in item)
    if env.get('JWT_PRIVATE_KEY') != '/run/study-private.pem' or env.get('JWT_PUBLIC_KEY') != '/run/study-public.pem':
        raise ValueError('Persistent signing-key configuration missing')
    return app

def database(action, build_report, private, report):
    subprocess.run([sys.executable, str(PG_HELPER), action, '--build-report', str(build_report),
                    '--private', str(private), '--report', str(report)], check=True, timeout=300)
    return json.loads(regular(report, 16 * 1024 * 1024))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'restore'])
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--private-key', type=Path, required=True)
    parser.add_argument('--public-key', type=Path, required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--storage', type=Path)
    parser.add_argument('--observation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.output.exists(): raise ValueError('Refuse evidence output overwrite')
    keys = {'private': args.private_key, 'public': args.public_key}
    key_bytes = {name: regular(path, 16384) for name, path in keys.items()}
    build_raw = regular(args.build_report, 16 * 1024 * 1024)
    build = json.loads(build_raw)
    before = inspect_app(build, keys)
    if args.action == 'capture':
        if args.storage is None: raise ValueError('Native storage required for capture')
        storage = regular(args.storage, 4 * 1024 * 1024)
        validate_storage(storage, args.origin)
        observation = regular(args.observation, 1048576)
        validate_observation(observation, digest(storage))
        args.checkpoint.mkdir(mode=0o700, parents=True, exist_ok=False)
        db = database('capture', args.build_report, args.checkpoint / 'database', args.checkpoint / 'capture-database.json')
        if db['status'] != 'checkpoint_captured': raise ValueError('Database capture failed')
        files = {'storage.json': storage, 'observation.json': observation, 'build-report.json': build_raw,
                 'private.pem': key_bytes['private'], 'public.pem': key_bytes['public']}
        for name, raw in files.items(): write_new(args.checkpoint / name, raw)
        manifest = {'origin': args.origin, 'application_container_id': before['Id'],
                    'files': {name: digest(raw) for name, raw in files.items()},
                    'database_baseline_sha256': digest(regular(args.checkpoint / 'database/baseline.json', 16 * 1024 * 1024))}
        write_new(args.checkpoint / 'manifest.json', encode(manifest))
        result = {'status': 'joint_checkpoint_captured_runtime_unqualified', 'manifest_sha256': digest(encode(manifest))}
    else:
        manifest = json.loads(regular(args.checkpoint / 'manifest.json', 1048576))
        if manifest['origin'] != args.origin or manifest['application_container_id'] != before['Id']:
            raise ValueError('Checkpoint application/origin differs')
        for name, expected in manifest['files'].items():
            if name not in {'storage.json', 'observation.json', 'build-report.json', 'private.pem', 'public.pem'}:
                raise ValueError('Unexpected checkpoint member')
            if digest(regular(args.checkpoint / name, 16 * 1024 * 1024)) != expected:
                raise ValueError('Corrupt joint checkpoint')
        if digest(build_raw) != manifest['files']['build-report.json']:
            raise ValueError('Build report changed')
        if any(digest(key_bytes[k]) != manifest['files'][k + '.pem'] for k in keys):
            raise ValueError('Fixed signing keys changed; no database restore attempted')
        baseline = regular(args.checkpoint / 'database/baseline.json', 16 * 1024 * 1024)
        if digest(baseline) != manifest['database_baseline_sha256']:
            raise ValueError('Database baseline changed')
        storage = regular(args.checkpoint / 'storage.json', 4 * 1024 * 1024)
        validate_storage(storage, args.origin)
        # Current stop/quiescence proof must bind the checkpoint storage selected
        # for the next new browser context, not credentials from a diverged branch.
        validate_observation(regular(args.observation, 1048576), digest(storage))
        db_report = args.output.with_name(args.output.name + '.database.json')
        db = database('restore', args.build_report, args.checkpoint / 'database', db_report)
        if db['status'] != 'restore_matches': raise ValueError('Database restore mismatch')
        result = {'status': 'database_restored_browser_context_not_started', 'storage_path': str((args.checkpoint / 'storage.json').resolve()),
                  'storage_sha256': digest(storage), 'database_report_sha256': digest(regular(db_report, 16 * 1024 * 1024))}
    after = inspect_app(build, keys)
    if after['Id'] != before['Id'] or any(regular(keys[k], 16384) != key_bytes[k] for k in keys):
        raise ValueError('Fixture identity changed during coordination')
    write_new(args.output, encode(result))

if __name__ == '__main__': main()
