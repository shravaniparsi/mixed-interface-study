"""One frozen metadata search; raw source stays outside the public repository."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
QUERY = 'is:issue is:closed label:bug "api" "validation" "frontend" created:<=2025-12-31'
PRIVATE = Path('/private/tmp/reported-interface-fault-frame-v1-source.json')
OUTPUT = ROOT / 'manifests/reported-interface-fault-frame-v1.json'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    assert not PRIVATE.exists() and not OUTPUT.exists(), 'Single collection already exists; do not repeat'
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    command = ['gh', 'api', '-X', 'GET', 'search/issues', '-f', 'q=' + QUERY,
               '-f', 'sort=created', '-f', 'order=asc', '-f', 'per_page=50', '-f', 'page=1']
    response = subprocess.run(command, capture_output=True, timeout=60)
    assert response.returncode == 0, response.stderr.decode()[:1000]
    PRIVATE.write_bytes(response.stdout); PRIVATE.chmod(0o600)
    source = json.loads(response.stdout)
    assert isinstance(source['items'], list) and len(source['items']) <= 50
    rows = []
    for item in source['items']:
        assert 'pull_request' not in item and item['state'] == 'closed'
        title, body = item['title'], item.get('body') or ''
        words = title.split()
        rows.append(dict(id=item['id'], node_id=item['node_id'], number=item['number'], url=item['html_url'],
                         repository=item['repository_url'].removeprefix('https://api.github.com/repos/'),
                         title_excerpt=' '.join(words[:20]), title_excerpt_truncated=len(words) > 20,
                         title_sha256=digest(title), body_sha256=digest(body), body_characters=len(body),
                         created_at=item['created_at'], updated_at=item['updated_at'], closed_at=item['closed_at'],
                         labels=sorted(label['name'] for label in item['labels'])))
    assert len({row['id'] for row in rows}) == len(rows)
    value = dict(kind='reported_interface_fault_search_frame_v1', frozen_head=head, query=QUERY,
                 sort='created', order='asc', page=1, per_page=50,
                 collected_at_utc=datetime.now(timezone.utc).isoformat(),
                 raw_response_sha256=hashlib.sha256(response.stdout).hexdigest(),
                 total_count=source['total_count'], incomplete_results=source['incomplete_results'],
                 retained_count=len(rows), items=rows, scientific_executions=0, confirmed_defects=0,
                 scope='Bounded search-return metadata; reported bugs are not validated faults or new discoveries.')
    OUTPUT.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k:v for k,v in value.items() if k != 'items'}, indent=2))


if __name__ == '__main__': main()
