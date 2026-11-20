#!/usr/bin/env python3
import argparse,copy,datetime,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def put(x,pointer,value):
 parts=pointer.strip('/').split('/');parent=x
 for key in parts[:-1]:parent=parent[int(key)] if isinstance(parent,list) else parent[key]
 parent[parts[-1]]=value

def verify_frame(before,after,id,changes):
 expected=copy.deepcopy(before);actual=copy.deepcopy(after);prior=expected['tables']['public.Url'];table=actual['tables']['public.Url']
 ids=[r['id'] for r in prior['rows']];rows={r['id']:r for r in table['rows']}
 assert len(ids)==len(set(ids))==len(rows)==len(table['rows']) and set(ids)==set(rows)
 assert before['tables']['public.Url']['row_sha256']==[digest(r) for r in before['tables']['public.Url']['rows']]
 old=next(r for r in prior['rows'] if r['id']==id);target=rows[id]
 assert datetime.datetime.fromisoformat(target['updatedAt'].replace('Z','+00:00'))>=datetime.datetime.fromisoformat(old['updatedAt'].replace('Z','+00:00'))
 target['updatedAt']=old['updatedAt']
 for p,v in changes.items():put(old,p,v)
 table['rows']=[rows[key] for key in ids]
 for t in [prior,table]:t['row_sha256']=[digest(r) for r in t['rows']]
 assert actual==expected,'collateral state or missing intended change'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);ap.add_argument('--sha256',required=True);ap.add_argument('--run',type=pathlib.Path,required=True);a=ap.parse_args()
 assert hashlib.sha256(a.archive.read_bytes()).hexdigest()==a.sha256;run=json.loads(a.run.read_text());inp=json.loads((ROOT/'development/redesign-zipline-rehearsal-v2/input.json').read_text())
 checks={}
 with zipfile.ZipFile(a.archive) as z:
  names=z.namelist();assert len(names)==len(set(names));assert all(pathlib.PurePosixPath(n).name==n for n in names);assert sum(i.file_size for i in z.infolist())<=32*1024**2
  get=lambda n:json.loads(z.read(n+'.json'));assert z.read('freeze.txt').decode().strip()==run['head_sha'];export=get('export');assert export['status']=='sanitized';assert set(names)=={r['file'] for r in export['files']}|{'export.json'}
  for r in export['files']:assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['public_sha256']
  result=get('result') if 'result.json' in names else {'status':'result_unavailable'}
  if result['status']=='ordinary_actions_rehearsed':
   assert run['status']=='completed' and run['conclusion']=='success';assert result['cleanup_complete'] and result['scientific_cases']==0 and result['altered_inputs_executed'] is False
   assert get('infra-00-result')['status']=='completed' and get('infra-00-result')['shutdown_verified']
   for name in ['runtime-before','runtime-after']:assert get(name)['status']=='verified_unchanged' and get(name)['entries']==64235
   assert get('network-routes')==[] and all(r['ifname']=='lo' for r in get('network-interfaces'));assert z.read('node-version.txt').decode().strip()=='v24.11.1'
   before=get('checkpoint-state');id=get('api-created')['id'];actor=get('checkpoint-actor')['user']['id'];rows=before['tables']['public.Url']['rows'];assert len(rows)==2
   target=next(r for r in rows if r['id']==id);native=next(r for r in rows if r['id']!=id)
   for key,value in inp['api'].items():assert target[key]==value,key
   assert target['userId']==native['userId']==actor;assert native['destination']==inp['native']['destination'] and native['vanity']==inp['native']['vanity'];assert native['discordComponentEmbed']==inp['api']['discordComponentEmbed']
   for n in ['checkpoint-repeat','checkpoint-after-backup','backup-logical-state','schema-after']:assert get(n)==before,n
   for name in ['public.File','public.Thumbnail','public.Invite']:assert before['tables'][name]['rows']==[]
   assert all(r['type']=='directory' for r in before['files']);checks['ordinary_shape_backup_runtime']=True
   fields=inp['fields'];planned=[dict(label='branch-00',target=fields[0]['pointer'],repair=False,warm=True),dict(label='branch-01',target=fields[0]['pointer'],repair=False,replicate=True),dict(label='branch-02',target=fields[0]['pointer'],repair=True)]
   for i,f in enumerate(fields[1:],1):planned.extend([dict(label=f'branch-{i*2+1:02d}',target=f['pointer'],repair=False),dict(label=f'branch-{i*2+2:02d}',target=f['pointer'],repair=True)])
   planned.extend(dict(label=f'branch-{i+9:02d}',target=f['pointer'],repair=False,field_change=True) for i,f in enumerate(fields))
   assert get('planned-branches')==planned;completed=get('completed-branches');assert len(completed)==len(planned)==13
   for item,done in zip(planned,completed):
    assert all(done[k]==v for k,v in item.items());label=item['label'];field=next(f for f in fields if f['pointer']==item['target']);other=next(f for f in fields if f['pointer']==field['unrelated_pointer'])
    changes={field['pointer']:field['replacement']} if item.get('field_change') else {other['pointer']:other['replacement'],**({field['pointer']:field['ordinary']} if item['repair'] else {})};assert done['changes']==changes
    for suffix in ['before','preflight-after','reset-state']:assert get(label+'-'+suffix)==before
    if not item.get('warm'):
     for suffix in ['before-start','start','repeat']:assert get(label+'-'+suffix)==before
     for suffix,base in [('browser-identity','checkpoint-browser-identity'),('form','checkpoint-form'),('actor','checkpoint-actor')]:assert get(label+'-'+suffix)==get(base)
    for suffix,base in [('browser-identity','checkpoint-browser-identity'),('form','checkpoint-form'),('actor','checkpoint-actor')]:assert get(label+'-reset-'+suffix)==get(base)
    expected=copy.deepcopy(target)
    for p,v in changes.items():put(expected,p,v)
    body={'maxViews':None,'discordComponentEmbed':expected['discordComponentEmbed']}
    for key in ['destination','vanity']:
     if expected[key]!=target[key]:body[key]=expected[key]
    request={'method':'PATCH','path':'/api/user/urls/'+id,'body':body};assert get(label+'-preflight-request')==get(label+'-request')==done['request']==request
    abort=get(label+'-abort');assert abort['method']=='PATCH' and abort['path']==request['path'] and 'ERR_BLOCKED_BY_CLIENT' in abort['failure']['errorText']
    verify_frame(before,get(label+'-after'),id,changes)
    for observed in [get(label+'-response'),next(r for r in get(label+'-api-after') if r['id']==id)]:
     for key in ['destination','vanity','discordComponentEmbed']:assert observed[key]==expected[key]
   assert get('branch-00-request')==get('branch-01-request');checks['all_13_frames_preflights_controls_and_restores']=True
   schema=get('schema-baseline');assert schema['status']=='qualified' and schema['handlers_invoked'] is False and schema['live_altered_producers']==0
   sr=schema['rows'];assert [r['accepted'] for r in sr]==[True,True,True,False,True];assert sr[0]['input']==sr[0]['value']==inp['api'];assert sr[2]['input']==sr[2]['value']==get('branch-00-request')['body'];assert sr[3]['input']['destination'] is None and sr[3]['errors'];assert sr[4]['value']['vanity']=='schema-calibration';checks['original_schema_full_fixture']=True
  out=ROOT/'results/redesign-zipline-rehearsal-v2';out.mkdir(exist_ok=True)
  for n in names:(out/n).write_bytes(z.read(n))
  summary={'status':'verified_ordinary_rehearsal' if checks else 'failure_evidence_retained','run_id':run['id'],'freeze':run['head_sha'],'artifact_sha256':a.sha256,'checks':checks,'observed_status':result['status'],'scientific_cases':0};(out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
