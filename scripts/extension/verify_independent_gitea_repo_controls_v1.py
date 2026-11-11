#!/usr/bin/env python3
"""Check ordinary controls against retained API/native traces, not runtime verdicts alone."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/independent-gitea-repo-controls-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):
    x=json.loads(json.dumps(v));x.pop('created_at',None);x.pop('updated_at',None)
    if x.get('owner'):
        x['owner'].pop('created',None);x['owner'].pop('last_login',None)
    return x

def qualify(o,s):
    if o['status']!='ordinary_control_passed' or not o.get('browser_cleanup_confirmed'):return False
    need(o['actor']['login']=='study-actor' and o['actor']['is_admin'] is False,'Actor')
    qs=o['requests'];actors=[q for q in qs if q['method']=='GET' and q['path']=='/api/v1/user'];versions=[q for q in qs if q['method']=='GET' and q['path']=='/api/v1/version'];need(len(actors)==1 and actors[0]['status']==200 and {k:actors[0]['response'][k] for k in ['id','login','is_admin']}==o['actor'],'Actor raw evidence');need(len(versions)==1 and versions[0]['status']==200 and versions[0]['response']==o['instance'] and o['instance']['version']=='28.3.0','Version raw evidence');initial=[q for q in qs if q['method']=='GET' and q['path']=='/api/v1/user/repos'];need(len(initial)==1 and initial[0]['status']==200 and initial[0]['response']==[],'Initial collection')
    need(o['initial_business_state']=={'actor':o['actor'],'resources':[]},'Initial state')
    made=[q for q in qs if q['method']=='POST' and q['path']=='/api/v1/user/repos'];need(len(made)==1 and made[0]['status']==201 and made[0]['body']==s['payload'],'Producer')
    raw=made[0]['response'];need(raw['owner']['id']==o['actor']['id'] and raw['full_name']=='study-actor/study-repo','Owned resource');path='/api/v1/repos/'+raw['full_name'];reads=[q for q in qs if q['method']=='GET' and q['path']==path];need(len(reads)==2 and all(q['status']==200 for q in reads),'Full readback');before,after=[q['response'] for q in reads];need(before==o['prefix'] and after==o['final'],'Recorded state')
    expected={**before,'description':s['edit_value']};body={k:expected[k] for k in s['fields']}
    if o['channel']=='api':
        edits=[q for q in qs if q['method']=='PATCH'];need(len(edits)==1 and edits[0]['path']==path and edits[0]['status']==200 and edits[0]['body']==body,'Full native-operation API projection')
    else:
        edits=o['native_requests'];need(len(edits)==1 and edits[0]['method']=='POST' and edits[0]['path']=='/'+raw['full_name']+'/settings' and edits[0]['status'] in (302,303),'Native write');entries=dict(edits[0]['form_entries']);need(entries['action']=='update' and entries['repo_name']==before['name'] and entries['description']==s['edit_value'] and entries['website']==before['website'] and ('template' in entries)==before['template'],'Native body')
        need([f['label'] for f in o['forms']]==['loaded','before_submit','fresh_final'],'Native snapshots')
        for form,values in zip(o['forms'],[before,expected,expected]):
            for f in s['native_fields']:
                found=[x for x in form['fields'] if x['name']==f['field']];need(len(found)==1 and found[0]['selector']==f['selector'] and found[0]['value']==values[f['field']],'Native measurement')
    a=dict(after);b=dict(expected);a.pop('updated_at',None);b.pop('updated_at',None);need(a==b,'Complete record preservation');need(business(before)==o['prefix_business'] and business(after)==o['final_business'],'Reset comparison');return True

def build(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};specs={s['id']:s for s in reg['workflows']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source: '+p)
    for p in sorted(Path(root).rglob('report.json')):
        r=read(p);u=r['unit'];uid=u['id'];need(uid in units and uid not in records and u==units[uid],'Unit inventory');need(r['registry_sha256']==sha(REGISTRY),'Registry');runs.add(r['run_identity']);commits.add(r['source_commit'])
        for rel,h in r['files_sha256'].items():need(sha(p.parent/rel)==h,'Raw hash')
        if 'image' in r:need(r['image']['id']==reg['image_id'],'Image')
        values={};branches={}
        for channel in ['api','ui']:
            f=p.parent/channel/'observation.json'
            if f.exists():values[channel]=read(f);branches[channel]=qualify(values[channel],specs[u['workflow']])
            else:branches[channel]=False
        paired=len(values)==2 and all(values['api'].get(k)==values['ui'].get(k) for k in ['initial_business_state','prefix_business','final_business'])
        records[uid]=dict(branches=branches,paired=paired,qualified=all(branches.values()) and paired and r.get('cleanup_confirmed',False),report_sha256=sha(p))
    need(set(records)==set(units),'Incomplete inventory');need(len(runs)==len(commits)==1,'Mixed source/run')
    return dict(kind='independent_gitea_repo_qualification_results_v1',run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,qualified_pairs=sum(r['qualified'] for r in records.values()),boundary_cases_executed=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
