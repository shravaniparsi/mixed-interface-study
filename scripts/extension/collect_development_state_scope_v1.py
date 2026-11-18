"""Single bounded source inspection on an exposed development system."""
import hashlib
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path('/private/tmp/development-state-scope-v1')


def main():
    path = ROOT / 'manifests/development-state-scope-schedule-v1.json'
    raw_schedule = path.read_bytes()
    schedule = json.loads(raw_schedule)
    assert len(schedule['files']) == schedule['request_limit'] == 8
    OUT.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    result = {'kind': 'development_state_scope_collection',
              'schedule_sha256': hashlib.sha256(raw_schedule).hexdigest(),
              'executing_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'rows': []}
    for index, item in enumerate(schedule['files'], 1):
        row = dict(item, index=index, status='not_run')
        result['rows'].append(row)
        remaining = schedule['wall_seconds'] - (time.monotonic() - started)
        try:
            if remaining <= 0:
                row['reason'] = 'overall_deadline'
                continue
            url = 'https://raw.githubusercontent.com/' + schedule['repository'] + '/' + schedule['revision'] + '/' + item['path']
            with urllib.request.urlopen(url, timeout=min(30, remaining)) as response:
                body = response.read(schedule['bytes_per_file_limit'] + 1)
                row['http_status'] = response.status
            if len(body) > schedule['bytes_per_file_limit']:
                raise ValueError('File byte limit exceeded')
            blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
            row.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), observed_blob_sha=blob)
            if blob != item['blob_sha']:
                raise ValueError('Git blob mismatch')
            dest = OUT / (str(index) + '.txt')
            dest.write_bytes(body)
            dest.chmod(0o600)
            row['status'] = 'verified'
        except Exception as error:
            row.update(status='failed', error_type=type(error).__name__, error=str(error))
        finally:
            result['elapsed_seconds'] = time.monotonic() - started
            (OUT / 'collection.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'statuses': [r['status'] for r in result['rows']]}))


if __name__ == '__main__':
    main()
