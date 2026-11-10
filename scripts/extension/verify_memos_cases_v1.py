#!/usr/bin/env python3
"""Independent finite-cohort reconstruction from retained HTTP, DOM and binary data."""
import argparse,base64,hashlib,json
from collections import Counter
from pathlib import Path
from verify_memos_preference_controls_v1 import wire,only
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/memos-execution-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def rebuild(o,c,reg):
    memo=c['workflow']=='memo';name='memos/study-control' if memo else 'users/study-actor/settings/GENERAL';path='/api/'+name
    result={'outcome':'unresolved','contract':[],'consistency':[],'representation_signal':False,'measurement_error':o.get('status')!='observed'}
    requests=o.get('requests',[]);need(o['case_id']==c['id'] and o['workflow']==c['workflow'],'Case identity')
    if 'instance' in o:need(o['instance']['version']==reg['version'] and o['instance']['commit']==reg['application_commit'],'Version')
    if 'actor' in o:need(o['actor']=={'name':'users/study-actor','role':'USER'},'Actor')
    if 'producer_body' not in o:return result
    seed={'content':'Ordinary memo','visibility':'PRIVATE','createTime':'2026-01-01T00:00:00Z','updateTime':'2026-01-01T00:00:00Z'} if memo else {'locale':'en','memoVisibility':'PROTECTED','theme':'paper','saveMediaMetadata':False}
    mask='content,visibility,space,pinned,state,create_time,update_time,location,attachments,relations' if memo else 'locale,memo_visibility,theme,save_media_metadata'
    producer={**seed}
    if c['cohort']=='boundary':
        if c['mutation']=='omitted':producer.pop(c['field'])
        else:producer[c['field']]=c['value']
    body=producer if memo else {'name':name,'generalSetting':producer};need(body==o['producer_body'],'Producer body')
    writes=[r for r in requests if r['method']==('POST' if memo else 'PATCH') and r['path']==('/api/memos?memoId=study-control' if memo else path+'?updateMask='+mask)]
    if not memo:
        need(writes and writes[0]['body']=={'name':name,'generalSetting':seed} and writes[0]['status']==200,'Initialization');need(o.get('initialized')==seed,'Initialized state');writes=writes[1:]
    if not writes:return result
    made=writes[0];need(made['body']==body and made['status']==o['producer_status'],'Producer trace')
    if made['status']!=200:
        checkpath='/api/memos' if memo else path
        reads=[r for r in requests if r['method']=='GET' and r['path']==checkpath]
        need(reads and reads[-1]['status']==200 and reads[-1]['response']==o['after_failed_producer'],'Failed producer readback')
        original=o['initial_business_state']['resource'] if memo else {'name':name,'generalSetting':seed}
        rejected=made['status'] in [400,409,422] and reads[-1]['response']==original
        if rejected:result['outcome']='producer_rejected'
        return result
    prefix=o.get('prefix')
    if prefix is None:return result
    reads=[r for r in requests if r['method']=='GET' and r['path']==path and r['status']==200];projection=lambda v:v if memo else v['generalSetting']
    # The preference initial/default and initialized reads precede the producer read.
    prefix_index=0 if memo else 2
    need(len(reads)>prefix_index and projection(reads[prefix_index]['response'])==prefix,'Prefix readback')
    need(reads[prefix_index]['response']['name']==name,'Persisted identity')
    domains=read(ROOT/'manifests/memos-preference-domains-v1.json')
    if memo:
        need(prefix['creator']=='users/study-actor','Memo owner')
        if not isinstance(prefix.get('content'),str):result['contract'].append('content:string')
        elif not prefix['content'].strip():result['consistency'].append('content:trimmed_nonempty_without_attachments')
    else:
        for field in ['locale','theme','memoVisibility']:
            if not isinstance(prefix.get(field),str):result['contract'].append(field+':string')
            if prefix.get(field) not in domains[field]:result['consistency'].append(field+':native_option')
        if prefix.get('memoVisibility') not in domains['memoVisibility']:result['contract'].append('memoVisibility:server_enum')
        if type(prefix.get('saveMediaMetadata')) is not bool:result['contract'].append('saveMediaMetadata:boolean')
    final=o.get('final');expected={**prefix,('visibility' if memo else 'saveMediaMetadata'):('PROTECTED' if memo else True)}
    if final is not None:need(projection(reads[-1]['response'])==final,'Final readback')
    if o['channel']=='api':
        mutations=[r for r in requests if r['method']=='PATCH' and r['path']==path+'?updateMask='+mask]
        if not memo:mutations=mutations[2:]
        if not mutations:return result
        need(len(mutations)==1,'Continuation inventory');edit=mutations[0]
        fields=['content','visibility','space','pinned','state','createTime','updateTime','location','attachments','relations']
        want={'name':name,**{k:expected.get(k) for k in fields}} if memo else {'name':name,'generalSetting':expected}
        need(edit['body']==want,'Full API mutation')
        if edit['status']==200 and final is not None:result['outcome']='clean' if final==expected else 'preservation_or_edit_discrepancy'
        elif edit['status'] in [400,409,422] and final==prefix:result['outcome']='continuation_rejected'
    else:
        forms=o.get('forms',[]);loaded=next((f for f in forms if f['label']=='loaded'),None)
        if loaded:
            if memo:result['representation_signal']=loaded['text_content']!=prefix.get('content')
            else:
                rows={r['field']:r for r in loaded['preference_fields']['fields']};need(set(rows)=={'locale','theme','memoVisibility'},'Native fields')
                for field,row in rows.items():
                    need(row['count']==1,'Native field count');selected=[x['text'] for x in row['options'] if x['selected']=='true'];value=prefix.get(field)
                    if field=='locale':
                        # Exact native-code suffix; no selected option is expected for unsupported values.
                        matched=(len(selected)==1 and selected[0].endswith(value)) if value in domains[field] else not selected
                    else:
                        displayed=value or ('system' if field=='theme' else 'PRIVATE');label=domains[field].get(displayed);matched=selected==([label] if label else [])
                    result['representation_signal']|=not matched
        natives=o.get('native_requests',[])
        for raw in natives:
            need(raw['method']=='POST' and raw['path']==('/memos.api.MemoService/UpdateMemo' if memo else '/memos.api.UserService/UpdateUserSetting'),'Native request identity')
            try:
                need(raw['content_type'].split(';')[0]=='application/proto','Binary content type');w=wire(base64.b64decode(raw['request_base64'],validate=True));need(set(w)=={1,2},'Native fields');resource=wire(only(w,1));need(only(resource,1).decode()==name,'Native resource');maskwire=wire(only(w,2))
                if memo:
                    need(set(resource)<={1,4,6} and only(resource,6,0)==2 and maskwire=={1:[b'visibility']},'Native memo mutation');need(only(resource,4,b'').decode()==prefix['content'],'Native content changed in patch')
                else:
                    need(set(resource)=={1,2} and maskwire=={1:[b'save_media_metadata']},'Native preference mask');general=wire(only(resource,2));need(set(general)<={1,2,3,4} and only(general,4,0)==1,'Native preference body')
            except (ValueError,UnicodeError,TypeError):result['measurement_error']=True
        before=next((f for f in forms if f['label']=='before_submit'),None)
        if before and before['disabled'] and not natives and final==prefix:result['outcome']='blocked_native_control'
        elif len(natives)==1 and not result['measurement_error'] and final is not None:
            if natives[0]['status']==200:result['outcome']='clean' if final==expected else 'preservation_or_edit_discrepancy'
            elif natives[0]['status'] in [400,409,422] and final==prefix:result['outcome']='continuation_rejected'
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed'):result['outcome']='unresolved'
    return result

