"""Check frozen frame coverage and optional private source projection, not label truth."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from collect_reported_interface_fault_frame_v1 import QUERY, digest, ROOT


def main(private_source=None):
    path = ROOT / 'manifests/reported-interface-fault-frame-v1.json'
    frame = json.loads(path.read_text())
    screen = json.loads((ROOT / 'manifests/reported-interface-fault-screen-v1.json').read_text())
    assert frame['frozen_head'] == '8252f86711178669615e7435edcfc8623e3c881a'
    assert frame['query'] == QUERY and (frame['sort'], frame['order'], frame['page'], frame['per_page']) == ('created', 'asc', 1, 50)
    items, rows = frame['items'], screen['rows']
    assert frame['retained_count'] == screen['retained_count'] == len(items) == len(rows) == 50
    assert len({r['id'] for r in items}) == 50
    assert [r['created_at'] for r in items] == sorted(r['created_at'] for r in items)
    assert screen['frame_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert screen['status_counts'] == dict(sorted(Counter(r['screen_status'] for r in rows).items()))
    assert screen['repository_count'] == len({r['repository'] for r in items})
    for position, (item, row) in enumerate(zip(items, rows), 1):
        assert row['position'] == position
        assert all(row[k] == item[k] for k in ('id', 'url', 'repository', 'body_sha256'))
        assert not row['scientific_admission']
        assert row['fixed_version'] == row['maintainer_fix_evidence'] == 'not inspected'
    assert frame['scientific_executions'] == screen['scientific_admissions'] == frame['confirmed_defects'] == screen['confirmed_defects'] == 0
    if private_source:
        raw = private_source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == frame['raw_response_sha256']
        source = json.loads(raw)
        assert source['total_count'] == frame['total_count'] and source['incomplete_results'] == frame['incomplete_results']
        assert len(source['items']) == len(items)
        for src, item in zip(source['items'], items):
            assert src['id'] == item['id'] and src['html_url'] == item['url']
            assert digest(src['title']) == item['title_sha256'] and digest(src.get('body') or '') == item['body_sha256']
            assert ' '.join(src['title'].split()[:20]) == item['title_excerpt']
            assert sorted(label['name'] for label in src['labels']) == item['labels']
    print(json.dumps(dict(retained=50, repositories=screen['repository_count'], statuses=screen['status_counts'],
                         private_source_verified=bool(private_source), scientific_admissions=0,
                         scope='Integrity and coverage checks; does not independently validate issue claims or interpretive labels.'), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--private-source', type=Path); args = parser.parse_args()
    main(args.private_source)
