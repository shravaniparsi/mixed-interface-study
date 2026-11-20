#!/usr/bin/env python3
import argparse,base64,datetime,hashlib,json,pathlib,re,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);a=ap.parse_args();assert re.fullmatch('[0-9a-f]{40}',a.freeze)
 files=['protocol/editability-repairability-evaluation-v1.md','manifests/redesign-evaluation-procedure-v1.json','manifests/redesign-evaluation-exposure-v1.json','manifests/redesign-evaluation-source-wave2-v1.json','scripts/extension/collect_redesign_evaluation_source_wave2_v1.py','scripts/extension/verify_redesign_evaluation_source_wave2_v1.py','results/editability-repairability-repository-metadata-v1/collection.json','results/editability-repairability-repository-metadata-v1/09/3.json','results/redesign-evaluation-source-wave1-v1/collection.json']
 bindings={}
 for name in files:
  raw=(ROOT/name).read_bytes();assert raw==subprocess.check_output(['git','show',a.freeze+':'+name],cwd=ROOT);bindings[name]=hashlib.sha256(raw).hexdigest()
 rows=json.loads((ROOT/files[3]).read_text())['rows'];assert len(rows)==5;project=json.loads((ROOT/files[6]).read_text())['projects'][8];tree=json.loads((ROOT/files[7]).read_text())['tree'];assert project['group']=='evaluation' and project['sequence']==9 and project['status']=='metadata_pinned_workflow_unqualified';assert bindings[files[7]]==project['requests'][2]['sha256']
 for row in rows:
  assert row['repository']==project['repository'] and row['revision']==project['revision'] and row['project_sequence']==9;e=next(e for e in tree if e['path']==row['path']);assert e['type']=='blob' and e['sha']==row['blob_sha'] and e['size']==row['declared_bytes']
 out=ROOT/'results/redesign-evaluation-source-wave2-v1';out.mkdir(exist_ok=False)
 prior=json.loads((ROOT/files[8]).read_text());assert prior['status']=='source_wave_closed';anchor=datetime.datetime.fromisoformat(prior['source_phase_anchor_utc']);assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(prior['source_phase_deadline_utc']);result={'freeze':a.freeze,'input_sha256':bindings,'project_sequence':9,'source_phase_anchor_utc':anchor.isoformat(),'source_phase_deadline_utc':(anchor+datetime.timedelta(hours=2)).isoformat(),'rows':[],'status':'in_progress','application_executed':False,'scientific_cases':0};used=prior['decoded_bytes'][project['repository']]
 for row in rows:
  observed=dict(row);result['rows'].append(observed);start=time.monotonic();(out/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
  try:
   assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(prior['source_phase_deadline_utc']);assert prior['scheduled_counts'][project['repository']]+len(rows)<=256;assert row['declared_bytes']<=1024**2 and used+row['declared_bytes']<=16*1024**2
   response=subprocess.run(['gh','api','repos/'+row['repository']+'/git/blobs/'+row['blob_sha']],capture_output=True,timeout=30);observed['exit_code']=response.returncode
   if response.returncode:raise RuntimeError(response.stderr.decode(errors='replace')[:1000])
   assert len(response.stdout)<=2*1024**2;envelope=str(row['sequence'])+'.json';(out/envelope).write_bytes(response.stdout);value=json.loads(response.stdout);assert value['encoding']=='base64';raw=base64.b64decode(value['content']);assert len(raw)==row['declared_bytes'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha'];raw.decode('utf8');name=str(row['sequence'])+'.txt';(out/name).write_bytes(raw);used+=len(raw);observed.update(status='collected_verified',file=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),envelope=envelope,envelope_sha256=hashlib.sha256(response.stdout).hexdigest())
  except Exception as e:observed.update(status='unavailable',error_type=type(e).__name__,error=str(e))
  observed['elapsed_seconds']=time.monotonic()-start;(out/'collection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:observed[k] for k in ['sequence','path','status']}),flush=True)
 result.update(status='source_wave_closed',scheduled_counts={project['repository']:prior['scheduled_counts'][project['repository']]+len(rows)},decoded_bytes={project['repository']:used});(out/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
