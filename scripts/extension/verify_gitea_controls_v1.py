#!/usr/bin/env python3
"""Independent native-form/API reconstruction for ordinary Gitea controls."""
import argparse,hashlib,json
from pathlib import Path
from urllib.parse import parse_qsl
from email.parser import BytesParser
from email.policy import default
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):return {k:x for k,x in v.items() if k not in ['created_at','updated_at']}
def preserve(v):return {k:x for k,x in v.items() if k!='updated_at'}
def form_entries(body,content_type):
    if content_type.split(';')[0]=='application/x-www-form-urlencoded':return [list(x) for x in parse_qsl(body,keep_blank_values=True)]
    need(content_type.startswith('multipart/form-data;'),'Native form content type')
    message=BytesParser(policy=default).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n'+body).encode())
    need(message.is_multipart(),'Multipart parsing');result=[]
    for part in message.iter_parts():
        need(part.get_content_disposition()=='form-data' and part.get_filename() is None,'Text form field')
        result.append([part.get_param('name',header='content-disposition'),part.get_payload(decode=True).decode('utf-8')])
    return result

def qualify(o,s,reg):
    if o['status']!='ordinary_control_passed' or not o.get('browser_cleanup_confirmed'):return False
    need(o['instance']['version']==reg['version'],'Version');need(o['actor']=={'id':2,'login':'study-actor','is_admin':False},'Ordinary actor')
    requests=o['requests'];users=[r for r in requests if r['method']=='GET' and r['path']=='/api/v1/user'];need(len(users)==1 and users[0]['status']==200 and users[0]['response']['id']==2 and users[0]['response']['is_admin'] is False,'Raw actor')
    repos=[r for r in requests if r['method']=='POST' and r['path']=='/api/v1/user/repos'];need(len(repos)==1 and repos[0]['status']==201 and repos[0]['body']==reg['repository'] and repos[0]['response']==o['repository'],'Repository creation');repo=o['repository'];need(repo['owner']['id']==2 and repo['full_name']=='study-actor/study-repo','Repository ownership')
    collection='/api/v1/repos/study-actor/study-repo/'+s['collection'];initial=[r for r in requests if r['method']=='GET' and r['path']==collection];need(len(initial)==1 and initial[0]['status']==200 and initial[0]['response']==[],'Empty resource collection')
    need(o['initial_business_state']=={'actor':o['actor'],'repository':{'id':repo['id'],'full_name':repo['full_name'],'owner_id':2},'resources':[]},'Initial state projection')
    creates=[r for r in requests if r['method']=='POST' and r['path']==collection];need(len(creates)==1 and creates[0]['status']==201 and creates[0]['body']==s['payload'],'Producer')
    path=collection+'/'+str(creates[0]['response']['id']);reads=[r for r in requests if r['method']=='GET' and r['path']==path];need(len(reads)==2 and all(r['status']==200 for r in reads),'Read inventory');prefix,final=[r['response'] for r in reads];need(prefix==o['prefix'] and final==o['final'],'Raw readbacks')
    expected={**prefix,'description':s['edit_value']};body={k:expected[k] for k in s['fields']}
    if o['channel']=='api':
        writes=[r for r in requests if r['method']=='PATCH' and r['path']==path];need(len(writes)==1 and writes[0]['status']==200 and writes[0]['body']==body,'Full API body')
    else:
        milestone=s['id']=='milestone';writepath='/study-actor/study-repo/'+('milestones/'+str(prefix['id'])+'/edit' if milestone else 'labels/edit');writes=o['native_requests'];need(len(writes)==1 and writes[0]['method']=='POST' and writes[0]['path']==writepath and writes[0]['status'] in [200,302,303],'Native identity')
        entries=form_entries(writes[0]['body'],writes[0]['content_type']);need(entries==writes[0]['form_entries'],'Independent form decoding');fields={}
        for k,v in entries:need(k not in fields,'Duplicate field in ordinary form');fields[k]=v
        need(fields.get('title')==prefix['title' if milestone else 'name'] and fields.get('content' if milestone else 'description')==s['edit_value'],'Intended native edit')
        if milestone:need(fields.get('deadline')=='2027-01-15' and prefix['due_on']=='2027-01-15T23:59:59Z','Native ordinary date')
        else:need(fields.get('color','').lstrip('#')==prefix['color'].lstrip('#') and fields.get('exclusive') in ['on','true','1'] and fields.get('is_archived','false') in ['false','0',''],'Native preserved label fields')
        forms=o['forms'];need([f['label'] for f in forms]==['loaded','before_submit','fresh_final'],'Native view inventory')
        need(all(f['title']==prefix['title' if milestone else 'name'] and f['title_attributes']['required'] and f['title_attributes']['maxLength']==50 for f in forms),'Native title binding')
        need(forms[0]['description']==prefix['description'] and all(f['description']==s['edit_value'] for f in forms[1:]),'Native description binding')
        if milestone:need(all(f['deadline']=='2027-01-15' for f in forms),'Native date binding')
        else:
            need(all(f['color'].lstrip('#')=='336699' and f['exclusive'] is True and f['is_archived'] is False and f['exclusive_order']==forms[0]['exclusive_order'] for f in forms),'Native label preservation')
            need(all(f['description_attributes']['maxLength']==200 and f['color_attributes']['required'] and f['color_attributes']['maxLength']==7 for f in forms),'Native label constraints')
    need(preserve(final)==preserve(expected),'Full target preservation');need(o['prefix_business']==business(prefix) and o['final_business']==business(final),'Cross-reset projection');return True

def build(root,registry):
    reg=read(registry);units={u['id']:u for u in reg['units']};specs={s['id']:s for s in reg['workflows']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source/proof: '+p)
    for p in sorted(Path(root).rglob('report.json')):
        r=read(p);u=r['unit'];uid=u['id'];need(uid in units and uid not in records and u==units[uid],'Unit inventory');need(r['registry_sha256']==sha(registry),'Registry');runs.add(r['run_identity']);commits.add(r['source_commit'])
        for rel,h in r['files_sha256'].items():need(sha(p.parent/rel)==h,'Raw hash')
        if 'image' in r:need(r['image']['id']==reg['image_id'],'Image')
        obs={};branches={}
        for channel in ['api','ui']:
            f=p.parent/channel/'observation.json'
            if f.exists():obs[channel]=read(f);branches[channel]=qualify(obs[channel],specs[u['workflow']],reg)
            else:branches[channel]=False
        paired=len(obs)==2 and all(obs['api'].get(k)==obs['ui'].get(k) for k in ['initial_business_state','prefix_business','final_business'])
        records[uid]=dict(branches=branches,paired=paired,qualified=all(branches.values()) and paired and r.get('cleanup_confirmed',False),report_sha256=sha(p))
    need(set(records)==set(units),'Incomplete inventory');need(len(runs)==len(commits)==1,'Mixed run/source')
    return dict(kind='gitea_ordinary_qualification_results_v1',registry_sha256=sha(registry),verifier_sha256=sha(__file__),run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,qualified_pairs=sum(r['qualified'] for r in records.values()),boundary_cases_executed=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',type=Path,default=ROOT/'manifests/gitea-controls-v1.json');p.add_argument('--output');a=p.parse_args();v=build(a.root,a.registry)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
