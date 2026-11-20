#!/usr/bin/env python3
import argparse,copy,hashlib,importlib.util,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualified_frame',ROOT/'scripts/extension/verify_redesign_zipline_rehearsal_v3.py');frame_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(frame_module)
canonical=frame_module.canonical;digest=frame_module.digest

def same_creation(before,after,id):
 x=copy.deepcopy(after);table=x['tables']['public.Url'];prior=before['tables']['public.Url'];ids=[r['id'] for r in prior['rows']]
 assert len(ids)==len(set(ids));assert len(table['rows'])==len(ids)+1 and sum(r['id']==id for r in table['rows'])==1
 remaining={r['id']:r for r in table['rows'] if r['id']!=id};assert set(remaining)==set(ids) and len(remaining)==len(ids)
 table['rows']=[remaining[k] for k in ids];table['row_sha256']=[digest(r) for r in table['rows']];assert x==before

def correct_frame(before,after,id,changes):
 try:frame_module.verify_frame(before,after,id,changes);return True
 except (AssertionError,KeyError,ValueError,TypeError,IndexError):return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);ap.add_argument('--sha256',required=True);ap.add_argument('--run',type=pathlib.Path,required=True);a=ap.parse_args()
 assert hashlib.sha256(a.archive.read_bytes()).hexdigest()==a.sha256;run=json.loads(a.run.read_text());inp=json.loads((ROOT/'development/redesign-zipline-scientific-v1/input.json').read_text());summary={'run_id':run['id'],'freeze':run['head_sha'],'artifact_sha256':a.sha256,'planned_projects':1,'planned_workflows':1,'evaluation':False,'status':'incomplete_evidence_retained'}
 with zipfile.ZipFile(a.archive) as z:
  names=z.namelist();assert len(names)==len(set(names));assert all(pathlib.PurePosixPath(n).name==n for n in names);assert sum(i.file_size for i in z.infolist())<=32*1024**2
  get=lambda n:json.loads(z.read(n+'.json'));assert z.read('freeze.txt').decode().strip()==run['head_sha'];export=get('export');assert export['status']=='sanitized';assert set(names)=={r['file'] for r in export['files']}|{'export.json'}
  for row in export['files']:assert hashlib.sha256(z.read(row['file'])).hexdigest()==row['public_sha256']
  result=get('result') if 'result.json' in names else {'status':'result_unavailable'};summary['observed_status']=result['status'];summary['producer_attempts_reported']=result.get('producer_attempts',0)
  if result['status']=='scientific_schedule_completed':
   assert run['status']=='completed' and run['conclusion']=='success';assert result['cleanup_complete'] and result['producer_attempts']==9 and result['altered_inputs_executed'] is True
   assert get('infra-00-result')['status']=='completed' and get('infra-00-result')['shutdown_verified']
   for label in ['runtime-before','runtime-after']:assert get(label)['status']=='verified_unchanged' and get(label)['entries']==64235
   assert get('network-routes')==[] and all(r['ifname']=='lo' for r in get('network-interfaces'));assert z.read('node-version.txt').decode().strip()=='v24.11.1'
   root=get('root-state');assert len(root['tables']['public.Url']['rows'])==1;native=root['tables']['public.Url']['rows'][0];actor=get('root-actor')['user']['id'];assert native['userId']==actor
   assert native['destination']==inp['native']['destination'] and native['vanity']==inp['native']['vanity'] and native['discordComponentEmbed']==inp['api']['discordComponentEmbed']
   for label in ['root-repeat','root-after-schema','root-after-backup','root-backup-state']:assert get(label)==root
   schemas=get('producer-schema');assert schemas['status']=='observed' and schemas['handlers_invoked'] is False and len(schemas['rows'])==9
   observed=get('producers');branches=get('branches');assert len(observed)==len(inp['producers'])==9;assert len({b['label'] for b in branches})==len(branches)
   scored=[];expected_branch_labels=[];pairs=[]
   def start_matches(label,cp,cp_label,warm=False):
    if not warm:
     assert get(label+'-before-start')==cp;assert get(label+'-repeat')==cp
    assert get(label+'-state')==cp
    for suffix in ['browser-identity','form','actor']:assert get(label+'-'+suffix)==get(cp_label+'-'+suffix)
   def score_branch(label,cp,cp_label,id,field,repair,warm=False):
    expected_branch_labels.append(label);b=next(b for b in branches if b['label']==label);assert b['target']==field['pointer'] and b['repair']==repair and b['warm']==warm
    other=next(f for f in inp['fields'] if f['pointer']==field['unrelated_pointer']);changes={other['pointer']:other['replacement'],**({field['pointer']:field['ordinary']} if repair else {})};assert b['changes']==changes;start_matches(label,cp,cp_label,warm)
    if b['status']=='preflight_unavailable':assert b.get('error');assert label+'-preflight-failure-state.json' in names;return b['status']
    assert get(label+'-preflight-after')==cp and get(label+'-schema-after')==cp
    d=get(label+'-preflight-request');abort=get(label+'-abort');assert d['method']=='PATCH' and d['path']=='/api/user/urls/'+id;assert abort['method']==d['method'] and abort['path']==d['path'] and 'ERR_BLOCKED_BY_CLIENT' in abort['failure']['errorText']
    s=get(label+'-schema');assert s['handlers_invoked'] is False and s['rows'][0]['input']==d['body']
    assert get(label+'-reset-state')==cp
    for suffix in ['browser-identity','form','actor']:assert get(label+'-reset-'+suffix)==get(cp_label+'-'+suffix)
    if b['status']=='native_observation_unavailable':assert b.get('error');assert label+'-unavailable-state.json' in names;return b['status']
    u=get(label+'-request');response=get(label+'-response');after=get(label+'-after');assert b['http_status']==response['status'];assert b['preflight_request_agreement']==(d==u)
    valid=correct_frame(cp,after,id,changes);assert b['frame_valid']==valid
    status=('intended_edit_persisted' if valid else 'persistence_or_frame_mismatch') if 200<=response['status']<300 else ('native_request_rejected' if cp==after else 'write_after_rejection')
    assert b['status']==status
    readback=get(label+'-api-after');assert readback['method']=='GET' and readback['route']=='/api/user/urls'
    return status
   for index,(producer,obs,s) in enumerate(zip(inp['producers'],observed,schemas['rows'])):
    p='p'+str(index);assert obs['index']==index and obs['id']==producer['id'];assert obs['target']==producer.get('target') and obs['operation']==producer.get('operation','ordinary')
    assert s['name']==producer['id'] and s['input']==producer['body'] and s['method']=='POST' and s['path']=='/api/user/urls' and s['httpPart']=='body';assert obs['schema_accepted']==s['accepted']
    start_matches(p+'-root',root,'root');before=get(p+'-producer-before');after=get(p+'-producer-after');assert before==root
    response=get(p+'-producer-response');assert response['method']=='POST' and response['route']=='/api/user/urls' and response['body']==producer['body'];assert obs['http_status']==response['status']
    if not 200<=response['status']<300:
     assert obs['status']=='producer_rejected_unchanged' and after==before;scored.append({'id':producer['id'],'status':obs['status'],'schema_accepted':s['accepted']});continue
    assert obs['status']=='accepted_persisted';id=response['json']['id'];assert response['parsed'];record=next(r for r in after['tables']['public.Url']['rows'] if r['id']==id);assert record==obs['persisted'] and record['userId']==actor and obs['record_id']==id;same_creation(before,after,id)
    entry={'id':producer['id'],'status':obs['status'],'schema_accepted':s['accepted'],'continuation':obs.get('continuation')};scored.append(entry)
    if obs.get('continuation')=='editor_or_checkpoint_unavailable':assert index>0 and obs.get('error') and p+'-editor-failure-state.json' in names;continue
    assert obs['continuation']=='fixed_schedule_observed'
    for suffix in ['editor-state','repeat','after-backup','backup-state']:assert get(p+'-'+suffix)==after
    assert get(p+'-actor')['user']['id']==actor
    targets=inp['fields'] if index==0 else [next(f for f in inp['fields'] if f['pointer']==producer['target'])]
    if index==0:assert score_branch(p+'-warm',after,p,id,targets[0],False,True)=='intended_edit_persisted'
    for field_index,field in enumerate(targets):
     sham=score_branch(p+f'-b{field_index}-sham',after,p,id,field,False);repair=score_branch(p+f'-b{field_index}-repair',after,p,id,field,True)
     if index==0:assert sham==repair=='intended_edit_persisted'
     pairs.append({'producer_id':producer['id'],'target':field['pointer'],'sham':sham,'repair':repair,'fixed_repair_restored_edit':sham=='native_request_rejected' and repair=='intended_edit_persisted'})
    if index==0:assert get(p+'-warm-request')==get(p+'-b0-sham-request')
   assert set(expected_branch_labels)=={b['label'] for b in branches}
   summary.update(status='verified_scientific_schedule',independent_projects=1,independent_workflows=1,producer_observations=scored,branch_pairs=pairs,producer_count=9,branch_count=len(branches),accepted_producers=sum(p['status']=='accepted_persisted' for p in scored),rejected_producers=sum(p['status']=='producer_rejected_unchanged' for p in scored),repair_restoration_pairs=sum(p['fixed_repair_restored_edit'] for p in pairs),interpretation='One development workflow; correlated inputs/branches, no independent evaluation or Q1-readiness claim.')
  out=ROOT/'results/redesign-zipline-scientific-v1';out.mkdir(exist_ok=True)
  for name in names:(out/name).write_bytes(z.read(name))
  (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
