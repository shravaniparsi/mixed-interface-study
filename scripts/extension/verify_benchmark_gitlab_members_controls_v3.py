#!/usr/bin/env python3
"""Reconstruct the registered ordinary triple; preserve failed or missing branches."""
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44021434885
HEAD='789d064f8971fa5e34b839ce2b8032f753e22bef'
DIGEST='673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
BRANCHES=('native_native','api_native','api_api')
INITIAL=[{'id':2330,'access_level':50}]
FINAL=[{'id':5,'access_level':30},{'id':43,'access_level':30},{'id':2330,'access_level':50},{'id':2367,'access_level':30}]
FIELDS={'name','path','path_with_namespace','description','visibility','empty_repo','default_branch','issues_enabled','merge_requests_enabled','wiki_enabled','snippets_enabled','jobs_enabled','lfs_enabled','request_access_enabled','shared_runners_enabled','auto_devops_enabled','builds_access_level','repository_access_level','issues_access_level','merge_requests_access_level','namespace_id','owner_id'}
def state_checks(row):
    before=row.get('producer_state',{});after=row.get('final_state',{})
    return {
        'reported_pass':row.get('ordinary_control_passed') is True,
        'actor':row.get('actor')=={'id':2330,'username':'byteblaze'},
        'preflight':row.get('preflight_project_absent') is True and any(q.get('method')=='GET' and q.get('path')=='/api/v4/projects/byteblaze%2Fllm_bulk_inference' and q.get('status')==404 for q in row.get('api_requests',[])),
        'projection_complete':set(before)==FIELDS and set(after)==FIELDS,
        'requested_project':all(before.get(k)==v for k,v in {'name':'llm_bulk_inference','path':'llm_bulk_inference','path_with_namespace':'byteblaze/llm_bulk_inference','visibility':'private','empty_repo':True,'owner_id':2330}.items()),
        'project_preserved':bool(before) and before==after,
        'initial_members':row.get('initial_members')==INITIAL,
        'final_members':row.get('final_members')==FINAL,
        'browser_cleanup':row.get('browser_cleanup_confirmed') is True,
        'complete_stage':row.get('stage')=='complete' and not row.get('error_type'),
        'zero_scientific_cases':row.get('scientific_cases_executed')==0,
    }
def reconstruct(root):
    run=json.loads((root/'run.json').read_text())
    assert run['status']=='completed' and run['headSha']==HEAD
    assert run['databaseId']==RUN
    result={'kind':'benchmark_gitlab_members_controls_v3','run_id':RUN,'frozen_head':HEAD,'scientific_cases_executed':0,'ordinary_triple_qualified':False,'branches':[],'job_seconds':0,'paid_model_calls':0,'cleanup_limitation':'Container removal is attempted by the runtime trap; no post-removal readback is archived. Each branch uses a separate disposable hosted runner.'}
    rows=[];ids=[]
    for branch in BRANCHES:
        jobs=[j for j in run['jobs'] if j['name']==f'qualify ({branch})'];assert len(jobs)==1
        job=jobs[0];assert job['status']=='completed'
        parse=lambda value:datetime.fromisoformat(value.replace('Z','+00:00'))
        seconds=(parse(job['completedAt'])-parse(job['startedAt'])).total_seconds();assert seconds>=0
        result['job_seconds']+=seconds
        folder=root/f'gitlab-members-control-v3-{branch}-{RUN}'
        path=folder/'members-control.json'
        entry={'branch':branch,'job_seconds':seconds,'job_conclusion':job['conclusion'],'evidence_present':path.exists()}
        checks={'job_success':job['conclusion']=='success'}
        if path.exists():
            row=json.loads(path.read_text());assert row['kind']=='benchmark_gitlab_members_control_v3' and row['branch']==branch
            rows.append(row);checks.update(state_checks(row))
            if branch=='native_native':
                checks['exact_native_form_before_submit']=row.get('project_form_before_submit')=={'name':'llm_bulk_inference','path':'llm_bulk_inference','private':True,'readme':False,'sast':False}
            entry.update(stage=row.get('stage'),action=row.get('action'),error_type=row.get('error_type'),failure_path=row.get('failure_path'))
        else:checks['observation_present']=False
        for name,key,expected in [('head.txt','source_head',HEAD),('version.txt','application_version','15.7.5')]:
            p=folder/name;checks[key]=p.exists() and p.read_text().strip()==expected
        p=folder/'image-identity.txt';checks['image_digest']=p.exists() and '@sha256:'+DIGEST in p.read_text()
        p=folder/'readiness.json';checks['ready']=p.exists() and json.loads(p.read_text()).get('ready') is True
        p=folder/'container-id.txt';cid=p.read_text().strip() if p.exists() else '';checks['container_identity']=bool(re.fullmatch('[0-9a-f]{64}',cid));ids.append(cid)
        entry['checks']=checks;entry['qualified']=all(checks.values());result['branches'].append(entry)
    result['distinct_container_identities']=len(set(ids))==3 and all(ids)
    result['matched_business_states']=len(rows)==3 and all(all(row.get(k)==rows[0].get(k) for row in rows) and rows[0].get(k) is not None for k in ('producer_state','final_state','initial_members','final_members'))
    result['ordinary_triple_qualified']=bool(all(e['qualified'] for e in result['branches']) and result['distinct_container_identities'] and result['matched_business_states'])
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    result=reconstruct(a.archive.resolve());target=ROOT/'manifests/benchmark-gitlab-members-controls-v3.json'
    if a.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
