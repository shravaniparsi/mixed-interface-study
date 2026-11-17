import pathlib,json,urllib.request,hashlib,base64,tarfile,io,time
root=pathlib.Path('/private/tmp/angular-runtime-qualification-v1');root.mkdir(exist_ok=False);start=time.monotonic();records=[];total=0
lock=json.loads(pathlib.Path('/private/tmp/petclinic-angular-semantics-v1/package-lock.json').read_text())['packages']
def fetch(url):
 assert time.monotonic()-start<900
 data=urllib.request.urlopen(url,timeout=45).read(64*1024*1024+1);assert len(data)<=64*1024*1024;return data
def unpack(raw,dest):
 global total
 tar=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')
 for member in tar.getmembers():
  if not member.isfile():continue
  parts=pathlib.PurePosixPath(member.name).parts[1:];assert parts and '..' not in parts and not pathlib.PurePosixPath(*parts).is_absolute();assert member.size<=64*1024*1024
  total+=member.size;assert total<=512*1024*1024
  p=dest.joinpath(*parts);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read());p.chmod(member.mode & 0o755)
try:
 name='node-v22.22.3-darwin-arm64.tar.gz';base='https://nodejs.org/dist/v22.22.3/'
 sums=fetch(base+'SHASUMS256.txt').decode();sha=next(line.split()[0] for line in sums.splitlines() if line.split()[-1]==name)
 raw=fetch(base+name);assert hashlib.sha256(raw).hexdigest()==sha;unpack(raw,root/'node');records.append(dict(name='node',version='22.22.3',url=base+name,sha256=sha,bytes=len(raw)))
 for name in ['@angular/forms','@angular/core','@angular/common','@angular/compiler','@angular/platform-browser','rxjs','tslib','@standard-schema/spec','zod','zone.js']:
  key='node_modules/'+name
  if key not in lock:records.append(dict(name=name,status='absent_from_lock'));continue
  d=lock[key];raw=fetch(d['resolved']);assert d['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode();unpack(raw,root/key);records.append(dict(name=name,version=d['version'],url=d['resolved'],integrity=d['integrity'],sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
 status='prepared'
except Exception as e:status='failed';records.append(dict(error_type=type(e).__name__,message=str(e)))
result=dict(status=status,records=records,expanded_file_bytes=total,elapsed_seconds=time.monotonic()-start);(root/'setup.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
