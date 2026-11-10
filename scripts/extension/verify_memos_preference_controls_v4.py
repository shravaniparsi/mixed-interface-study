#!/usr/bin/env python3
"""Reconstruct ordinary preference pairs; preserve incomplete attempts as failures."""
import argparse,base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,msg):
    if not v:raise ValueError(msg)
def wire(raw):
    i=0;out={}
    def varint():
        nonlocal i
        n=0
        for shift in range(0,70,7):
            require(i<len(raw),'Truncated integer');b=raw[i];i+=1;n|=(b&127)<<shift
            if b<128:return n
        raise ValueError('Oversized integer')
    while i<len(raw):
        tag=varint();field=tag>>3;kind=tag&7;require(field>0,'Zero field')
        if kind==0:value=varint()
        elif kind==2:
            size=varint();require(i+size<=len(raw),'Truncated bytes');value=raw[i:i+size];i+=size
        else:raise ValueError('Unexpected wire kind')
        out.setdefault(field,[]).append(value)
    return out
def only(fields,n,default=None):
    values=fields.get(n,[]);require(len(values)<=1,'Duplicate singular');return values[0] if values else default
def build(root):
    registry=ROOT/'manifests/memos-preference-controls-v4.json';reg=read(registry);expected={u['id']:u for u in reg['units']};found={};runs=set();commits=set()
    for path in sorted(Path(root).rglob('report.json')):
        report=read(path);uid=report['unit']['id'];require(uid in expected and uid not in found,'Unit inventory');require(report['unit']==expected[uid],'Unit changed');require(report['registry_sha256']==sha(registry),'Registry differs');runs.add(report['run_identity']);commits.add(report['source_commit'])
        for rel,h in report['files_sha256'].items():require(sha(path.parent/rel)==h,'Raw artifact differs')
        record={'status':report['status'],'report_sha256':sha(path),'qualified':False}
        if report['status']=='ordinary_pair_passed':
            require(report['cleanup_confirmed'],'Container cleanup');observations={c:read(path.parent/c/'observation.json') for c in ['api','ui']}
            for c,o in observations.items():
                require(o['status']=='ordinary_control_passed' and o['browser_cleanup_confirmed'],'Branch incomplete');require(o['actor']=={'name':'users/study-actor','role':'USER'},'Actor mismatch')
                require(o['prefix']=={'locale':'en','memoVisibility':'PROTECTED','theme':'paper','saveMediaMetadata':False},'Prefix mismatch');require(o['final']=={**o['prefix'],'saveMediaMetadata':True},'Preservation mismatch')
                require(o['instance']['version']==reg['version'],'Version mismatch')
                patches=[r for r in o['requests'] if r['method']=='PATCH'];require(len(patches)==(2 if c=='api' else 1),'API write inventory')
                for index,patch in enumerate(patches):
                    require(patch['status']==200 and patch['path']=='/api/users/study-actor/settings/GENERAL?updateMask=locale,memo_visibility,theme,save_media_metadata','Complete API mask')
                    require(patch['body']=={'name':'users/study-actor/settings/GENERAL','generalSetting':o['prefix'] if index==0 else o['final']},'API body differs')
                gets=[r for r in o['requests'] if r['method']=='GET' and r['path']=='/api/users/study-actor/settings/GENERAL'];require(len(gets)==3,'Read inventory');require(gets[-2]['response']['generalSetting']==o['prefix'] and gets[-1]['response']['generalSetting']==o['final'],'Readback differs')
            require(observations['api']['initial_business_state']==observations['ui']['initial_business_state'],'Initial reset differs')
            native=observations['ui']['native_request'];require(native['status']==200 and native['content_type'].split(';')[0]=='application/proto','Native transport')
            request=wire(base64.b64decode(native['request_base64'],validate=True));require(set(request)=={1,2},'Request keys');setting=wire(only(request,1));require(set(setting)=={1,2},'Setting keys');require(only(setting,1).decode()=='users/study-actor/settings/GENERAL','Resource mismatch');general=wire(only(setting,2));require(set(general)<={1,2,3,4} and only(general,4,0)==1,'Native boolean');mask=wire(only(request,2));require(mask=={1:[b'save_media_metadata']},'Native mask')
            forms=observations['ui']['forms'];require([f['label'] for f in forms]==['loaded','fresh_final'],'Native view inventory');require([f['checked'] for f in forms]==['false','true'],'Native switch values');require(all(f['switch_count']==1 and not f['disabled'] for f in forms),'Native binding')
            for form in forms:
                fields=form['preference_fields']['fields'];require([f['field'] for f in fields]==['locale','theme','memoVisibility'],'Field bindings')
                require(all(f['count']==1 for f in fields),'Field count')
                selected=lambda f:[x['text'] for x in f['options'] if x['selected']=='true']
                require(len(selected(fields[0]))==1 and selected(fields[0])[0].endswith('en'),'Locale option')
                require(selected(fields[1])==['Paper'] and selected(fields[2])==['Protected'],'Selected preferences')
                require(sorted(x['text'] for x in fields[1]['options'])==sorted(['Sync with system','Light','Dark','Paper']),'Theme inventory')
                require(sorted(x['text'] for x in fields[2]['options'])==sorted(['Private','Protected','Public']),'Visibility inventory')
            record['qualified']=True
        found[uid]=record
    require(set(found)==set(expected),'Missing reports');require(len(runs)==len(commits)==1,'Mixed runs')
    return {'kind':'memos_preference_qualification_attempt_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':found,'qualified_pairs':sum(r['qualified'] for r in found.values()),'boundary_results':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
