"""Verify build-resolved frontend and vendored Maven dependencies before runtime."""
import hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from source_check import require

def verify_frontend(original_lock, final_lock, installed_lock):
 original=json.loads(pathlib.Path(original_lock).read_text());final=json.loads(pathlib.Path(final_lock).read_text());installed=json.loads(pathlib.Path(installed_lock).read_text())
 require(original==final,'frontend_lock_unchanged')
 expected=original['packages'];actual=installed['packages'];checked=[]
 require(set(actual)<=set(expected),'no_unlocked_frontend_packages')
 for path,pkg in expected.items():
  if not path:continue
  if path not in actual:
   require(pkg.get('optional') is True,'required_frontend_package_present',path=path);continue
  for key in ['version','resolved','integrity','link']:
   require(pkg.get(key)==actual[path].get(key),'frontend_package_identity',path=path,attribute=key)
  checked.append(path)
 require(bool(checked),'frontend_packages_present')
 return dict(packages_checked=len(checked),optional_absent=sorted(set(expected)-set(actual)-{''}))

def verify_maven(vendor_root,resolved_root):
 vendor=pathlib.Path(vendor_root);resolved=pathlib.Path(resolved_root);checked=[]
 for jar in sorted(vendor.rglob('*.jar')):
  rel=jar.relative_to(vendor);candidate=resolved/rel
  require(candidate.is_file() and not candidate.is_symlink(),'vendored_resolved_jar_present',path=str(rel))
  expected=hashlib.sha256(jar.read_bytes()).hexdigest()
  require(hashlib.sha256(candidate.read_bytes()).hexdigest()==expected,'vendored_resolved_jar_identity',path=str(rel));checked.append(dict(path=str(rel),sha256=expected))
 require(bool(checked),'vendored_jars_present')
 return checked

if __name__=='__main__':
 src,build,out=map(pathlib.Path,sys.argv[1:]);report=dict(frontend=verify_frontend(src/'frontend/package-lock.json',build/'frontend/package-lock.json',build/'frontend/node_modules/.package-lock.json'),maven=verify_maven(src/'backend/vendor-maven-repository',build/'maven-repository'))
 out.write_text(json.dumps(report,indent=2)+'\n')
