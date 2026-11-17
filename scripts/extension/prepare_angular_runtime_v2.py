"""One bounded, observable dependency preparation; no framework measurement."""
import base64, hashlib, io, json, pathlib, tarfile, time, traceback, urllib.request
ROOT = pathlib.Path('/private/tmp/angular-runtime-qualification-v2')
LOCK = pathlib.Path('/private/tmp/petclinic-angular-semantics-v1/package-lock.json')
PACKAGES = ['@angular/forms', '@angular/core', '@angular/common', '@angular/compiler', '@angular/platform-browser', 'rxjs', 'tslib', '@standard-schema/spec', 'zod', 'zone.js']

def main():
    ROOT.mkdir(exist_ok=False)
    started = time.monotonic()
    state = dict(status='preparing', phase='initialize', member=None, records=[], expanded_bytes=0,
                 lock_sha256=hashlib.sha256(LOCK.read_bytes()).hexdigest())
    def save():
        state['elapsed_seconds'] = time.monotonic()-started
        (ROOT/'setup.json').write_text(json.dumps(state, indent=2)+'\n')
    def check(condition, message):
        if not condition: raise ValueError(message)
    def deadline(): check(time.monotonic()-started < 900, '15 minute deadline exceeded')
    def fetch(url):
        deadline(); state.update(phase='download', url=url, member=None); save()
        with urllib.request.urlopen(url, timeout=45) as response:
            raw = response.read(64*1024*1024+1)
        check(len(raw)<=64*1024*1024, 'download exceeds64MiB')
        return raw
    def extract(raw, destination, only_node=False):
        state['phase']='extract'
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            selected=0
            for member in archive:
                deadline()
                if not member.isfile(): continue
                parts=pathlib.PurePosixPath(member.name).parts[1:]
                if only_node and parts != ('bin','node'): continue
                state['member']={'name':member.name,'size':member.size}; save()
                check(bool(parts) and '..' not in parts and not pathlib.PurePosixPath(*parts).is_absolute(), 'unsafe member path')
                check(member.size<=128*1024*1024, 'member exceeds128MiB')
                check(state['expanded_bytes']+member.size<=512*1024*1024, 'expanded total exceeds512MiB')
                path=destination.joinpath(*parts); path.parent.mkdir(parents=True,exist_ok=True)
                check(not path.exists(),'duplicate extraction path')
                body=archive.extractfile(member).read()
                check(len(body)==member.size, 'member size mismatch')
                path.write_bytes(body); path.chmod(member.mode & 0o755)
                state['expanded_bytes']+=len(body); selected+=1
            check(selected>0, 'no regular files selected')
            if only_node: check(selected==1,'expected exactly one Node executable')
    try:
        lock=json.loads(LOCK.read_text())['packages']
        name='node-v22.22.3-darwin-arm64.tar.gz'; base='https://nodejs.org/dist/v22.22.3/'
        sums=fetch(base+'SHASUMS256.txt').decode()
        expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1]==name)
        raw=fetch(base+name); digest=hashlib.sha256(raw).hexdigest()
        check(digest==expected,'Node SHA256 mismatch')
        state['records'].append(dict(name='node',version='22.22.3',url=base+name,sha256=digest,bytes=len(raw),integrity_verified=True)); save()
        extract(raw,ROOT/'node',only_node=True)
        for name in PACKAGES:
            key='node_modules/'+name
            if key not in lock:
                state['records'].append(dict(name=name,status='absent_from_lock')); save(); continue
            package=lock[key]; raw=fetch(package['resolved'])
            actual='sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode()
            check(actual==package['integrity'],name+' SHA512 mismatch')
            state['records'].append(dict(name=name,version=package['version'],url=package['resolved'],sha256=hashlib.sha256(raw).hexdigest(),integrity=actual,bytes=len(raw),integrity_verified=True)); save()
            extract(raw, ROOT/key)
        state.update(status='prepared',phase='complete',member=None)
    except Exception as error:
        state.update(status='failed',error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally: save()
    print(json.dumps(state,indent=2))
    return 0 if state['status']=='prepared' else 1

if __name__=='__main__': raise SystemExit(main())
