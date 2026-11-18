"""One prospective metadata request; no candidate-source collection or retries."""
import argparse
import datetime
import hashlib
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUERY = 'topic:self-hosted topic:openapi archived:false fork:false stars:>=100 pushed:>=2026-01-01 created:<2026-01-01'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True)
    args = parser.parse_args()
    paths = ['protocol/openapi-public-metadata-screen-v1.md',
             'manifests/openapi-public-exposure-snapshot-v1.json',
             'scripts/extension/collect_openapi_public_metadata_v1.py']
    hashes = {}
    for name in paths:
        raw = (ROOT / name).read_bytes()
        if raw != subprocess.check_output(['git', 'show', args.freeze + ':' + name], cwd=ROOT):
            raise SystemExit('Frozen artifact mismatch')
        hashes[name] = hashlib.sha256(raw).hexdigest()
    dest = ROOT / 'results/openapi-public-metadata-v1'
    manifest = ROOT / 'manifests/openapi-public-metadata-screen-v1.json'
    if dest.exists() or manifest.exists():
        raise SystemExit('Refusing retry or overwrite')
    dest.mkdir()
    result = dict(freeze=args.freeze, artifact_hashes=hashes, query=QUERY,
                  requested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  candidate_sources_fetched=0, runtime_jobs=0, rows=[])
    try:
        token = subprocess.check_output(['gh', 'auth', 'token'], text=True, timeout=10).strip()
        url = 'https://api.github.com/search/repositories?' + urllib.parse.urlencode(
            dict(q=QUERY, sort='stars', order='desc', per_page=20, page=1))
        request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json', 'User-Agent': 'mixed-interface-study'})
        with urllib.request.urlopen(request, timeout=30) as response:
            result['http_status'] = response.status
            raw = response.read(4194305)
        (dest / 'response.json').write_bytes(raw)
        result['response_sha256'] = hashlib.sha256(raw).hexdigest()
        if len(raw) > 4194304:
            raise ValueError('Response exceeds 4 MiB ceiling; truncated prefix retained')
        body = json.loads(raw)
        result.update(total_count=body['total_count'], incomplete_results=body['incomplete_results'])
        prior = json.loads((ROOT / paths[1]).read_text())['references']
        for rank, row in enumerate(body['items'], 1):
            name = row['full_name'].lower()
            aliases = [p for p in prior if p != name and p.rsplit('/', 1)[-1] == name.rsplit('/', 1)[-1]]
            result['rows'].append(dict(rank=rank, repository=row['full_name'],
                repository_id=row['id'], description=row['description'],
                exact_prior_reference_paths=prior.get(name, []), possible_leaf_aliases=aliases,
                status='exposed' if name in prior else 'ancestry_and_exposure_unresolved',
                workflow_qualified=False))
        result['status'] = 'metadata_collected'
    except Exception as exc:
        result.update(status='unavailable', error_type=type(exc).__name__, error=str(exc))
    manifest.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('artifact_hashes','rows')}, indent=2))
    print(json.dumps([dict(rank=r['rank'], repository=r['repository'],status=r['status']) for r in result['rows']],indent=2))


if __name__ == '__main__':
    main()
