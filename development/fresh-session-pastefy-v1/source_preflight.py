"""Verify original Pastefy tree and vendored Maven artifacts; never build or run it."""
import hashlib,json,pathlib,shutil,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/fresh-session-feasibility-v1'))
from source_check import require,tree_identity,verify
REV='caf35d8f279e2e1386a066753f2d644a0ba79507'
META=ROOT/'results/editability-repairability-repository-metadata-v1/25/3.json'
def vendor_inventory(src):
 base=src/'backend/vendor-maven-repository';rows=[]
 for p in sorted(base.rglob('*')):
  if not p.is_file():continue
  raw=p.read_bytes();row=dict(path=str(p.relative_to(src)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());rows.append(row)
  if p.suffix in ['.jar','.pom']:
   side=p.with_name(p.name+'.sha1');require(side.is_file(),'vendored_checksum_present',path=row['path'])
   require(side.read_text().strip().lower()==hashlib.sha1(raw).hexdigest(),'vendored_checksum_matches',path=row['path'])
 require(any(x['path'].endswith('.jar') for x in rows),'vendored_jars_present')
 return rows

def main(dest):
 dest=pathlib.Path(dest);require(not dest.exists(),'fresh_destination');require(shutil.disk_usage(dest.parent).free>128*1024**2,'disk_headroom')
 meta=json.loads(META.read_text());require(meta['truncated'] is False,'complete_source_tree');rows=meta['tree'];expected_tree=tree_identity(rows)
 subprocess.run(['git','init','-q',str(dest)],check=True,timeout=10)
 git=['git','-c','core.hooksPath=/dev/null','-C',str(dest)]
 with (dest.parent/(dest.name+'-fetch.log')).open('wb') as log:
  subprocess.run(git+['fetch','--depth=1','--no-tags','https://github.com/interaapps/pastefy.git',REV],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
 read=lambda *a:subprocess.check_output(git+list(a),text=True,timeout=15).strip()
 require(read('rev-parse','FETCH_HEAD')==REV,'commit_identity');require(read('rev-parse','FETCH_HEAD^{tree}')==expected_tree,'commit_tree_binding')
 subprocess.run(git+['checkout','--quiet','--detach','FETCH_HEAD'],check=True,timeout=30)
 result=verify(dest,rows);vendors=vendor_inventory(dest)
 return dict(status='source_and_vendored_dependencies_verified',revision=REV,source=result,vendored_files=vendors,application_started=False,dependencies_installed=False,scope='Packaged source identity, not review of all source contents or resolved remote dependencies.')
if __name__=='__main__':
 report=main(sys.argv[1]);pathlib.Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='vendored_files'}))
