"""One-shot Checkcle package metadata inspection; no image layers or execution."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import signal
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/maintained-checkcle-package-metadata-v1'
MANIFEST = ROOT / 'manifests/maintained-checkcle-package-metadata-v1.json'
SOURCE = '250f5bd62e6e08e32670db394cc6b21b177435bd'
REGISTRY = 'https://registry-1.docker.io/v2/operacle/checkcle/'
ACCEPT = ', '.join(['application/vnd.oci.image.index.v1+json', 'application/vnd.docker.distribution.manifest.list.v2+json', 'application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json'])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--freeze', required=True); args = parser.parse_args()
    for path in ['protocol/maintained-checkcle-package-metadata-v1.md', 'scripts/extension/inspect_checkcle_package_metadata_v1.py']:
        assert (ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', args.freeze + ':' + path], cwd=ROOT)
    if OUT.exists() or MANIFEST.exists():
        raise SystemExit('Refusing repeat collection')
    OUT.mkdir(parents=True)
    events = []
    result = dict(protocol_freeze=args.freeze, image='docker.io/operacle/checkcle:latest', source_commit=SOURCE,
                  requests=events, application_executed=False, layers_downloaded=False)
    opener = urllib.request.build_opener(NoRedirect())
    started = time.monotonic()

    def request_body(url, stage, token=None, secret=False):
        remaining = 240 - (time.monotonic() - started)
        if len(events) >= 8 or remaining <= 0:
            raise ValueError('Registered request/time bound exhausted')
        headers = {'Accept': ACCEPT, 'User-Agent': 'mixed-interface-study'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        event = {'stage': stage, 'host': urllib.parse.urlsplit(url).hostname}
        events.append(event)
        try:
            response = opener.open(urllib.request.Request(url, headers=headers), timeout=min(30, remaining))
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(2 * 1024 * 1024 + 1)
            event.update(status=response.code, bytes=len(raw), content_type=response.headers.get('Content-Type'))
            location = response.headers.get('Location')
            digest = response.headers.get('Docker-Content-Digest')
        if not secret:
            path = OUT / (stage + '.json'); path.write_bytes(raw)
            event.update(archive=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest())
            if digest:
                event['reported_digest'] = digest
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError(stage + ': response exceeds bound')
        return event['status'], raw, location

    def expired(signum, frame):
        raise TimeoutError('Registered request deadline')

    signal.signal(signal.SIGALRM, expired)

    def request(url, stage, token=None, secret=False):
        remaining = 240 - (time.monotonic() - started)
        if remaining <= 0:
            raise ValueError('Registered elapsed-time bound exhausted')
        signal.setitimer(signal.ITIMER_REAL, min(30, remaining))
        try:
            return request_body(url, stage, token, secret)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def verify(raw, digest):
        if 'sha256:' + hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Descriptor digest mismatch')

    try:
        token = None
        status, raw, _ = request(REGISTRY + 'manifests/latest', 'tag-anonymous')
        if status == 401:
            status, authraw, _ = request('https://auth.docker.io/token?service=registry.docker.io&scope=repository%3Aoperacle%2Fcheckcle%3Apull', 'anonymous-token', secret=True)
            if status != 200:
                raise ValueError('Anonymous token unavailable')
            token = json.loads(authraw)['token']; del authraw
            status, raw, _ = request(REGISTRY + 'manifests/latest', 'tag-authenticated', token)
        if status != 200:
            raise ValueError('Manifest status ' + str(status))
        result['tag_digest'] = 'sha256:' + hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        if 'manifests' in manifest:
            candidates = sorted([m for m in manifest['manifests'] if m.get('platform', {}).get('os') == 'linux' and m.get('platform', {}).get('architecture') == 'amd64' and not m.get('platform', {}).get('variant')], key=lambda m:m['digest'])
            result['linux_amd64_candidates'] = candidates
            if not candidates:
                raise ValueError('No exact linux/amd64 candidate')
            digest = candidates[0]['digest']
            if not digest.startswith('sha256:'):
                raise ValueError('Unsupported child digest')
            status, raw, _ = request(REGISTRY + 'manifests/' + digest, 'platform-manifest', token)
            if status != 200:
                raise ValueError('Child manifest unavailable')
            verify(raw, digest); manifest = json.loads(raw)
        result['manifest_digest'] = 'sha256:' + hashlib.sha256(raw).hexdigest()
        digest = manifest['config']['digest']
        if not digest.startswith('sha256:'):
            raise ValueError('Unsupported config digest')
        status, raw, location = request(REGISTRY + 'blobs/' + digest, 'image-config', token)
        for index in range(2):
            if status not in [301,302,303,307,308]:
                break
            parsed = urllib.parse.urlsplit(location or '')
            host = parsed.hostname or ''
            if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in [None,443] or not any(host == suffix or host.endswith('.' + suffix) for suffix in ['docker.com','docker.io','cloudflarestorage.com']):
                raise ValueError('Redirect outside registered destination policy')
            status, raw, location = request(location, 'image-config-redirect-' + str(index + 1))
        if status != 200:
            raise ValueError('Config status ' + str(status))
        verify(raw, digest); config = json.loads(raw)
        result.update(config_digest=digest, architecture=config.get('architecture'), os=config.get('os'), labels=config.get('config', {}).get('Labels') or {})
        if result['architecture'] != 'amd64' or result['os'] != 'linux':
            raise ValueError('Config platform mismatch')
        revision = result['labels'].get('org.opencontainers.image.revision')
        result['status'] = 'declared_revision_match' if revision == SOURCE else ('revision_mismatch' if revision else 'revision_missing')
    except Exception as exc:
        # Do not stringify network exceptions: they can contain signed URLs.
        result.update(status='unavailable', error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            result['error'] = str(exc)
    result['elapsed_seconds'] = time.monotonic() - started
    MANIFEST.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:result.get(k) for k in ['status','error_type','error','manifest_digest','config_digest','labels']}, indent=2))


if __name__ == '__main__':
    main()
