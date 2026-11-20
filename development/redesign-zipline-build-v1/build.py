#!/usr/bin/env python3
"""One original-source build; never starts the resulting application."""
import hashlib, json, os, pathlib, subprocess, tarfile, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(os.environ['RUNNER_TEMP']) / 'redesign-zipline-build-v1'
OUT = BASE / 'evidence'
SRC = BASE / 'source'
REV = '49b81a290dfa59906c4d2a69f729460fc6357134'
TREE = ROOT / 'results/editability-repairability-repository-metadata-v1/02/3.json'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'revision': REV, 'application_executed': False, 'scientific_cases': 0, 'status': 'started', 'stage': 'archive', 'commands': []}
    started = time.monotonic()
    try:
        expected = {e['path']: e for e in json.loads(TREE.read_text())['tree'] if e['type'] == 'blob'}
        assert len(expected) == 737 and sum(e['size'] for e in expected.values()) == 4408628
        report['tree_sha256'] = sha(TREE.read_bytes())
        archive = BASE / 'source.tar.gz'
        url = 'https://codeload.github.com/diced/zipline/tar.gz/' + REV
        download = subprocess.run(['curl','--fail','--location','--retry','0','--max-time','60','--max-filesize',str(8*1024*1024),'--output',str(archive),url], capture_output=True, timeout=65)
        (OUT/'archive-download.log').write_bytes(download.stderr)
        assert download.returncode == 0, 'archive download failed: '+str(download.returncode)
        received = archive.stat().st_size
        assert received <= 8*1024*1024
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
                item = expected[rel]; assert member.size == item['size']; assert bool(member.mode & 0o111) == (item['mode'] == '100755')
                total += member.size; assert total <= 16 * 1024 * 1024 and len(seen) < 1000
                raw = tf.extractfile(member).read()
                assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == item['sha']
                target = SRC / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                target.chmod(0o755 if item['mode'] == '100755' else 0o644)
                seen.add(rel)
        assert seen == set(expected)
        report.update(verified_files=len(seen), verified_bytes=total)
        report['lock_sha256'] = {p: sha((SRC/p).read_bytes()) for p in ['package.json','pnpm-lock.yaml','pnpm-workspace.yaml']}
        def run(command, log, timeout):
            tick = time.monotonic()
            row = {'command': command, 'log': log}; report['commands'].append(row)
            with (OUT/log).open('wb') as handle:
                completed = subprocess.run(command, cwd=SRC, stdout=handle, stderr=subprocess.STDOUT, timeout=timeout, env={**os.environ, 'COREPACK_ENABLE_DOWNLOAD_PROMPT':'0', **({'ZIPLINE_BUILD':'true'} if report['stage']=='original_build' else {})})
            row.update(exit_code=completed.returncode, elapsed_seconds=time.monotonic()-tick)
            assert completed.returncode == 0, command
        report['stage'] = 'tool_versions'
        run(['node','--version'], 'node-version.txt', 30)
        assert (OUT/'node-version.txt').read_text().strip() == 'v24.11.1'
        run(['corepack','--version'], 'corepack-version.txt', 30)
        run(['corepack','pnpm','--version'], 'pnpm-version.txt', 60)
        assert (OUT/'pnpm-version.txt').read_text().strip().splitlines()[-1] == '11.28.8'
        report['stage'] = 'locked_install'
        run(['corepack','pnpm','install','--frozen-lockfile'], 'install.log', 600)
        report['stage'] = 'original_build'
        run(['corepack','pnpm','run','build'], 'build.log', 900)
        report['stage'] = 'post_build_identity'
        for rel, item in expected.items():
            raw = (SRC/rel).read_bytes()
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == item['sha'], rel
        assert (SRC/'build/server/index.js').is_file() and (SRC/'build/client/index.html').is_file()
        roots = ['build','node_modules','drizzle','package.json','pnpm-lock.yaml','pnpm-workspace.yaml','mimes.json','code.json']
        files = []
        for name in roots:
            p = SRC/name; assert p.exists(), name
            files.extend([p] if not p.is_dir() else [p]+list(p.rglob('*')))
        files.sort(key=lambda p:str(p.relative_to(SRC)))
        outputs=[]; total=0
        for p in files:
            rel=str(p.relative_to(SRC))
            if p.is_symlink():
                target=p.resolve(strict=True); target.relative_to(SRC)
                assert str(target.relative_to(SRC)).split('/')[0] in roots
                outputs.append({'path':rel,'type':'symlink','target':os.readlink(p)})
            elif p.is_dir():
                outputs.append({'path':rel,'type':'directory','mode':p.stat().st_mode & 0o777})
            else:
                assert p.is_file();size=p.stat().st_size;total+=size;assert total<=2*1024*1024*1024
                outputs.append({'path':rel,'type':'file','bytes':size,'sha256':sha(p.read_bytes()),'mode':p.stat().st_mode & 0o777})
        report['outputs']=outputs;report['output_regular_bytes']=total
        with tarfile.open(OUT/'runtime.tar.gz','w:gz',dereference=False) as tf:
            for p in files:
                tf.inodes.clear()  # Preserve explicit regular-file entries rather than tar hardlinks.
                tf.add(p,arcname=str(p.relative_to(SRC)),recursive=False)
        bundle=OUT/'runtime.tar.gz';assert bundle.stat().st_size<=1024*1024*1024
        h=hashlib.sha256()
        with bundle.open('rb') as f:
            for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
        report['runtime_archive_sha256']=h.hexdigest();report['runtime_archive_bytes']=bundle.stat().st_size
        report.update(status='build_succeeded', stage='complete')
    except Exception as error:
        report.update(status='build_unavailable', error_type=type(error).__name__, error=str(error))
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ['status','stage','application_executed']}))
    return 0 if report['status']=='build_succeeded' else 1
if __name__ == '__main__': raise SystemExit(main())
