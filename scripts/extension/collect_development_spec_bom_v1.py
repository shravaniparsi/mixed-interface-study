"""Collect the fixed two-resource BOM schedule without installs or retries."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

BASE = 'https://repo.maven.apache.org/maven2/tech/jhipster/jhipster-dependencies/7.9.3/jhipster-dependencies-7.9.3.pom'
OUT = Path('/private/tmp/development-spec-bom-v1')

def main():
    OUT.mkdir(mode=0o700, exist_ok=False)
    start = time.monotonic()
    result = {'rows': []}
    for filename, suffix, bound in [('bom.pom', '', 1048576), ('bom.sha1', '.sha1', 1024)]:
        row = dict(filename=filename, url=BASE+suffix, status='not_run')
        result['rows'].append(row)
        try:
            remaining = 60-(time.monotonic()-start)
            if remaining <= 0:
                raise RuntimeError('deadline')
            with urllib.request.urlopen(BASE+suffix, timeout=min(30, remaining)) as response:
                raw = response.read(bound+1)
                row['http_status'] = response.status
            if len(raw) > bound:
                raise ValueError('byte bound')
            path = OUT/filename
            path.write_bytes(raw)
            path.chmod(0o600)
            row.update(status='received', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        except Exception as error:
            row.update(status='error', error_type=type(error).__name__, message=str(error))
        finally:
            result['elapsed_seconds'] = time.monotonic()-start
            path = OUT/'collection.json'
            path.write_text(json.dumps(result, indent=2)+'\n')
            path.chmod(0o600)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
