"""Run the valid-path, API-only PetClinic feasibility sequence against local H2."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default=os.environ.get('PETCLINIC_BASE_URL', 'http://127.0.0.1:9966/petclinic'))
parser.add_argument('--output', required=True, type=Path, help='New JSON evidence file; existing files are rejected')
parser.add_argument('--visit-date', default='2026-11-06', type=datetime.date.fromisoformat)
args = parser.parse_args()
base = args.base_url.rstrip('/')
url = urlsplit(base)
if url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1') or url.username or url.password or url.query or url.fragment:
    parser.error('--base-url must be loopback HTTP, without credentials, query or fragment')
if args.output.exists():
    parser.error('--output already exists; choose a new evidence filename')
args.output.parent.mkdir(parents=True, exist_ok=True)
opener = build_opener(ProxyHandler({}), NoRedirect())
trace = []


def call(method, path, payload=None, status=200):
    raw = None if payload is None else json.dumps(payload).encode()
    request = Request(base + path, data=raw, method=method, headers={'Content-Type': 'application/json'})
    started = time.perf_counter()
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read().decode()
        try:
            value = json.loads(body) if body else None
        except json.JSONDecodeError:
            value = body
        trace.append({'method': method, 'path': path, 'request': payload, 'status': response.status, 'response': value, 'seconds': time.perf_counter() - started})
        assert response.status == status, (response.status, status, path)
        return value


result = {'kind': 'feasibility_api_only_smoke', 'subject': 'petclinic', 'not_a_mixed_interface_experiment': True, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'actor': 'anonymous native default', 'base_url': base, 'visit_date': args.visit_date.isoformat(), 'trace': trace}
try:
    assert call('GET', '/actuator/health')['status'] == 'UP'
    before = call('GET', '/api/owners')
    result['initial_owner_count'] = len(before)
    result['initial_owners_sha256'] = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert len(before) == 10, 'fresh H2 seed required before the smoke sequence'
    pet_types = call('GET', '/api/pettypes')
    owner_fields = {'firstName': 'Alice', 'lastName': 'Research', 'address': '1 Pilot Lane', 'city': 'Testville', 'telephone': '5550100001'}
    owner = call('POST', '/api/owners', owner_fields, 201)
    owner_id = owner['id']
    pet = call('POST', f'/api/owners/{owner_id}/pets', {'name': 'Pilotpet', 'birthDate': '2024-01-10', 'type': pet_types[0]}, 201)
    pet_id = pet['id']
    visit_date = args.visit_date.isoformat()
    call('POST', f'/api/owners/{owner_id}/pets/{pet_id}/visits', {'date': visit_date, 'description': 'Pilot routine check'}, 201)
    owner_fields['telephone'] = '5550100002'
    call('PUT', f'/api/owners/{owner_id}', owner_fields, 204)
    observed = call('GET', f'/api/owners/{owner_id}')
    assert observed['telephone'] == '5550100002'
    attached = [p for p in observed['pets'] if p['id'] == pet_id]
    assert len(attached) == 1
    assert any(v['description'] == 'Pilot routine check' and v['date'] == visit_date for v in attached[0]['visits'])
    result['assertions'] = ['health UP', 'owner created', 'pet linked to owner', 'visit linked to pet', 'meaningful owner edit persisted', 'relationships and visit preserved after owner edit']
    result['status'] = 'passed'
except Exception as exc:
    result['status'] = 'failed'
    result['error'] = repr(exc)
finally:
    result['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'requests': len(trace), 'result': str(args.output), 'error': result.get('error')}))
if result['status'] != 'passed':
    raise SystemExit(1)
