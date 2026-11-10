#!/usr/bin/env python3
"""Reconstruct memo controls from raw REST, binary request and full readback records."""
import argparse,base64,json
from pathlib import Path
from verify_memos_preference_controls_v1 import ROOT,read,sha,require,wire,only
REGISTRY=ROOT/'manifests/memos-memo-probe-v1.json'
NAME='memos/study-control';PATH='/api/'+NAME
SEED={'content':'Ordinary memo','visibility':'PRIVATE','createTime':'2026-01-01T00:00:00Z','updateTime':'2026-01-01T00:00:00Z'}
FIELDS=['content','visibility','space','pinned','state','createTime','updateTime','location','attachments','relations']
MASK='content,visibility,space,pinned,state,create_time,update_time,location,attachments,relations'
def build(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};found={};runs=set();commits=set()
    for path in sorted(Path(root).rglob('report.json')):
        report=read(path);uid=report['unit']['id'];require(uid in units and uid not in found,'Unexpected unit');require(report['unit']==units[uid],'Unit differs');require(report['registry_sha256']==sha(REGISTRY),'Registry differs');runs.add(report['run_identity']);commits.add(report['source_commit'])
        for rel,h in report['files_sha256'].items():require(sha(path.parent/rel)==h,'Raw artifact changed')
        record={'status':report['status'],'report_sha256':sha(path),'qualified':False}
        if report['status']=='ordinary_pair_passed':
            require(report['cleanup_confirmed'],'Container cleanup');require(report['image']['id']==reg['image_id'],'Image mismatch')
            branches={c:read(path.parent/c/'observation.json') for c in ['api','ui']}
            for c,o in branches.items():
                require(o['status']=='ordinary_control_passed' and o['browser_cleanup_confirmed'],'Branch failed');require(o['actor']=={'name':'users/study-actor','role':'USER'},'Actor differs');require(o['instance']['version']==reg['version'] and o['instance']['commit']==reg['source_commit'],'Version/source differs')
                require(o['prefix']['name']==NAME and o['prefix']['creator']=='users/study-actor','Resource owner');require(all(o['prefix'][k]==v for k,v in SEED.items()),'Seed differs');require(o['prefix']['state']=='NORMAL','Not ordinary');require(o['final']=={**o['prefix'],'visibility':'PROTECTED'},'Complete preservation differs')
                posts=[r for r in o['requests'] if r['method']=='POST'];require(len(posts)==1 and posts[0]['path']=='/api/memos?memoId=study-control' and posts[0]['body']==SEED and posts[0]['status']==200,'Producer differs')
                gets=[r for r in o['requests'] if r['method']=='GET' and r['path']==PATH];require(len(gets)==(2 if c=='api' else 3) and all(r['status']==200 for r in gets),'Read inventory');require(gets[0]['response']==o['prefix'] and gets[-1]['response']==o['final'],'Readback mismatch')
                patches=[r for r in o['requests'] if r['method']=='PATCH'];require(len(patches)==(1 if c=='api' else 0),'API mutation inventory')
                if patches:
                    p=patches[0];require(p['status']==200 and p['path']==PATH+'?updateMask='+MASK,'Full mutation mask');require(p['body']=={'name':NAME,**{k:o['final'].get(k) for k in FIELDS}},'Full mutation body')
            for key in ['initial_business_state','prefix','final']:require(branches['api'][key]==branches['ui'][key],'Matched reset differs: '+key)
            probe=branches['ui']['synthetic_probe'];require(probe['kind']=='deliberate_empty_editor' and probe['content']=='' and probe['disabled'] is True and probe['target_requests']==0,'Negative control not observed');require(probe['persisted']==branches['ui']['prefix'],'Probe changed stored record')
            ui=branches['ui'];native=ui['native_request'];require(native['status']==200 and native['path']=='/memos.api.MemoService/UpdateMemo' and native['content_type'].split(';')[0]=='application/proto','Native transport')
            request=wire(base64.b64decode(native['request_base64'],validate=True));require(set(request)=={1,2},'Request fields');memo=wire(only(request,1));require(memo=={1:[NAME.encode()],4:[b'Ordinary memo'],6:[2]},'Native memo body');require(wire(only(request,2))=={1:[b'visibility']},'Native mask')
            forms=ui['forms'];require([f['label'] for f in forms]==['loaded','before_submit','fresh_final'],'View inventory');require([f['audience'] for f in forms]==['Private','Protected','Protected'],'Audience sequence');require(all(f['editor_count']==f['audience_count']==f['update_count']==1 and f['content']=='Ordinary memo' and not f['disabled'] for f in forms),'Native bindings')
            record['qualified']=True
        found[uid]=record
    require(set(found)==set(units),'Missing units');require(len(runs)==len(commits)==1,'Mixed runs')
    return {'kind':'memos_memo_synthetic_probe_attempt_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':found,'qualified_pairs':sum(r['qualified'] for r in found.values()),'boundary_results':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v,indent=2))
