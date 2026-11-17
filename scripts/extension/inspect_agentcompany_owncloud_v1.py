#!/usr/bin/env python3
"""Copy a fixed source list from an immutable, never-started image container."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

IMAGE = 'ghcr.io/theagentcompany/servers-owncloud@sha256:326406d88345899db22fc1081aa8fa15415c542a71b80486c0a2cebf59f56f63'
FILES = ['version.php', 'apps/files_sharing/lib/API/Share20OCS.php',
         'apps/dav/lib/Connector/Sabre/File.php', 'core/js/sharedialoglinkshareview.js',
         'apps/richdocuments/appinfo/info.xml', 'apps/files_sharing/appinfo/info.xml',
         'apps/files_texteditor/appinfo/info.xml', 'COPYING', 'COPYING-README']


def main():
    base = Path(sys.argv[1])
    base.mkdir(parents=True, exist_ok=False)
    report = {'image': IMAGE, 'head': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
              'scope': 'Fixed source extraction only; no container start, task execution or model calls.',
              'status': 'in_progress', 'files': [], 'cleanup': 'not_needed'}
    def save():
        (base / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    def command(args, timeout):
        result = subprocess.run(args, capture_output=True, timeout=timeout)
        return result
    container = None
    save()
    try:
        pulled = command(['docker', 'pull', IMAGE], 420)
        (base / 'pull.log').write_bytes(pulled.stdout + pulled.stderr)
        assert pulled.returncode == 0, 'Image pull failed'
        info = command(['docker', 'image', 'inspect', IMAGE], 30)
        assert info.returncode == 0
        details = json.loads(info.stdout)[0]
        report['image_metadata'] = {k: details[k] for k in ('Id', 'RepoDigests', 'Architecture', 'Os', 'Size')}
        assert IMAGE in details['RepoDigests']
        assert details['Os'] == 'linux' and details['Architecture'] == 'amd64'
        assert details['Size'] <= 8 * 1024**3, 'Expanded image exceeds bound'
        created = command(['docker', 'create', '--network', 'none', '--entrypoint', '/bin/true', IMAGE], 60)
        assert created.returncode == 0
        container = created.stdout.decode().strip()
        assert len(container) == 64 and all(c in '0123456789abcdef' for c in container)
        state = command(['docker', 'inspect', container], 30)
        assert state.returncode == 0
        state = json.loads(state.stdout)[0]
        report['container_state'] = state['State']
        report['network_mode'] = state['HostConfig']['NetworkMode']
        assert state['State']['Status'] == 'created' and not state['State']['Running']
        assert state['State']['StartedAt'].startswith('0001-01-01')
        assert report['network_mode'] == 'none'
        save()
        for relative in FILES:
            target = base / 'source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copied = command(['docker', 'cp', f'{container}:/var/www/html/{relative}', str(target)], 30)
            row = {'path': relative, 'returncode': copied.returncode}
            if copied.returncode == 0:
                assert target.is_file() and target.stat().st_size <= 1024**2, 'Unexpected source size/type'
                raw = target.read_bytes()
                row.update(status='copied', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            else:
                row.update(status='unavailable', error=copied.stderr.decode(errors='replace')[:2000])
            report['files'].append(row)
            save()
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error)[:2000])
    finally:
        if container:
            cleaned = command(['docker', 'rm', '-fv', container], 30)
            report['cleanup'] = 'success' if cleaned.returncode == 0 else 'failed'
        save()
    print(json.dumps({'status': report['status'], 'files': len(report['files']), 'cleanup': report['cleanup']}))
    return 0 if report['status'] == 'completed' and report['cleanup'] == 'success' else 1


if __name__ == '__main__':
    raise SystemExit(main())
