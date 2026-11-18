"""Execute one ordinary API operation; caller owns retention and teardown."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from seatsurfing_postgres_checkpoint_v2 import APP, PG, PG_IMAGE_ID, BROWSER_IMAGE_ID, bind_build

ROOT = Path(__file__).resolve().parents[2]
LABEL = 'org.mixed-interface.study=seatsurfing-qualification-v1'
OPERATIONS = {'ordinary_create', 'independent_load', 'ordinary_continue'}


def api_command(name, configuration, storage, evidence):
    return ['docker', 'run', '--name', name, '--label', LABEL, '--network', 'container:' + PG,
            '--restart', 'no', '--user', f'{os.getuid()}:{os.getgid()}', '--read-only', '--memory', '512m', '--cpus', '1', '-e', 'TZ=UTC',
            '-v', f'{ROOT}:/study:ro', '-v', f'{configuration}:/input/config.json:ro',
            '-v', f'{storage}:/input/storage.json:ro', '-v', f'{evidence}:/evidence:rw',
            '--entrypoint', 'node', BROWSER_IMAGE_ID,
            '/study/scripts/extension/seatsurfing_api_worker_v1.mjs',
            '/input/config.json', '/input/storage.json', '/evidence/result.json']


def run_api_operation(*, operation, storage, storage_sha256, build_report, private_directory, location_id=None, edit=None):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'shravaniparsi/mixed-interface-study':
        raise RuntimeError('Require authorized CI repository')
    if operation not in OPERATIONS: raise ValueError('Unregistered API operation')
    build = json.loads(Path(build_report).read_text())
    if build.get('study_commit') != os.environ.get('GITHUB_SHA'): raise RuntimeError('Study commit mismatch')
    image_id = bind_build(build)
    storage = Path(storage).absolute()
    if storage.is_symlink() or not storage.is_file() or storage.stat().st_size > 1048576:
        raise ValueError('Require bounded original storage file')
    if hashlib.sha256(storage.read_bytes()).hexdigest() != storage_sha256: raise ValueError('Storage hash mismatch')
    private = Path(private_directory).absolute()
    if private.exists(): raise ValueError('Refuse operation evidence overwrite or repeat')
    name = 'study-seatsurfing-api-' + operation.replace('_', '-')
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], timeout=15).decode().splitlines()
    if name in names: raise RuntimeError('Operation container already exists; no replay')
    app, pg = json.loads(subprocess.check_output(['docker', 'inspect', APP, PG], timeout=15))
    for item, expected in ((app, image_id), (pg, PG_IMAGE_ID)):
        if item['Image'] != expected or item['Config']['Labels'].get('org.mixed-interface.study') != 'seatsurfing-qualification-v1':
            raise RuntimeError('Fixture identity mismatch')
        if not item['State']['Running'] or item['State']['Paused'] or item['State']['Restarting']:
            raise RuntimeError('Require running unpaused fixture')
    if pg['HostConfig']['NetworkMode'] != 'none' or app['HostConfig']['NetworkMode'] not in ('container:' + PG, 'container:' + pg['Id']):
        raise RuntimeError('Fixture namespace mismatch')
    image, = json.loads(subprocess.check_output(['docker', 'image', 'inspect', BROWSER_IMAGE_ID], timeout=15))
    if image['Id'] != BROWSER_IMAGE_ID or image['Os'] != 'linux' or image['Architecture'] != 'amd64':
        raise RuntimeError('API runtime identity mismatch')
    os.umask(0o077)
    private.mkdir(parents=True, mode=0o700, exist_ok=False)
    evidence = private / 'worker'; evidence.mkdir(mode=0o700)
    config = {'operation': operation, 'origin': 'http://127.0.0.1:8080', 'storageSha256': storage_sha256}
    if location_id is not None: config['id'] = location_id
    if edit is not None: config['edit'] = edit
    configuration = private / 'config.json'; configuration.write_text(json.dumps(config))
    command = api_command(name, configuration, storage, evidence)
    report = {'operation': operation, 'command': command, 'application_container_id': app['Id'],
              'database_container_id': pg['Id'], 'storage_sha256': storage_sha256, 'retry_count': 0,
              'runtime_qualified': False, 'container_retained_for_parent_cleanup': True}
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=95)
        (private / 'stdout.bin').write_bytes(result.stdout); (private / 'stderr.bin').write_bytes(result.stderr)
        report['exit_code'] = result.returncode
        if result.returncode or result.stdout or result.stderr: raise RuntimeError('API worker failed or emitted unexpected output')
        path = evidence / 'result.json'
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16777216: raise RuntimeError('API result observation bound')
        raw = path.read_bytes(); value = json.loads(raw)
        if value.get('status') != 'api_operation_observed' or value.get('operation') != operation:
            raise RuntimeError('API result status or operation mismatch')
        if value.get('storageSha256') != storage_sha256 or value.get('configSha256') != hashlib.sha256(configuration.read_bytes()).hexdigest():
            raise RuntimeError('API result input binding mismatch')
        report.update(status='api_worker_result_retained', result_sha256=hashlib.sha256(raw).hexdigest(), result=value)
    except subprocess.TimeoutExpired as error:
        (private / 'stdout.bin').write_bytes(error.stdout or b''); (private / 'stderr.bin').write_bytes(error.stderr or b'')
        report.update(status='api_worker_deadline', container_may_still_be_running=True)
    except Exception as error:
        report.update(status='api_worker_instrument_failure', error_type=type(error).__name__)
    (private / 'launch-result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
