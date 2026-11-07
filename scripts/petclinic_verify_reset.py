"""Verify that a manual PetClinic backend restart restored the initial owner graph."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default=os.environ.get('PETCLINIC_BASE_URL', 'http://127.0.0.1:9966/petclinic'))
parser.add_argument('--baseline', required=True, type=Path, help='JSON from a successful petclinic_api_smoke.py run')
parser.add_argument('--output', required=True, type=Path, help='New JSON evidence file; existing files are rejected')
args = parser.parse_args()
base = args.base_url.rstrip('/')
url = urlsplit(base)
if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1') or url.username or url.password or url.query or url.fragment:
    parser.error('--base-url must be loopback HTTP, without credentials, query or fragment')
if args.output.exists():
    parser.error('--output already exists; choose a new evidence filename')
prior = json.loads(args.baseline.read_text())
if prior.get('status') != 'passed':
    parser.error('--baseline must be a successful API smoke result')
opener = build_opener(ProxyHandler({}), NoRedirect())
result = {'kind': 'process_restart_reset_check', 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base_url': base, 'baseline': str(args.baseline), 'expected_owner_count': prior['initial_owner_count'], 'expected_sha256': prior['initial_owners_sha256'], 'scope': 'Exact GET owners graph after a manual process restart; this script does not restart the backend.'}
try:
    with opener.open(base + '/api/owners', timeout=10) as response:
        owners = json.loads(response.read())
    observed = hashlib.sha256(json.dumps(owners, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result.update(owner_count=len(owners), owners_sha256=observed, equal=observed == prior['initial_owners_sha256'])
    assert result['equal'] and len(owners) == prior['initial_owner_count']
    result['status'] = 'passed'
except Exception as exc:
    result['status'] = 'failed'
    result['error'] = repr(exc)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('x') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
if result['status'] != 'passed':
    raise SystemExit(1)