def build(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};cases={c['id']:c for c in reg['cases']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source/proof differs: '+p)
    for p in sorted(Path(root).rglob('report.json')):
        report=read(p);u=report['unit'];uid=u['id'];need(uid in units and uid not in records and u==units[uid],'Unit inventory');need(report['registry_sha256']==sha(REGISTRY),'Registry');runs.add(report['run_identity']);commits.add(report['source_commit'])
        for rel,h in report['files_sha256'].items():need(sha(p.parent/rel)==h,'Raw hash')
        if 'image' in report:need(report['image']['id']==reg['image_id'],'Image')
        obs={};channels={}
        for channel in ['api','ui']:
            f=p.parent/channel/'observation.json'
            if f.exists():obs[channel]=read(f);channels[channel]=rebuild(obs[channel],cases[u['case_id']],reg)
            else:channels[channel]={'outcome':'unresolved','contract':[],'consistency':[],'representation_signal':False,'measurement_error':True}
        paired=len(obs)==2 and all(obs['api'].get(k)==obs['ui'].get(k) for k in ['initial_business_state','prefix_status','prefix']) and report.get('cleanup_confirmed')
        outcomes=[channels[c]['outcome'] for c in ['api','ui']];shared=any(v['contract'] or v['consistency'] for v in channels.values());representation=channels['ui']['representation_signal']
        if not paired or 'unresolved' in outcomes:category='unresolved'
        elif outcomes==['producer_rejected']*2:category='producer_rejected'
        elif outcomes==['clean']*2:category='both_clean'
        elif outcomes[0]!=outcomes[1]:category='channel_difference'
        else:category='matching_nonclean'
        eligible=category not in ['producer_rejected','unresolved'];api_signal=shared or outcomes[0]!='clean';native_signal=shared or outcomes[1]!='clean' or representation
        overlap=('both' if api_signal and native_signal else 'api_only' if api_signal else 'native_only' if native_signal else 'neither') if eligible else 'not_eligible'
        repeat=category in ['unresolved','channel_difference','matching_nonclean'] or shared or representation
        records[uid]={'case_id':u['case_id'],'cohort':u['cohort'],'classification':category,'channels':channels,'paired':bool(paired),'baseline_overlap':overlap,'repeat_required':repeat,'report_sha256':sha(p)}
    need(set(records)==set(units),'Incomplete full inventory');need(len(runs)==len(commits)==1,'Mixed runs')
    return {'kind':'memos_finite_results_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':records,'counts':{cohort:dict(Counter(v['classification'] for v in records.values() if v['cohort']==cohort)) for cohort in ['valid_control','boundary']},'repeat_case_ids':sorted({v['case_id'] for v in records.values() if v['cohort']=='boundary' and v['repeat_required']}),'natural_defects_confirmed':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['counts'],indent=2))
