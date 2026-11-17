"""Prepare exact locked development packages without importing or installing."""
import base64,hashlib,io,json,tarfile,time,traceback,urllib.request,urllib.parse
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
NAMES=['@angular/forms','@angular/core','@angular/common','@angular/compiler','rxjs','tslib']
def main():
    root=Path('/private/tmp/reactive14-runtime-v1');root.mkdir(exist_ok=False);start=time.monotonic()
    state=dict(status='preparing',phase='lock_integrity',records=[],expanded_bytes=0)
    def save():
        state['elapsed_seconds']=time.monotonic()-start;(root/'setup.json').write_text(json.dumps(state,indent=2)+'\n')
    def check(ok,message):
        if not ok:raise ValueError(message)
    def deadline():check(time.monotonic()-start<120,'120second deadline')
    try:
        evidence=json.loads((REPO/'manifests/development-lockfile-screen-v1.json').read_text())['rows'][0]
        raw=Path('/private/tmp/development-lockfile-screen-v1/1.lock').read_bytes();check(hashlib.sha256(raw).hexdigest()==evidence['sha256'],'lock hash mismatch');lock=json.loads(raw)['packages'];state['lock_sha256']=evidence['sha256']
        for name in NAMES:
            deadline();package=lock['node_modules/'+name];url=package['resolved'];check(urllib.parse.urlparse(url).scheme=='https' and urllib.parse.urlparse(url).hostname=='registry.npmjs.org','unexpected package host')
            state.update(phase='download',package=name,member=None);save()
            with urllib.request.urlopen(url,timeout=min(30,max(0.1,120-(time.monotonic()-start)))) as response:data=response.read(16*1024*1024+1)
            check(len(data)<=16*1024*1024,'16MiB archive bound');actual='sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode();check(actual==package['integrity'],'lock integrity mismatch')
            archive=root/(name.replace('/','_')+'.tgz');archive.write_bytes(data)
            record=dict(name=name,version=package['version'],url=url,integrity=actual,sha256=hashlib.sha256(data).hexdigest(),archive_bytes=len(data),integrity_verified=True);state['records'].append(record);save()
            destination=root/'node_modules'/name;state['phase']='extract'
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                for member in tar:
                    deadline()
                    if not member.isfile():continue
                    state['member']=dict(name=member.name,size=member.size)
                    parts=Path(member.name).parts[1:];check(bool(parts) and '..' not in parts and not Path(*parts).is_absolute(),'unsafe archive path')
                    check(member.size<=16*1024*1024,'16MiB member bound');check(state['expanded_bytes']+member.size<=128*1024*1024,'128MiB total bound')
                    p=destination.joinpath(*parts);p.parent.mkdir(parents=True,exist_ok=True);check(not p.exists(),'duplicate member');body=tar.extractfile(member).read();check(len(body)==member.size,'member size mismatch');p.write_bytes(body);state['expanded_bytes']+=len(body)
            metadata=json.loads((destination/'package.json').read_text());check(metadata['name']==name and metadata['version']==package['version'],'package metadata mismatch')
            record['package_metadata']={k:metadata[k] for k in ['name','version','engines','dependencies','peerDependencies','peerDependenciesMeta','type','main','module','exports'] if k in metadata};save()
        state.update(status='prepared',phase='complete',member=None)
    except Exception as error:state.update(status='failed',error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:save()
    print(json.dumps(dict(status=state['status'],packages=len(state['records']),expanded_bytes=state['expanded_bytes'],elapsed_seconds=state['elapsed_seconds'])))
    return int(state['status']!='prepared')
if __name__=='__main__':raise SystemExit(main())
