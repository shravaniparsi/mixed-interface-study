#!/usr/bin/env python3
"""Reconstruct frozen README branches; never infer confirmed defects automatically."""
import argparse,copy,hashlib,json,re
from collections import Counter
from datetime import datetime
from pathlib import Path
from verify_benchmark_gitlab_readme_controls_v2 import state_checks,path_checks,FIELDS,EXPECTED
ROOT=Path(__file__).resolve().parents[2]
BRANCHES=('native_native','api_native','api_api')
DIGEST='673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
def qualified(row):
 if not row or not row.get('case_passed') or row.get('stage')!='complete':return False
 patch=row.get('optional_field_patch',{});before=row.get('producer_state',{})
 if patch.get('initialize_with_readme'):return False
 desc=before.get('description')
 if ('description' in patch and desc!=patch['description']) or ('description' not in patch and desc not in (None,'')):return False
 adjusted=copy.deepcopy(row);adjusted['ordinary_control_passed']=row['case_passed'];adjusted['scientific_cases_executed']=0
 checks=state_checks(adjusted);checks['initial_empty']=before.get('empty_repo') is True and before.get('default_branch')=='main'
 expected_body={'name':'nolan_young_fans','path':'nolan_young_fans','visibility':'private','initialize_with_readme':False,**patch}
 for q in adjusted.get('api_requests',[]):
  if q.get('method')=='POST' and q.get('path')=='/api/v4/projects':
   if q.get('body')!=expected_body:return False
   q['body']={'name':'nolan_young_fans','path':'nolan_young_fans','visibility':'private','initialize_with_readme':False}
 checks.update(path_checks(adjusted,row['branch']))
 if row['branch']=='native_native':checks['native_form']=row.get('project_form_before_submit')=={'name':'nolan_young_fans','path':'nolan_young_fans','private':True,'readme':False,'sast':False}
 checks['producer_snapshot']=row.get('producer_repository',{}).get('project')==before and row.get('producer_repository',{}).get('file') is None
 checks['final_snapshot']=row.get('final_repository',{}).get('project')==row.get('final_state') and (row.get('final_repository',{}).get('file') or {}).get('content')==EXPECTED
 return all(checks.values())
def classify(rows,controls):
 complete=all(rows.get(b) for b in BRANCHES);before=[rows[b].get('producer_state') for b in BRANCHES] if complete else []
 matched=bool(before and before[0] is not None and all(x==before[0] for x in before));passed={b:qualified(rows.get(b)) for b in BRANCHES};candidate=False
 if not complete:cat='incomplete_triple'
 elif not controls:cat='unqualified_batch_controls'
 elif any(r.get('actor')!={'id':2330,'username':'byteblaze'} or not r.get('preflight_project_absent') for r in rows.values()):cat='reset_or_actor_verification_failure'
 elif rows['native_native'].get('native_representability')=='unsupported_explicit_description':
  r=rows['native_native'];valid=r.get('native_description_field_count')==0 and r.get('scientific_cases_executed')==0 and r.get('producer_state') is None and 'description' in r.get('optional_field_patch',{}) and not any(q.get('method')=='POST' and q.get('path')=='/projects' for q in r.get('native_writes',[]))
  cat='native_input_not_representable' if valid else 'invalid_representability_evidence'
 elif any(r.get('optional_field_patch',{}).get('initialize_with_readme') is True for r in rows.values()):cat='lifecycle_control_requires_separate_interpretation'
 elif any(x is None for x in before):cat='producer_rejection_or_instrument_failure'
 elif not matched:cat='producer_state_mismatch'
 elif all(passed.values()):cat='all_paths_preserve'
 else:
  r=rows['api_native'];snap=r.get('failure_repository',{});project=snap.get('project');pid=r.get('project_id');paths={f'/api/v4/projects/{pid}/repository/commits','/api/v4/projects/byteblaze%2Fnolan_young_fans/repository/commits'}
  http=any(q.get('method')=='POST' and q.get('path') in paths and q.get('status',0)>=400 for q in r.get('native_writes',[]))
  mutation=any(q.get('method')=='POST' and q.get('path') in paths for q in r.get('native_writes',[]))
  changed=bool(project and set(project)==FIELDS and mutation and (project!=r.get('producer_state') or snap.get('file')!=r.get('producer_repository',{}).get('file')))
  candidate=passed['native_native'] and passed['api_api'] and not passed['api_native'] and r.get('stage')=='continuation' and (http or changed)
  cat='candidate_incremental_signal_requires_review' if candidate else 'continuation_or_instrument_failure'
 return {'classification':cat,'producer_states_equal':matched,'branch_pass':passed,'candidate_incremental_signal':bool(candidate),'confirmed_natural_defect':False}
