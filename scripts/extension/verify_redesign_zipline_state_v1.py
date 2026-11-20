#!/usr/bin/env python3
import argparse,copy,datetime,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/redesign-zipline-state-v1'
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def normalize(state,id,before):
 x=copy.deepcopy(state);table=x['tables']['public.Url'];row=next(r for r in table['rows'] if r['id']==id);old=next(r for r in before['tables']['public.Url']['rows'] if r['id']==id)
 assert row['destination']=='https://example.com/edited'
 assert datetime.datetime.fromisoformat(row['updatedAt'].replace('Z','+00:00'))>=datetime.datetime.fromisoformat(old['updatedAt'].replace('Z','+00:00'))
 row['destination']=old['destination'];row['updatedAt']=old['updatedAt'];table['rows'].sort(key=canonical);table['row_sha256']=[digest(r) for r in table['rows']]
 return x

def main():
 ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);ap.add_argument('--sha256',required=True);ap.add_argument('--run',type=pathlib.Path,required=True);a=ap.parse_args()
 raw=a.archive.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.sha256;run=json.loads(a.run.read_text())
 with zipfile.ZipFile(a.archive) as z:
  assert len(z.namelist())==len(set(z.namelist()));assert sum(x.file_size for x in z.infolist())<=32*1024**2
  assert all(pathlib.PurePosixPath(n).name==n for n in z.namelist())
  get=lambda n:json.loads(z.read(n+'.json'))
  assert z.read('freeze.txt').decode().strip()==run['head_sha']
  export=get('export');assert export['status']=='sanitized';assert set(z.namelist())=={r['file'] for r in export['files']}|{'export.json'}
  for r in export['files']:assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['public_sha256']
  result=get('result') if 'result.json' in z.namelist() else {'status':'runner_result_unavailable'};checks={}
  if result['status']=='ordinary_state_restore_checks_passed':
   assert run['status']=='completed' and run['conclusion']=='success';assert result['cleanup_complete'] is True
   assert result['scientific_cases']==0 and result['altered_inputs_executed'] is False
   for n in ['runtime-before','runtime-after']:assert get(n)['status']=='verified_unchanged' and get(n)['entries']==64235
   assert get('network-routes')==[] and all(r['ifname']=='lo' for r in get('network-interfaces'))
   assert z.read('node-version.txt').decode().strip()=='v24.11.1';assert 'postgres (PostgreSQL) 16.' in z.read('pg-versions.txt').decode();checks['runtime_storage_isolation']=True
   before=get('checkpoint-state');id=get('api-created')['id'];actor=get('checkpoint-actor')['user']['id']
   target=next(r for r in before['tables']['public.Url']['rows'] if r['id']==id);assert target['destination']=='https://example.com/api' and target['userId']==actor
   assert len(before['tables']['public.Url']['rows'])==2
   assert any(r['vanity']=='research-native' and r['destination']=='https://example.com/native' and r['userId']==actor for r in before['tables']['public.Url']['rows']);checks['independent_ordinary_readback']=True
   for n in ['checkpoint-repeat','checkpoint-after-backup','backup-logical-state','warm-before','restored-before-start','restored-start-state','restored-repeat','restored-before']:assert get(n)==before,n
   for table in ['public.File','public.Thumbnail','public.Invite']:assert before['tables'][table]['rows']==[]
   assert all(r['type']=='directory' for r in before['files']);checks['backup_and_starting_state']=True
   assert get('checkpoint-browser-identity')==get('restored-browser-identity');assert get('checkpoint-form')==get('restored-form');assert get('checkpoint-actor')==get('restored-actor');checks['browser_form_actor']=True
   for label in ['warm','restored']:
    assert normalize(get(label+'-after'),id,before)==before,label
    request=get(label+'-request');assert request=={'method':'PATCH','path':'/api/user/urls/'+id,'body':{'maxViews':None,'destination':'https://example.com/edited'}}
    assert get(label+'-response')['destination']=='https://example.com/edited'
    assert next(r for r in get(label+'-api-after') if r['id']==id)['destination']=='https://example.com/edited'
   checks['warm_restored_requests_and_frames']=True
  OUT.mkdir(exist_ok=True)
  for n in z.namelist():(OUT/n).write_bytes(z.read(n))
  summary={'status':'verified_success_evidence' if checks else 'failure_evidence_retained','run_id':run['id'],'freeze':run['head_sha'],'artifact_sha256':a.sha256,'recomputed_checks':checks,'observed_status':result['status'],'scientific_cases':0,'scope':'Ordinary PostgreSQL logical state/restore qualification only; no baseline or repair experiment.'}
  (OUT/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
