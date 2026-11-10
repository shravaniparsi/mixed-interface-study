#!/usr/bin/env python3
"""Check ordinary controls against retained API/native traces, not runtime verdicts alone."""
import argparse,hashlib,json
import verify_vikunja_controls_v3 as project_verifier
import verify_vikunja_task_controls_v3 as task_verifier
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/vikunja-probes-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):
    x=json.loads(json.dumps(v))
    if x.get('subscription'):x['subscription'].pop('created',None)
    for k in ['created','updated']:x.pop(k,None)
    for key in ['owner','created_by']:
        if x.get(key):
            for k in ['created','updated']:x[key].pop(k,None)
    for view in x.get('views',[]):
        for k in ['created','updated']:view.pop(k,None)
    return x

def qualify(o,s):
    if o['status']!='ordinary_control_passed':return False
    task=s['id']=='task';v=task_verifier if task else project_verifier;adapted=json.loads(json.dumps(o))
    if o['channel']=='ui':
        p=o['synthetic_probe']
        if task:
            need(p['kind']=='deliberate_whitespace_title' and p['input']=='   ' and p['restored']=='Ordinary task' and p['target_requests']==0,'Task invalid editor probe')
            need(p['before']==o['prefix'] and p['persisted']==o['prefix'],'Probe preservation')
            path=s['collection']+'/'+str(o['prefix']['id']);indices=[i for i,r in enumerate(o['requests']) if r['method']=='GET' and r['path']==path]
            need(len(indices)==3 and o['requests'][indices[1]]['status']==200 and o['requests'][indices[1]]['response']==p['persisted'],'Probe raw readback')
            adapted['requests'].pop(indices[1])
        else:
            need(p['kind']=='detached_native_input_coercion' and p['color']['type']=='color','Color probe source')
            samples={r['input']:r for r in p['color']['samples']};need(len(samples)==7 and samples['#336699']['value']=='#336699' and samples['not-a-color']['value']!='not-a-color','Color coercion controls')
            if s['id']=='project':
                attrs=p['identifier']['attributes'];need(attrs=={'type':'text','maxLength':10,'required':False},'Actual identifier attributes')
                need(p['identifier']['valid_input']=='STUDY' and len(p['identifier']['valid_input'])<=attrs['maxLength'] and p['identifier']['violating_input']=='ABCDEFGHIJK' and len(p['identifier']['violating_input'])>attrs['maxLength'],'Length controls')
                need(all(f['identifier_attributes']['maxLength']==10 and f['identifier_attributes']['type']=='text' for f in o['forms']),'Loaded length attributes')
    prior=v.REGISTRY
    try:
        v.REGISTRY=REGISTRY
        return v.qualify(adapted,s)
    finally:v.REGISTRY=prior

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
