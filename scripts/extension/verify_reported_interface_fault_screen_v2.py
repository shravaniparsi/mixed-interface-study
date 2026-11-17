"""Check retained-frame update coverage and optional private anchors, not label truth."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main(private_source=None):
    before_bytes = (ROOT / 'manifests/reported-interface-fault-screen-v1.json').read_bytes()
    before = json.loads(before_bytes)
    after = json.loads((ROOT / 'manifests/reported-interface-fault-screen-v2.json').read_text())
    assert after['predecessor_sha256'] == hashlib.sha256(before_bytes).hexdigest()
    expected = [6,7,9,14,23,24,29,34,40,42,47,49]
    assert after['review_update_positions'] == expected
    assert len(before['rows']) == len(after['rows']) == 50
    assert after['status_counts'] == dict(sorted(Counter(x['screen_status'] for x in after['rows']).items()))
    source = None
    if private_source:
        raw = private_source.read_bytes()
        frame = json.loads((ROOT / 'manifests/reported-interface-fault-frame-v1.json').read_text())
        assert hashlib.sha256(raw).hexdigest() == frame['raw_response_sha256']
        source = json.loads(raw)['items']
    for position,(old,new) in enumerate(zip(before['rows'],after['rows']),1):
        assert all(old[k] == new[k] for k in ('position','id','url','repository','body_sha256'))
        assert not new['scientific_admission']
        if position not in expected:
            assert old == new
        else:
            assert old['screen_status'] == 'partial_body_review_unresolved'
            context = position in [6,7,23,29,40,49]
            assert new['body_review_complete'] == (not context)
            assert new['screen_status'] == ('other_reported_problem_context_screen' if context else 'other_reported_problem')
            if source:
                body = source[position-1]['body']
                assert hashlib.sha256(body.encode()).hexdigest() == new['body_sha256']
                assert new['eligibility_anchor'] in body
    print(json.dumps(dict(retained=50,updated=12,context_only=6,counts=after['status_counts'],private_anchors_verified=bool(source),application_admissions=0),indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--private-source',type=Path);args=parser.parse_args();main(args.private_source)
