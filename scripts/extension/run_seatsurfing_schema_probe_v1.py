#!/usr/bin/env python3
"""Coordinator-only original schema execution; no dispatch on import."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
NAME = 'study-seatsurfing-schema-probe'
LABEL = 'org.mixed-interface.study=seatsurfing-qualification-v1'


def schema_command(image):
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', image)
    return ['docker', 'run', '-i', '--name', NAME, '--label', LABEL, '--network', 'none',
            '--restart', 'no', '--read-only', '--memory', '256m', '--cpus', '1', image]


def run_schema_probe(build_report, payload, output):
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert os.environ.get('GITHUB_REPOSITORY') == 'shravaniparsi/mixed-interface-study'
    output = Path(output)
    assert not output.exists(), 'No schema result overwrite'
    build = json.loads(Path(build_report).read_text())
    assert build['status'] == 'source_build_verified_and_inventory_complete'
    assert build['application_revision'] == '9953f452324bab6fb8f7106dd8965cc401aa456c'
    assert build['study_commit'] == os.environ.get('GITHUB_SHA')
    schema = build['original_schema']
    assert schema['status'] == 'compiled_not_executed'
    assert schema['probe_source_sha256'] == hashlib.sha256((ROOT / 'scripts/extension/seatsurfing_original_schema_v1.go').read_bytes()).hexdigest()
    assert isinstance(payload, bytes) and len(payload) <= 65536
    names = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}'], timeout=15).decode().splitlines()
    assert NAME not in names, 'Original schema container already exists; no replay'
    image, = json.loads(subprocess.check_output(['docker', 'image', 'inspect', schema['image_id']], timeout=15))
    assert image['Id'] == schema['image_id'] and image['Os'] == 'linux' and image['Architecture'] == 'amd64'
    assert image['Config']['User'] == '65532:65532'
    assert image['Config']['Entrypoint'] == ['/study-schema/probe']
    report = {'status': 'in_progress', 'input_sha256': hashlib.sha256(payload).hexdigest(),
              'schema_identity': schema, 'retry_count': 0}
    try:
        result = subprocess.run(schema_command(image['Id']), input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        report.update(exit_code=result.returncode, stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace'))
        assert result.returncode == 0 and not result.stderr, 'Original schema initialization/execution failed'
        assert len(result.stdout) <= 1048576, 'Schema output observation bound'
        value = json.loads(result.stdout)
        assert value['baseline'] == 'original_request_decode_and_tag_validation'
        assert value['schema_type'] == 'router.CreateLocationRequest'
        assert value['handler_invoked_by_probe'] is False and isinstance(value['accepted'], bool)
        report.update(status='original_schema_observed', result=value, handler_or_persistence_qualified=False)
    except subprocess.TimeoutExpired as error:
        report.update(status='schema_observation_deadline', stdout=(error.stdout or b'').decode(errors='replace'),
                      stderr=(error.stderr or b'').decode(errors='replace'), container_may_still_be_running=True)
    except Exception as error:
        report.update(status='schema_instrument_failure', error_type=type(error).__name__, error=str(error))
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: json.dump(report, stream, indent=2); stream.write('\n')
    # Parent retains the labelled stopped/pending container and private evidence,
    # then explicitly cleans it up. An observation failure never authorizes retry.
    return report
