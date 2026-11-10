#!/usr/bin/env python3
"""Reconstruct ordinary paired controls from recorded API and native form evidence."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];REGISTRY=ROOT/'manifests/linkding-extension-controls-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,message):
    if not v:raise ValueError(message)
def check(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};flows={w['id']:w for w in reg['workflows']};records={};runs=set();commits=set();form_views=0
    for path,h in reg['source_sha256'].items():require(sha(ROOT/path)==h,'Source changed: '+path)
    require(sha(ROOT/reg['deployment_report'])==reg['deployment_report_sha256'],'Deployment evidence changed')
    for folder in sorted(Path(root).iterdir()):
        require(folder.is_dir(),'Unexpected archive item');pair=folder/'pair';r=read(pair/'report.json');u=r['unit'];uid=u['id'];require(uid in units and uid not in records and u==units[uid],'Foreign/duplicate unit')
        require(r['registry_sha256']==sha(REGISTRY) and r['boundary_cases_executed']==0,'Registry/scope differs')
        actual={str(p.relative_to(pair)):sha(p) for p in sorted(pair.rglob('*')) if p.is_file() and p.name!='report.json'}
        require(actual==r['files_sha256'],'Evidence inventory differs');runs.add(r['run_identity']);commits.add(r['source_commit'])
        if r['status']!='ordinary_pair_passed':
            records[uid]={'qualified':False,'error':r.get('error'),'report_sha256':sha(pair/'report.json')};continue
        require(r['cleanup_confirmed'],'Container cleanup missing');require(r['image']['id']==reg['image_id'],'Image differs')
        w=flows[u['workflow']];expected={**w['payload'],w['edit_field']:w['edit_value']};observations=[]
        def business(x):return {k:x[k] for k in w['fields']}
        for channel in u['branch_order']:
            o=read(pair/channel/'observation.json');require(o['workflow']==w['id'] and o['channel']==channel and o['status']=='ordinary_control_passed' and o['browser_cleanup_confirmed'],'Branch status differs')
            requests=o['requests'];created=[q for q in requests if q['channel']=='api' and q['method']=='POST'];require(len(created)==1 and created[0]['body']==w['payload'] and created[0]['status']==201,'Producer request differs')
            resource=created[0]['response']['id'];require(type(resource)is int and resource==o['resource_id'],'Resource binding differs');resource_path=w['collection']+str(resource)+'/'
            reads=[q for q in requests if q['channel']=='api' and q['method']=='GET' and q['path']==resource_path];require(len(reads)==2 and all(q['status']==200 for q in reads),'Persisted reads missing')
            require(business(reads[0]['response'])==w['payload'] and business(reads[1]['response'])==expected,'Persisted state differs')
            require(o['prefix']==w['payload'] and o['final']==expected,'Normalized state differs')
            edits=[q for q in requests if q['method'] in ('PATCH','POST') and q is not created[0]]
            require(len(edits)==1 and edits[0]['channel']==channel,'Continuation count differs')
            if channel=='api':require(edits[0]['path']==resource_path and edits[0]['status']==200 and edits[0]['body']=={w['edit_field']:w['edit_value']},'API continuation differs')
            else:
                require(edits[0]['path']==w['edit_path'].replace('{id}',str(resource)) and edits[0]['status'] in (200,302,303),'Native submission differs')
                posted={k:v for k,v in edits[0]['body']};require(posted[w['edit_field']]==w['edit_value'],'Wrong native edit input')
                require([f['label'] for f in o['forms']]==['loaded','fresh_final'],'Native view stages differ')
                for f,values in zip(o['forms'],[w['payload'],expected]):
                    for key in w['form_fields']:
                        found=[x for x in f['fields'] if x['name']==key];require(len(found)==1 and found[0]['value']==values[key],'Native field measurement differs: '+key)
                    form_views+=1
            observations.append(o)
        for key in ('initial_business_state','prefix','final'):require(observations[0][key]==observations[1][key],'Paired state differs')
        records[uid]={'qualified':True,'report_sha256':sha(pair/'report.json')}
    require(set(records)==set(units),'Incomplete control inventory');require(len(runs)==len(commits)==1,'Mixed attempts')
    return {'kind':'verified_linkding_ordinary_controls_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':records,'qualified_pairs':sum(r['qualified'] for r in records.values()),'native_form_views':form_views,'boundary_cases_executed':0,'boundary_execution_authorized':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=check(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Already registered');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
