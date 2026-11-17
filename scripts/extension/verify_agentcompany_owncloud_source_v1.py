#!/usr/bin/env python3
"""Reconstruct fixed packaged-source inspection and narrowly scoped comparisons."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from inspect_agentcompany_owncloud_v1 import FILES, IMAGE

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/agentcompany-owncloud-source-ci-44048854777'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    initialization = ROOT / 'results/agentcompany-initialization-source-v1'
    collection = json.loads((initialization / 'collection.json').read_text())
    for item in collection['files']:
        path = initialization / 'source' / item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    npc_tree = json.loads((initialization / 'npc-path-inventory.json').read_text())
    assert npc_tree['revision'] == collection['revision'] and not npc_tree['truncated']
    assert not any(Path(row['path']).name == 'scenarios.json' for row in npc_tree['entries'])
    run = json.loads((BASE / 'run.json').read_text())
    report = json.loads((BASE / 'artifact/report.json').read_text())
    head = '315a6741b3456228e8bdc8bf4a24a8de8c877f27'
    assert run['databaseId'] == 44048854777 and run['headSha'] == head == report['head']
    assert report['run_id'] == str(run['databaseId'])
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert report['status'] == 'completed' and report['cleanup'] == 'success'
    assert report['image'] == IMAGE and IMAGE in report['image_metadata']['RepoDigests']
    state = report['container_state']
    assert state['Status'] == 'created' and not state['Running'] and state['Pid'] == 0
    assert state['StartedAt'] == '0001-01-01T00:00:00Z' and report['network_mode'] == 'none'
    assert [r['path'] for r in report['files']] == FILES
    sources = {}
    for row in report['files']:
        path = BASE / 'artifact/source' / row['path']
        if row['status'] == 'copied':
            assert row['returncode'] == 0 and path.stat().st_size == row['bytes'] <= 1024**2
            assert sha(path) == row['sha256']
            sources[str(path.relative_to(ROOT))] = sha(path)
        else:
            assert row['status'] == 'unavailable' and row['returncode'] != 0 and not path.exists()
    comparisons = []
    for relative in ('apps/files_sharing/lib/API/Share20OCS.php', 'apps/dav/lib/Connector/Sabre/File.php', 'core/js/sharedialoglinkshareview.js'):
        actual = BASE / 'artifact/source' / relative
        upstream = ROOT / 'results/agentcompany-interface-source-v1/source/owncloud/core' / relative
        comparisons.append({'path': relative, 'packaged_sha256': sha(actual), 'upstream_sha256': sha(upstream),
                            'byte_equal': actual.read_bytes() == upstream.read_bytes()})
    version = (BASE / 'artifact/source/version.php').read_text()
    version_string = re.search(r"\$OC_VersionString = '([^']+)'", version).group(1)
    app_versions = {}
    for app in ('richdocuments', 'files_sharing', 'files_texteditor'):
        xml = ET.parse(BASE / 'artifact/source/apps' / app / 'appinfo/info.xml').getroot()
        app_versions[app] = xml.findtext('version')
    assert len(run['jobs']) == 1
    job = run['jobs'][0]
    assert job['databaseId'] == 133921283972 and job['conclusion'] == 'success'
    timing = json.loads((BASE / 'timing.json').read_text())['billable']['UBUNTU']
    assert timing['jobs'] == len(timing['job_runs']) == 1
    assert timing['job_runs'][0]['job_id'] == job['databaseId']
    assert timing['total_ms'] == sum(r['duration_ms'] for r in timing['job_runs'])
    elapsed = (datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) - datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()
    return {'kind': 'agentcompany_owncloud_packaged_source_v1', 'run_id': run['databaseId'], 'head': head,
            'image': IMAGE, 'core_version_string': version_string, 'app_versions': app_versions,
            'copied_files': sum(r['status'] == 'copied' for r in report['files']),
            'unavailable_files': [r['path'] for r in report['files'] if r['status'] != 'copied'],
            'comparisons': comparisons, 'source_sha256': sources,
            'container_started': False, 'job_elapsed_seconds': elapsed, 'reported_billable_execution_ms': timing['total_ms'],
            'docker_reported_size_bytes': report['image_metadata']['Size'],
            'interpretation': 'Only the three compared files establish byte correspondence. No whole-image equivalence, live behavior, task completion, defect, or filesystem disk-use measurement is established.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    path = ROOT / 'manifests/agentcompany-owncloud-packaged-source-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k != 'source_sha256'}, indent=2))
