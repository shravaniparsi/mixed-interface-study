"""One bounded anonymous read-only lookup of the original Fusio native app."""
import datetime,hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2]
manifest,freeze=sys.argv[1:];s=json.loads((R/manifest).read_text());bound={}
for p in [manifest,'scripts/evaluation/fusio_catalog_metadata.py',s['parent_collection'],*s['basis']]:
 raw=(R/p).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+p],cwd=R);bound[p]=hashlib.sha256(raw).hexdigest()
parent=json.loads((R/s['parent_collection']).read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(parent['source_phase_deadline_utc'])
assert s['url']=='https://api.fusio-project.org/marketplace/directory/app/fusio/fusio' and s['method']=='GET'
out=R/s['output'];out.mkdir(exist_ok=False)
x={'status':'started','freeze':freeze,'input_sha256':bound,'project_sequence':16,'source_phase_anchor_utc':parent['source_phase_anchor_utc'],'source_phase_deadline_utc':parent['source_phase_deadline_utc'],'method':'GET','url':s['url'],'attempts':1,'application_executed':False,'scientific_cases':0}
try:
 p=subprocess.run(['curl','--fail','--proto','=https','--max-redirs','0','--retry','0','--max-time','30','--max-filesize','1048576',s['url']],capture_output=True,timeout=35)
 x['exit_code']=p.returncode;assert p.returncode==0,p.stderr.decode(errors='replace')[-1000:];assert len(p.stdout)<=1048576
 (out/'metadata.json').write_bytes(p.stdout);d=json.loads(p.stdout);assert isinstance(d,dict)
 x.update(status='catalog_metadata_collected_unqualified',bytes=len(p.stdout),sha256=hashlib.sha256(p.stdout).hexdigest(),observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as e:x.update(status='catalog_metadata_unavailable',error_type=type(e).__name__,error=str(e))
finally:(out/'collection.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['status','application_executed','scientific_cases']}))
