#!/usr/bin/env python3
"""Check ordinary controls against retained API/native traces, not runtime verdicts alone."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/vikunja-controls-v3.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):
    x=json.loads(json.dumps(v))
    for k in ['created','updated']:x.pop(k,None)
    for key in ['owner','created_by']:
        if x.get(key):
            for k in ['created','updated']:x[key].pop(k,None)
    for view in x.get('views',[]):
        for k in ['created','updated']:view.pop(k,None)
    return x

def qualify(o,s):
    if o['status']!='ordinary_control_passed' or not o.get('browser_cleanup_confirmed'):return False
    need(o['actor']['username']=='study-actor' and o['actor']['is_admin'] is False,'Ordinary actor')
    initial=[r for r in o['requests'] if r['method']=='GET' and r['path']==s['collection']]
    need(len(initial)==1 and initial[0]['status']==200 and initial[0]['response']==o['initial_raw'],'Initial raw collection')
    raw=initial[0]['response'];need(o['initial_business_state']=={**raw,'items':[business(v) for v in raw['items']]},'Initial projection')
    requests=o['requests'];users=[r for r in requests if r['method']=='GET' and r['path']=='/api/v2/user']
    need(len(users)==1 and users[0]['status']==200 and users[0]['response']['id']==o['actor']['id'] and users[0]['response']['is_admin'] is False,'Actor raw proof')
    creates=[r for r in requests if r['method']=='POST' and r['path']==s['collection']];need(len(creates)==1 and creates[0]['status']==201 and creates[0]['body']==s['payload'],'Producer')
    path=s['collection']+'/'+str(creates[0]['response']['id']);reads=[r for r in requests if r['method']=='GET' and r['path']==path]
    need(len(reads)==2 and all(r['status']==200 for r in reads),'Read inventory');prefix,final=[r['response'] for r in reads]
    need(prefix==o['prefix'] and final==o['final'],'Raw readback');need(prefix[s['owner_field']]['id']==o['actor']['id'],'Owner')
    want=dict(prefix,title=s['edit_value']);body={k:want[k] for k in s['fields']}
    if o['channel']=='api':
        writes=[r for r in requests if r['method']=='PUT' and r['path']==path];need(len(writes)==1 and writes[0]['status']==200 and writes[0]['body']==body,'Full API update')
    else:
        captured=o['fetch_requests'];need(len(captured)==1 and captured[0]['method']=='PUT' and captured[0]['path']==path and captured[0]['status']==200 and json.loads(captured[0]['body'])==body,'Fetch clone body')
        writes=json.loads(json.dumps(o['native_requests']))
        need(len(writes)==1 and (writes[0]['body'] is None or writes[0]['body']==captured[0]['body']),'Transport body consistency')
        writes[0]['body']=captured[0]['body'];need(len(writes)==1 and writes[0]['path']==path and writes[0]['method']=='PUT' and writes[0]['status']==200 and json.loads(writes[0]['body'])==body,'Native update')
        forms=o['forms'];need([f['label'] for f in forms]==['loaded','before_submit','fresh_final'],'Native view inventory')
        need(forms[0]['title']==prefix['title'] and all(f['title']==s['edit_value'] for f in forms[1:]),'Native title')
        need(all('Ordinary description' in f['description_text'] and f['color'].lower()=='#336699' for f in forms),'Native preserved fields')
        if s['id']=='project':need(all(f['identifier']==prefix['identifier'] for f in forms),'Native identifier')
    a=dict(final);b=dict(want);a.pop('updated',None);b.pop('updated',None);need(a==b,'Full record preservation')
    need(business(prefix)==o['prefix_business'] and business(final)==o['final_business'],'Business projection')
    return True

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
    return dict(kind='vikunja_ordinary_qualification_results_v1',run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,qualified_pairs=sum(r['qualified'] for r in records.values()),boundary_cases_executed=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
