#!/usr/bin/env python3
"""One original-source build; never starts the resulting application."""
import hashlib, json, os, pathlib, subprocess, tarfile, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(os.environ['RUNNER_TEMP']) / 'redesign-gomodel-build-v1'
OUT = BASE / 'evidence'
SRC = BASE / 'source'
REV = '13bfff9c678dfbba25955f917a1ea233ae1e8630'
TREE = ROOT / 'results/editability-repairability-repository-metadata-v1/01/3.json'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'revision': REV, 'application_executed': False, 'scientific_cases': 0, 'status': 'started', 'stage': 'archive', 'commands': []}
    started = time.monotonic()
    try:
        expected = {e['path']: e for e in json.loads(TREE.read_text())['tree'] if e['type'] == 'blob'}
        assert len(expected) == 3182 and sum(e['size'] for e in expected.values()) == 40947087
        report['tree_sha256'] = sha(TREE.read_bytes())
        archive = BASE / 'source.tar.gz'
        url = 'https://codeload.github.com/enterpilot/gomodel/tar.gz/' + REV
        download = subprocess.run(['curl','--fail','--location','--retry','0','--max-time','60','--max-filesize',str(32*1024*1024),'--output',str(archive),url], capture_output=True, timeout=65)
        (OUT/'archive-download.log').write_bytes(download.stderr)
        assert download.returncode == 0, 'archive download failed: '+str(download.returncode)
        received = archive.stat().st_size
        assert received <= 32*1024*1024
        report.update(archive_url=url, archive_bytes=received, archive_sha256=sha(archive.read_bytes()))
        report['stage'] = 'verify_source'
        SRC.mkdir(exist_ok=False)
        seen = set(); total = 0; roots = set()
        with tarfile.open(archive, 'r:gz') as tf:
            for member in tf:
                parts = pathlib.PurePosixPath(member.name).parts
                assert parts and not member.name.startswith('/') and '..' not in parts
                roots.add(parts[0]); assert len(roots) == 1
                if member.isdir(): continue
                assert member.isfile() and len(parts) > 1
                rel = '/'.join(parts[1:]); assert rel in expected and rel not in seen
                item = expected[rel]; assert member.size == item['size']
                total += member.size; assert total <= 64 * 1024 * 1024 and len(seen) < 3500
                raw = tf.extractfile(member).read()
                assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == item['sha']
                target = SRC / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                target.chmod(0o755 if item['mode'] == '100755' else 0o644)
                seen.add(rel)
        assert seen == set(expected)
        report.update(verified_files=len(seen), verified_bytes=total)
        report['lock_sha256'] = {p: sha((SRC/p).read_bytes()) for p in ['go.mod','go.sum','web/dashboard/package-lock.json']}
        def run(command, log, timeout):
            tick = time.monotonic()
            row = {'command': command, 'log': log}; report['commands'].append(row)
            with (OUT/log).open('wb') as handle:
                completed = subprocess.run(command, cwd=SRC, stdout=handle, stderr=subprocess.STDOUT, timeout=timeout, env={**os.environ, 'CGO_ENABLED':'0'})
            row.update(exit_code=completed.returncode, elapsed_seconds=time.monotonic()-tick)
            assert completed.returncode == 0, command
        report['stage'] = 'tool_versions'
        run(['go','version'], 'go-version.txt', 30)
        run(['node','--version'], 'node-version.txt', 30)
        run(['npm','--version'], 'npm-version.txt', 30)
        report['stage'] = 'original_build'
        run(['make','build','VERSION=study-'+REV[:12], 'COMMIT='+REV,'DATE=2026-11-18T00:00:00Z'], 'build.log', 1200)
        report['stage'] = 'post_build_identity'
        for rel, item in expected.items():
            raw = (SRC/rel).read_bytes()
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == item['sha'], rel
        binary = SRC/'bin/gomodel'; frontend = SRC/'internal/admin/dashboard/static/dist'
        assert binary.is_file() and (frontend/'index.html').is_file()
        files = [binary] + sorted(p for p in frontend.rglob('*') if p.is_file())
        assert sum(p.stat().st_size for p in files) <= 192*1024*1024
        report['outputs'] = [{'path':str(p.relative_to(SRC)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files]
        run(['go','version','-m',str(binary)], 'go-build-metadata.txt', 30)
        with tarfile.open(OUT/'executable.tar.gz', 'w:gz') as tf:
            for p in files: tf.add(p, arcname=str(p.relative_to(SRC)), recursive=False)
        report['executable_archive_sha256'] = sha((OUT/'executable.tar.gz').read_bytes())
        report['generated_files'] = sorted(str(p.relative_to(SRC)) for p in SRC.rglob('*') if p.is_file() and str(p.relative_to(SRC)) not in expected and 'node_modules' not in p.parts)
        report.update(status='build_succeeded', stage='complete')
    except Exception as error:
        report.update(status='build_unavailable', error_type=type(error).__name__, error=str(error))
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ['status','stage','application_executed']}))
    return 0 if report['status']=='build_succeeded' else 1
if __name__ == '__main__': raise SystemExit(main())
