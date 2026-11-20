#!/usr/bin/env python3
"""Retain ordinary-control raw evidence and recompute successful readback checks."""
import argparse,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/redesign-zipline-ordinary-v3'
def main():
 p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('--sha256',required=True);a=p.parse_args()
 raw=a.archive.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.sha256
 with zipfile.ZipFile(a.archive) as z:
  assert len(z.namelist())==len(set(z.namelist()))
  assert sum(x.file_size for x in z.infolist())<=32*1024**2
  for n in z.namelist():assert pathlib.PurePosixPath(n).name==n and z.getinfo(n).file_size<=16*1024**2
  def get(n):return json.loads(z.read(n+'.json'))
  assert z.read('freeze.txt').decode().strip()=='7519d6c549c98c86a1d771a01f2a61535ec9634a'
  exported=get('export');assert exported['status']=='sanitized'
  assert set(z.namelist())=={r['file'] for r in exported['files']}|{'export.json'}
  for row in exported['files']:assert hashlib.sha256(z.read(row['file'])).hexdigest()==row['public_sha256']
  assert 'failure.html' not in z.namelist() and 'failure.png' not in z.namelist()
  checks={};result=get('result') if 'result.json' in z.namelist() else {'status':'runner_result_unavailable'}
  if result['status']=='ordinary_browser_api_checks_passed':
   inp=json.loads((ROOT/'development/redesign-zipline-ordinary-v3/input.json').read_text())
   assert result['scientific_cases']==0 and result['altered_inputs_executed'] is False
   assert get('api-token-response')=={'issued':True};actor=get('browser-actor');other=get('api-actor');assert actor['user']['id']==other['user']['id'];checks['same_actor']=True
   before=get('before');after=get('after');created=get('api-created');assert len(before)==len(after)==2
   b=next(x for x in before if x['id']==created['id']);v=next(x for x in after if x['id']==created['id'])
   assert b['userId']==actor['user']['id'];assert b['destination']==inp['api']['destination'] and b['vanity']==inp['api']['vanity']
   assert v['destination']==inp['edit_destination'];checks['intended_edit_readback']=True
   frame=lambda x:{k:v for k,v in x.items() if k not in ['destination','updatedAt']}
   assert frame(b)==frame(v);assert [x for x in before if x['id']!=created['id']]==[x for x in after if x['id']!=created['id']];checks['api_visible_frame']=True
   native=get('native-create-request');assert native['destination']==inp['native']['destination'] and native['vanity']==inp['native']['vanity']
   request=get('edit-request');assert request['method']=='PATCH' and request['url'].endswith('/api/user/urls/'+created['id']) and request['body']['destination']==inp['edit_destination']
   trace=get('trace');assert any(x['channel']=='browser-response' and x['phase']=='native_create' and x['url'].endswith('/api/user/urls') and x['status']==200 for x in trace)
   assert any(x['channel']=='browser-response' and x['url']==request['url'] and x['status']==200 for x in trace);checks['native_request_response_evidence']=True
   assert z.read('node-version.txt').decode().strip()=='v24.11.1'
   routes=get('network-routes');assert routes==[];interfaces=get('network-interfaces');assert all(x['ifname']=='lo' for x in interfaces);checks['loopback_only']=True
   captured=get('response-capture');assert all(x['capture']['status']!='pending' for x in captured);checks['capture_closed']=True
   assert any(x['url']==request['url'] and x['capture']['status']=='complete' and json.loads(x['capture']['body'])['destination']==inp['edit_destination'] for x in captured)
   assert any(x['phase']=='native_create' and x['url'].endswith('/api/user/urls') and x['capture']['status']=='complete' and isinstance(json.loads(x['capture']['body']),dict) and json.loads(x['capture']['body']).get('vanity')==inp['native']['vanity'] for x in captured);checks['required_native_response_bodies']=True
   assert get('bundle-verification')['runtime_sha256']=='dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8'
  OUT.mkdir(exist_ok=True)
  for n in z.namelist():(OUT/n).write_bytes(z.read(n))
 summary={'status':'verified_success_evidence' if checks else 'failure_evidence_retained','run_id':44733320228,'artifact_zip_sha256':a.sha256,'artifact_zip_bytes':len(raw),'observed_status':result['status'],'stage':result.get('stage'),'recomputed_checks':checks,'sanitized_export_verified':True,'scientific_cases':0,'scope':'Ordinary native/API feasibility and API-visible frame only; independent database readback, full-state restoration, baselines and repair causality unqualified.'}
 (OUT/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
