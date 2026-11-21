#!/usr/bin/env python3
"""Stream-verify the reused runtime without extraction or application execution."""
import hashlib,json,pathlib,posixpath,sys,tarfile,zipfile
from source_check import require
ZIP_SHA='07da97081df579cf956e505c488615d54ada2bb1ab90cedd70390ab69d9eecce'
TAR_SHA='dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8'
def digest(f):
 h=hashlib.sha256()
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(archive):
 with open(archive,'rb') as f:require(digest(f)==ZIP_SHA,'zip_sha256')
 with zipfile.ZipFile(archive) as z:
  require(len(z.namelist())==len(set(z.namelist())),'unique_zip_entries')
  original=json.loads(z.read('result.json'));require(original['status']=='build_succeeded','build_status')
  require(original['revision']=='49b81a290dfa59906c4d2a69f729460fc6357134','build_revision')
  expected={r['path']:r for r in original['outputs']};require(len(expected)==len(original['outputs']),'unique_inventory')
  with z.open('runtime.tar.gz') as f:require(digest(f)==TAR_SHA,'runtime_sha256')
  seen=set();total=0
  with z.open('runtime.tar.gz') as f,tarfile.open(fileobj=f,mode='r|gz') as t:
   for member in t:
    name=member.name.rstrip('/');p=pathlib.PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and str(p)==name,'safe_member',path=name)
    require(name not in seen and name in expected,'expected_unique_member',path=name);seen.add(name);row=expected[name]
    require(member.mode&0o777==row.get('mode',member.mode&0o777),'member_mode',path=name)
    if row['type']=='directory':require(member.isdir(),'directory',path=name)
    elif row['type']=='symlink':
     require(member.issym() and member.linkname==row['target'],'symlink_identity',path=name)
     target=posixpath.normpath(posixpath.join(str(p.parent),member.linkname))
     require(not member.linkname.startswith('/') and not target.startswith('../') and target in expected,'internal_symlink',path=name)
    else:
     require(member.isfile() and member.size==row['bytes'],'file_identity',path=name)
     require(digest(t.extractfile(member))==row['sha256'],'member_digest',path=name);total+=member.size
  require(seen==set(expected),'complete_runtime')
  require(total==original['output_regular_bytes'],'total_runtime_bytes')
  return dict(status='verified_archive_only',application_started=False,archive_bytes=pathlib.Path(archive).stat().st_size,archive_sha256=ZIP_SHA,runtime_sha256=TAR_SHA,entries=len(seen),regular_bytes=total,dependency_manifests=original['lock_sha256'])
if __name__=='__main__':
 result=verify(sys.argv[1]);pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
