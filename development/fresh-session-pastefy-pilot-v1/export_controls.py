"""Assemble sanitized text evidence only, using the qualified common exporter."""
import json,pathlib,shutil,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from export_evidence import export
base=pathlib.Path(sys.argv[1]);dest=base/'publication';dest.mkdir();secrets=[]
for credentials in (base/'execution').glob('state-*/credentials.json'):
 secrets.append(json.loads(credentials.read_text())['api_key'])
(dest/'redaction-values.json').write_text(json.dumps(secrets))
for name,source in [('evidence',base/'execution/evidence'),('build-evidence',base/'build/evidence')]:
 target=dest/name;target.mkdir()
 if source.exists():
  for p in source.iterdir():
   if p.is_file() and not p.is_symlink():shutil.copyfile(p,target/p.name)
for state in (base/'execution').glob('state-*'):
 for p in list(state.glob('jvm-*.log'))+list(state.glob('mysql.log')):
  shutil.copyfile(p,dest/'evidence'/(state.name+'-'+p.name))
if (base/'mysql-smoke/mysql.log').is_file():shutil.copyfile(base/'mysql-smoke/mysql.log',dest/'evidence/mysql-smoke.log')
for name in ['validator-install.log','comparator-regeneration.json','mysql-smoke-run.log','run.log','unit-tests.log','database-packages.txt']:
 if (base/name).is_file():shutil.copyfile(base/name,dest/'evidence'/name)
report=export(dest);print(json.dumps(dict(status=report['status'],files=len(report['files']),public_bytes=report['public_bytes'])))