def reconstruct(archive,head,run_id):
 run=json.loads((archive/'run.json').read_text());assert run['status']=='completed' and run['headSha']==head and run['databaseId']==run_id
 reg=json.loads((ROOT/'manifests/benchmark-gitlab-readme-execution-v1.json').read_text())
 for f,h in reg['source_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
 jobs={j['name']:j for j in run['jobs']};assert set(jobs)=={'execute (1)','execute (2)'}
 specs={c['id']:c for c in reg['cases']};out={'kind':'benchmark_gitlab_readme_results_v1','run_id':run_id,'head_sha':head,'scheduled_specifications':6,'scheduled_triples':12,'scheduled_scientific_branches':36,'scheduled_control_branches':4,'production_phase_entries':0,'controls_observed':0,'scientific_branch_records':0,'job_seconds':0,'paid_model_calls':0,'confirmed_natural_defects':0,'repetitions':[],'triples':[]};ids=[]
 for rep in (1,2):
  job=jobs[f'execute ({rep})'];assert job['status']=='completed';dt=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'));seconds=(dt(job['completedAt'])-dt(job['startedAt'])).total_seconds();assert seconds>=0;out['job_seconds']+=seconds
  folder=archive/f'gitlab-readme-inputs-r{rep}-{run_id}';file=folder/'batch.json';batch=json.loads(file.read_text()) if file.exists() else None
  schedule=next(x for x in reg['schedules'] if x['repetition']==rep)['executions'];rows={};entries={}
  image=folder/'image-identity.txt';identity=image.exists() and '@sha256:'+DIGEST in image.read_text()
  if batch:
   assert batch['source_commit']==head and int(batch['run_id'])==run_id and batch['repetition']==rep
   seen=set()
   for entry in batch['executions']:
    i=entry['index'];assert i not in seen and 0<=i<len(schedule);seen.add(i);assert all(entry[k]==schedule[i][k] for k in ('case_id','branch','role'))
    key=(entry['case_id'],entry['branch']);entries[key]=entry
    cid=entry.get('container_id')
    if cid:assert re.fullmatch('[0-9a-f]{64}',cid);ids.append(cid)
    assert entry['folder']==f'{i:02d}'
    f=folder/entry['folder']/'readme-case.json'
    if f.exists():
     row=json.loads(f.read_text());assert row['case_id']==key[0] and row['branch']==key[1] and row['case_role']==entry['role'] and row['optional_field_patch']==specs[key[0]]['optional_field_patch'];rows[key]=row
     assert row['scientific_cases_executed'] in (0,1);out['production_phase_entries']+=row['scientific_cases_executed'];out['controls_observed']+=int(entry['role']=='control');out['scientific_branch_records']+=int(entry['role']=='scientific')
  def clean(key,success=False):
   e=entries.get(key,{});return bool(identity and e.get('container_id') and e.get('container_removed') is True and e.get('browser_cleanup_confirmed') is True and type(e.get('process_exit_code')) is int and (not success or e.get('process_exit_code')==0))
  controls=bool(batch and batch['status']=='completed' and all(qualified(rows.get((c,'native_native'))) and clean((c,'native_native'),True) for c in ('control_start','control_end')))
  out['repetitions'].append({'repetition':rep,'job_seconds':seconds,'job_conclusion':job['conclusion'],'batch_status':batch['status'] if batch else 'missing','controls_passed':controls,'recorded_executions':len(rows)})
  for case in (x for x in reg['cases'] if x['role']=='scientific'):
   group={b:rows.get((case['id'],b)) for b in BRANCHES};v=classify(group,controls)
   if all(group.values()) and not all(clean((case['id'],b),v['branch_pass'][b]) for b in BRANCHES):v.update(classification='process_or_cleanup_failure',candidate_incremental_signal=False)
   v.update(case_id=case['id'],repetition=rep,observed_branches=[b for b in BRANCHES if group[b]]);out['triples'].append(v)
 assert len(ids)==len(set(ids)),'Fresh container reused'
 out.update(container_count=len(ids),container_ids_unique=True,classification_counts=dict(Counter(x['classification'] for x in out['triples'])),candidate_incremental_signals=sum(x['candidate_incremental_signal'] for x in out['triples']))
 out['scheduled_execution_complete']=out['scientific_branch_records']==36 and out['controls_observed']==4 and all(r['controls_passed'] and r['recorded_executions']==20 for r in out['repetitions'])
 out['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()};return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--expected-head',required=True);p.add_argument('--run-id',type=int,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();v=reconstruct(a.archive.resolve(),a.expected_head,a.run_id);target=ROOT/'manifests/benchmark-gitlab-readme-results-v1.json'
 if a.verify:assert json.loads(target.read_text())==v
 else:target.write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({k:v for k,v in v.items() if k not in ('source_sha256','triples')},indent=2))
