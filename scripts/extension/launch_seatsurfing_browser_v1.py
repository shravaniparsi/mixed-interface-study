#!/usr/bin/env python3
"""Coordinator helper for one original native/restored worker, not a dispatcher."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from seatsurfing_browser_bridge_v1 import BrowserBridge
from seatsurfing_postgres_checkpoint_v2 import APP, PG, BROWSER, PG_IMAGE_ID, BROWSER_IMAGE_ID

ROOT = Path(__file__).resolve().parents[2]
LABEL = 'org.mixed-interface.study=seatsurfing-qualification-v1'


def browser_command(tools, configuration, evidence, storage=None):
    command = ['docker', 'run', '-i', '--init', '--name', BROWSER, '--label', LABEL,
               '--network', 'container:' + PG, '--restart', 'no', '--read-only',
               '--memory', '2g', '--cpus', '2', '--shm-size', '512m', '--tmpfs', '/tmp:rw,size=512m',
               '-e', 'TZ=UTC', '-v', f'{ROOT}:/study:ro', '-v', f'{tools}:/tools:ro',
               '-v', f'{configuration}:/input/config.json:ro', '-v', f'{evidence}:/evidence:rw']
    if storage is not None:
        # Storage path inside the untouched private configuration is absolute;
        # mount precisely that verified file at the same path, not its directory.
        command += ['-v', f'{storage}:{storage}:ro']
    command += ['--entrypoint', 'node', BROWSER_IMAGE_ID,
                '/study/scripts/extension/seatsurfing_native_browser_worker_v1.mjs',
                '/tools', '/input/config.json', '/evidence/results']
    return command


def launch_native_browser(*, tools, configuration, private_directory, build_report):
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    tools, configuration, private_directory, build_report = map(lambda p: Path(p).resolve(),
        [tools, configuration, private_directory, build_report])
    build = json.loads(build_report.read_text())
    assert build['status'] == 'source_build_verified_and_inventory_complete'
    assert build['application_revision'] == '9953f452324bab6fb8f7106dd8965cc401aa456c'
    assert build['study_commit'] == os.environ.get('GITHUB_SHA')
    assert configuration.stat().st_size <= 1048576
    config = json.loads(configuration.read_text())
    assert config['origin'] == 'http://127.0.0.1:8080'
    assert config['mode'] in ('native_login', 'verified_restoration')
    storage = None
    if config['mode'] == 'verified_restoration':
        storage = Path(config['storagePath'])
        assert storage.is_absolute() and not storage.is_symlink() and storage.is_file()
        assert storage.stat().st_size <= 1048576
        assert hashlib.sha256(storage.read_bytes()).hexdigest() == config['storageSha256']
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], timeout=15).decode().splitlines()
    assert BROWSER not in names, 'Existing browser must be explicitly retained/stopped/removed by coordinator; no replacement here'
    app, pg = json.loads(subprocess.check_output(['docker', 'inspect', APP, PG], timeout=15))
    for item in [app, pg]:
        assert item['State']['Running'] and not item['State']['Paused'] and not item['State']['Restarting']
        assert item['Config']['Labels']['org.mixed-interface.study'] == 'seatsurfing-qualification-v1'
    assert app['Image'] == build['application_image_id'] and pg['Image'] == PG_IMAGE_ID
    assert pg['HostConfig']['NetworkMode'] == 'none'
    assert app['HostConfig']['NetworkMode'] in ('container:' + PG, 'container:' + pg['Id'])
    browser_image, = json.loads(subprocess.check_output(['docker', 'image', 'inspect', BROWSER_IMAGE_ID], timeout=15))
    assert browser_image['Id'] == BROWSER_IMAGE_ID and browser_image['Architecture'] == 'amd64'
    assert browser_image['Os'] == 'linux'
    private_directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    evidence = private_directory / 'worker'
    evidence.mkdir(mode=0o700)
    argv = browser_command(tools, configuration, evidence, storage)
    (private_directory / 'launch.json').write_text(json.dumps({'argv': argv, 'mode': config['mode'],
        'configuration_sha256': hashlib.sha256(configuration.read_bytes()).hexdigest(),
        'application_container_id': app['Id'], 'database_container_id': pg['Id'],
        'joint_restoration_verified_by_launcher': False}, indent=2) + '\n')
    return BrowserBridge(argv, private_directory / 'transport', evidence / 'results', config['mode'])
