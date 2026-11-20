#!/usr/bin/env python3
"""Reusable exact-blob acquisition under the unchanged evaluation source limits."""
import argparse,base64,datetime,hashlib,json,pathlib,re,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc)
def verify(out):
 x=json.loads((out/'collection.json').read_text());assert x['status']=='source_wave_closed'
 for p,h in x['input_sha256'].items():assert sha((ROOT/p).read_bytes())==h,p
 schedule=json.loads((ROOT/x['manifest']).read_text());assert len(x['rows'])==len(schedule['rows'])
 for expected,row in zip(schedule['rows'],x['rows']):
  assert all(row[k]==v for k,v in expected.items())
  if row['status']=='unavailable':continue
  assert row['status']=='collected_verified'
  raw=(out/row['file']).read_bytes();envelope=(out/row['envelope']).read_bytes()
  assert sha(raw)==row['sha256'] and sha(envelope)==row['envelope_sha256']
  assert base64.b64decode(json.loads(envelope)['content'])==raw
  assert len(raw)==row['declared_bytes']==row['bytes']
  assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha']
 summary=dict(status='verified',collected=sum(r['status']=='collected_verified' for r in x['rows']),unavailable=sum(r['status']=='unavailable' for r in x['rows']),application_executed=False,scientific_cases=0)
 (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
def collect(manifest,freeze):
 assert re.fullmatch('[0-9a-f]{40}',freeze)
 s=json.loads((ROOT/manifest).read_text());seq=s['project_sequence'];assert 9<=seq<=40
 tree_path=f'results/editability-repairability-repository-metadata-v1/{seq:02d}/3.json'
 files=[manifest,'scripts/evaluation/source_wave.py','protocol/editability-repairability-evaluation-v1.md','manifests/redesign-evaluation-procedure-v1.json','manifests/redesign-evaluation-exposure-v1.json','results/editability-repairability-repository-metadata-v1/collection.json',tree_path,s['status_path']]
 if s.get('prior_collection'):files.append(s['prior_collection'])
 bindings={}
 for p in files:
  raw=(ROOT/p).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+p],cwd=ROOT);bindings[p]=sha(raw)
 project=json.loads((ROOT/files[5]).read_text())['projects'][seq-1];assert project['sequence']==seq and project['group']=='evaluation';assert bindings[tree_path]==project['requests'][2]['sha256']
 state=json.loads((ROOT/s['status_path']).read_text());assert state['selected_slots']<6 and state['source_phase_seconds_used']<12*3600
 assert all(r['status']!='source_unattempted' for r in state['rows'] if r['sequence']<seq)
 tree={e['path']:e for e in json.loads((ROOT/tree_path).read_text())['tree']}
 for p in s['absent_root_paths']:assert p not in tree
 prior=json.loads((ROOT/s['prior_collection']).read_text()) if s.get('prior_collection') else None
 if prior:assert prior['status']=='source_wave_closed' and prior['project_sequence']==seq and prior['revision']==project['revision']
 anchor=datetime.datetime.fromisoformat(prior['source_phase_anchor_utc']) if prior else now()
 used=prior['decoded_bytes'] if prior else 0;paths=prior['scheduled_paths'][:] if prior else []
 deadline=min(anchor+datetime.timedelta(hours=2),anchor+datetime.timedelta(seconds=12*3600-state['source_phase_seconds_used']))
 for row in s['rows']:
  e=tree[row['path']];assert e['type']=='blob' and e['sha']==row['blob_sha'] and e['size']==row['declared_bytes']
  assert row['path'] not in paths;paths.append(row['path'])
 assert len(paths)<=256
 out=ROOT/s['output'];out.mkdir(exist_ok=False)
 x=dict(manifest=manifest,freeze=freeze,input_sha256=bindings,project_sequence=seq,repository=project['repository'],revision=project['revision'],source_phase_anchor_utc=anchor.isoformat(),source_phase_deadline_utc=deadline.isoformat(),status='in_progress',rows=[],application_executed=False,scientific_cases=0,scheduled_paths=paths,decoded_bytes=used)
 def save():(out/'collection.json').write_text(json.dumps(x,indent=2)+'\n')
 for i,row in enumerate(s['rows'],1):
  observed=dict(row);x['rows'].append(observed);t=time.monotonic();save()
  try:
   assert now()<deadline,'source deadline reached';assert row['declared_bytes']<=1024**2 and used+row['declared_bytes']<=16*1024**2
   cp=subprocess.run(['gh','api','repos/'+project['repository']+'/git/blobs/'+row['blob_sha']],capture_output=True,timeout=30);observed['exit_code']=cp.returncode
   if cp.returncode:raise RuntimeError(cp.stderr.decode(errors='replace')[:1000])
   assert len(cp.stdout)<=2*1024**2
   value=json.loads(cp.stdout);assert value['encoding']=='base64';raw=base64.b64decode(value['content']);assert len(raw)==row['declared_bytes'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha'];raw.decode('utf8')
   envelope=f'{i}.json';name=f'{i}.txt';(out/envelope).write_bytes(cp.stdout);(out/name).write_bytes(raw);used+=len(raw)
   observed.update(status='collected_verified',file=name,bytes=len(raw),sha256=sha(raw),envelope=envelope,envelope_sha256=sha(cp.stdout))
  except Exception as e:observed.update(status='unavailable',error_type=type(e).__name__,error=str(e))
  observed['elapsed_seconds']=time.monotonic()-t;x['decoded_bytes']=used;save();print(json.dumps({'path':row['path'],'status':observed['status']}),flush=True)
 x['status']='source_wave_closed';save();verify(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--freeze');p.add_argument('--verify-output');a=p.parse_args()
 if a.verify_output:verify(ROOT/a.verify_output)
 else:assert a.manifest and a.freeze;collect(a.manifest,a.freeze)
if __name__=='__main__':main()
