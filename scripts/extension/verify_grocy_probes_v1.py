#!/usr/bin/env python3
"""Reconstruct Grocy ordinary controls without conflating null and empty strings."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];REGISTRY=ROOT/'manifests/grocy-extension-probes-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,message):
    if not v:raise ValueError(message)
def check(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};flows={w['id']:w for w in reg['workflows']};records={};runs=set();commits=set();views=0
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():require(sha(ROOT/p)==h,'Source differs: '+p)
    require(sha(ROOT/reg['deployment_report'])==reg['deployment_report_sha256'],'Deployment differs')
    for folder in sorted(Path(root).iterdir()):
        pair=folder/'pair';r=read(pair/'report.json');u=r['unit'];require(u['id'] in units and u==units[u['id']] and u['id'] not in records,'Unit differs');require(r['registry_sha256']==sha(REGISTRY) and r['boundary_cases_executed']==0,'Scope differs');runs.add(r['run_identity']);commits.add(r['source_commit'])
        require({str(p.relative_to(pair)):sha(p) for p in pair.rglob('*') if p.is_file() and p.name!='report.json'}==r['files_sha256'],'Inventory differs')
        if r['status']!='ordinary_pair_passed':records[u['id']]={'qualified':False,'error':r.get('error'),'report_sha256':sha(pair/'report.json')};continue
        require(r['cleanup_confirmed'] and r['image']['id']==reg['image_id'] and r['actor_permissions']==reg['actor_permissions'],'Image/cleanup/role differs');w=flows[u['workflow']];observations=[]
        def canonical(k,v):return int(v) if k in w['integer_fields'] and type(v)is str and re.fullmatch(r'-?[0-9]+',v) else v
        def business(v):return {k:canonical(k,v[k]) for k in w['fields']}
        for channel in ('api','ui'):
            o=read(pair/channel/'observation.json');require(o['workflow']==w['id'] and o['channel']==channel and o['status']=='ordinary_control_passed' and o['browser_cleanup_confirmed'],'Branch differs');qs=o['requests'];info=[q for q in qs if q['path']=='/api/system/info'];require(len(info)==1 and info[0]['status']==200 and info[0]['response']['grocy_version']['Version']==reg['version'],'Version differs');initial=[q for q in qs if q['method']=='GET' and q['path']==w['collection']];require(len(initial)==1 and initial[0]['status']==200 and len(initial[0]['response'])==w['initial_count'],'Initial state differs')
            fixtures={}
            for f in w['fixtures']:
                before=[q for q in qs if q['method']=='GET' and q['path']==f['collection']];made=[q for q in qs if q['method']=='POST' and q['path']==f['collection']];require(len(before)==len(made)==1 and before[0]['status']==200 and isinstance(before[0]['response'],list) and made[0]['body']==f['payload'] and made[0]['status']==200,'Fixture differs');fixtures[f['id']]=int(made[0]['response']['created_object_id'])
            seed=lambda rows:sorted([{k:v for k,v in row.items() if k!='row_created_timestamp'} for row in rows],key=lambda row:row['id']);expected_seeds={w['collection']:seed(initial[0]['response'])};expected_seeds.update({f['collection']:seed(next(q['response'] for q in qs if q['method']=='GET' and q['path']==f['collection'])) for f in w['fixtures']});require(o['initial_business_state']['seed_collections']==expected_seeds and o['initial_business_state']['resource_count']==w['initial_count'],'Seed reconstruction differs');actor=o['initial_business_state']['actor_id'];payload={k:actor if v=='$actor' else fixtures[v[9:]] if type(v)is str and v.startswith('$fixture:') else v for k,v in w['payload'].items()};require(o['fixture_ids']==fixtures and o['resolved_payload']==payload,'Payload resolution differs')
            made=[q for q in qs if q['method']=='POST' and q['path']==w['collection']];require(len(made)==1 and made[0]['body']==payload and made[0]['status']==200,'Producer differs');resource=int(made[0]['response']['created_object_id']);require(o['resource_id']==resource,'Resource differs');path=w['collection']+'/'+str(resource);reads=[q for q in qs if q['method']=='GET' and q['path']==path];expected={**payload,w['edit_field']:w['edit_value']};require(len(reads)==(3 if channel=='ui' else 2) and all(q['status']==200 for q in reads) and business(reads[0]['response'])==o['prefix']==payload and business(reads[1]['response'])==o['final']==expected,'Persisted states differ')
            edits=[q for q in qs if q['method']=='PUT' and q['path']==path];require(len(edits)==1 and edits[0]['channel']==channel and edits[0]['status']==204,'Continuation differs')
            if channel=='api':require(edits[0]['body']==expected,'API full-record input differs')
            else:
                require(edits[0]['body'][w['edit_field']]==w['edit_value'],'Native edit differs');require([f['label'] for f in o['forms']]==['loaded','before_submit','fresh_final'],'Native stages differ')
                for form,values in zip(o['forms'],[payload,expected,expected]):
                    for binding in w['native_fields']:
                        key=binding['field'];found=[f for f in form['fields'] if f['name']==key];value=values[key]==1 if binding['kind']=='checkbox' else str(values[key]);require(len(found)==1 and found[0]['count']==1 and found[0]['selector']==binding['selector'] and found[0]['value']==value,'Native measurement differs: '+key)
                    views+=1
            if channel=='ui':
                probe=next(p for p in reg['probes'] if p['id']==u['probe']);observed=o['adapter_probe'];require(observed['id']==probe['id'] and observed['synthetic'] and observed['status']=='qualified' and observed['selector']==probe['selector'],'Probe binding differs');require(reads[2]['status']==200 and business(reads[2]['response'])==observed['persisted_after']==expected,'Probe changed persisted fields')
                if probe['kind']=='reference_inventory':require(not any(x['value']==probe['value'] for x in observed['options']) and any(x['value']==str(expected[probe['field']]) for x in observed['options']),'Option inventory differs')
                else:require(observed['field']['value']==probe['value'] and observed['field'][probe['reason']] is True and observed['field']['valid'] is False and observed['form_valid'] is False and observed['target_writes']==[] and observed['observation_window_ms']==1000,'Invalid-control measurement differs')
            observations.append(o)
        for key in ['initial_business_state','prefix','final','fixture_ids']:require(observations[0][key]==observations[1][key],'Pair differs: '+key)
        records[u['id']]={'qualified':True,'report_sha256':sha(pair/'report.json')}
    require(set(records)==set(units) and len(runs)==len(commits)==1,'Incomplete/mixed archive')
    return {'kind':'verified_grocy_synthetic_probes_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':records,'qualified_pairs':sum(r['qualified'] for r in records.values()),'native_form_views':views,'boundary_cases_executed':0,'boundary_execution_authorized':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=check(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
