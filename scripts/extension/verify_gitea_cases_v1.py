#!/usr/bin/env python3
"""Offline raw reconstruction; does not import the runtime outcome classifier."""
import argparse,hashlib,json,re
from pathlib import Path
from verify_gitea_controls_v2 import form_entries
from verify_gitea_issue_controls_v1 import qualify as qualify_issue
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def preserve(v):return {k:x for k,x in v.items() if k!='updated_at'}
def business(v):return {k:x for k,x in v.items() if k not in ['updated_at','created_at']}
def reconstruct(o,s,c,reg):
    result=dict(outcome='unresolved',consistency=[],representation_signal=False)
    if s['id']=='issue':
        if qualify_issue(o,s,reg):result['outcome']='clean'
        return result
    need(o['candidate']==c and o['workflow']==s['id'],'Candidate identity')
    requests=o['requests'];collection='/api/v1/repos/study-actor/study-repo/'+s['collection']
    def matching(method,path):return [r for r in requests if r['method']==method and r['path']==path]
    version=matching('GET','/api/v1/version');need(len(version)==1 and version[0]['status']==200 and version[0]['response']==o['instance'] and o['instance']['version']==reg['version'],'Raw version')
    users=matching('GET','/api/v1/user');need(len(users)==1 and users[0]['status']==200 and users[0]['response']['id']==2 and users[0]['response']['is_admin'] is False and users[0]['response']['login']=='study-actor','Raw ordinary actor')
    need(o['actor']==dict(id=2,login='study-actor',is_admin=False),'Actor projection')
    repos=matching('POST','/api/v1/user/repos');need(len(repos)==1 and repos[0]['status']==201 and repos[0]['body']==reg['repository'] and repos[0]['response']==o['repository'],'Repository fixture');repo=o['repository'];need(repo['owner']['id']==2 and repo['full_name']=='study-actor/study-repo','Repository ownership')
    initial=matching('GET',collection);need(initial and initial[0]['status']==200 and initial[0]['response']==[],'Initial empty collection')
    need(o['initial_business_state']==dict(actor=o['actor'],repository=dict(id=repo['id'],full_name=repo['full_name'],owner_id=2),resources=[]),'Initial state')
    payload=dict(s['payload'])
    if c['cohort']=='boundary':
        if c['mutation']=='omitted':payload.pop(c['field'],None)
        else:payload[c['field']]=c['value']
    creates=matching('POST',collection);need(len(creates)==1 and creates[0]['body']==payload and creates[0]['status']==o['producer_status'],'Producer wire')
    if creates[0]['status']!=201:
        if o.get('status')=='observed' and o.get('browser_cleanup_confirmed') and creates[0]['status'] in [400,409,422]:
            need(len(initial)==2 and initial[1]['status']==200 and initial[1]['response']==o['after_failed_producer']==[],'Rejected producer unchanged');result['outcome']='producer_rejected'
        return result
    target=collection+'/'+str(creates[0]['response']['id']);reads=matching('GET',target);need(reads and reads[0]['status']==200 and reads[0]['response']==o['prefix'],'Raw prefix');p=o['prefix'];need(o['prefix_business']==business(p),'Prefix projection');f=o.get('final')
    title=p['title' if s['id']=='milestone' else 'name'];milestone=s['id']=='milestone'
    if not isinstance(title,str) or not 1<=len(title)<=50:result['consistency'].append('title:required_max50')
    if not milestone:
        color=p['color']
        if not isinstance(color,str) or not re.fullmatch(r'#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})',color):result['consistency'].append('color:native_hex')
        if p['exclusive'] and (not isinstance(title,str) or re.search(r'.*[^/]/[^/].*',title) is None):result['consistency'].append('exclusive:scoped_name')
    writes=matching('PATCH',target)
    if o['channel']=='api':
        if writes:
            body={k:({**p,'description':s['edit_value']})[k] for k in s['fields']};need(len(writes)==1 and writes[0]['body']==body and writes[0]['status']==o['continuation_status'],'Full API continuation')
    else:
        need(not writes,'No API continuation in native branch');forms=o['forms']
        if forms:
            loaded=forms[0];need(loaded['label']=='loaded','Loaded view first');result['representation_signal']=loaded['title']!=title or loaded['description']!=p['description']
            if milestone:result['representation_signal']|=loaded['deadline']!='2027-01-15'
            else:result['representation_signal']|=loaded['color'].lstrip('#').lower()!=p['color'].lstrip('#').lower() or loaded['exclusive']!=p['exclusive'] or loaded['is_archived']!=p['is_archived']
        native=o['native_requests'];attempts=o['native_attempts'];writepath='/study-actor/study-repo/'+('milestones/'+str(p['id'])+'/edit' if milestone else 'labels/edit')
        if len(native)>1 or len(attempts)>1:return result
        if o.get('status')=='observed':
            need(len(forms)>=2 and forms[1]['label']=='before_submit','Loaded/before-submit evidence');before=forms[1];need(before['description']==s['edit_value'],'Meaningful native edit')
            need(before['title']==loaded['title'],'Native did not repair title')
            if milestone:need(before['deadline']==loaded['deadline'],'Native did not repair date')
            else:need(all(before[k]==loaded[k] for k in ['color','exclusive','exclusive_order','is_archived']),'Native did not repair other fields')
            if native:
                n=native[0];need(n['method']=='POST' and n['path']==writepath and n['status']==o['continuation_status'] and attempts==[dict(method='POST',path=writepath)],'Native target/method/status')
                entries=form_entries(n['body'],n['content_type']);need(entries==n['form_entries'] and len(entries)==len(dict(entries)),'Native decoding');fields=dict(entries)
                need(fields.get('title')==before['title'] and fields.get('content' if milestone else 'description')==s['edit_value'],'Native business body')
                if milestone:need(fields.get('deadline')==before['deadline'],'Native date body')
                else:
                    need(fields.get('color')==before['color'],'Native color body');need((fields.get('exclusive') in ['on','1','true'])==before['exclusive'] and (fields.get('is_archived') in ['on','1','true'])==before['is_archived'],'Native checkbox body')
                if n['status'] in [200,302,303]:need(len(forms)==3 and forms[2]['label']=='fresh_final','Fresh persisted editor')
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed') or not isinstance(f,dict):return result
    need(len(reads)==2 and reads[-1]['status']==200 and reads[-1]['response']==f and o['final_business']==business(f),'Raw final readback')
    status=o.get('continuation_status')
    if status in [200,302,303]:result['outcome']='clean' if preserve(f)==preserve({**p,'description':s['edit_value']}) else 'preservation_or_edit_discrepancy'
    elif status in [400,409,422] and f==p:result['outcome']='continuation_rejected'
    elif o['channel']=='ui' and o.get('save_control',{}).get('form_valid') is False and not o['native_attempts'] and not o['native_requests'] and o.get('no_request_window_ms')==1500 and f==p:result['outcome']='blocked_native_control'
    return result

def build(root,registry):
    reg=read(registry);units={u['id']:u for u in reg['units']};specs={s['id']:s for s in reg['workflows']};cases={c['id']:c for c in reg['cases']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source/proof: '+p)
    for path in sorted(Path(root).rglob('report.json')):
        report=read(path);u=report['unit'];uid=u['id'];need(uid in units and uid not in records and u==units[uid],'Unit inventory');need(report['registry_sha256']==sha(registry),'Registry identity');runs.add(report['run_identity']);commits.add(report['source_commit'])
        for rel,h in report['files_sha256'].items():need(sha(path.parent/rel)==h,'Raw archive hash')
        need(report.get('image',{}).get('id')==reg['image_id'],'Image identity');obs={};outcomes={}
        for channel in ['api','ui']:
            p=path.parent/channel/'observation.json'
            if p.exists():obs[channel]=read(p);outcomes[channel]=reconstruct(obs[channel],specs[u['workflow']],cases[u['case_id']],reg)
            else:outcomes[channel]=dict(outcome='unresolved',consistency=[],representation_signal=False)
        paired=len(obs)==2 and all(k in obs['api'] and k in obs['ui'] and obs['api'][k]==obs['ui'][k] for k in ['initial_business_state'])
        if paired and any('prefix_business' in o for o in obs.values()):paired=all('prefix_business' in o for o in obs.values()) and obs['api']['prefix_business']==obs['ui']['prefix_business']
        if 'outcomes' in report:need(report['outcomes']==outcomes,'Independent/runtime outcome agreement')
        records[uid]=dict(unit=u,outcomes=outcomes,paired=paired,cleanup=report.get('cleanup_confirmed',False),report_sha256=sha(path))
    # A failed linked valid control may stop a batch before its boundary jobs.
    missing=set(units)-set(records)
    for uid in missing:records[uid]=dict(unit=units[uid],outcomes={c:dict(outcome='unresolved',consistency=[],representation_signal=False) for c in ['api','ui']},paired=False,cleanup=False,not_executed=True)
    need(len(runs)==len(commits)==1,'Single run/source');counts={};followups=[]
    for uid,row in records.items():
        unit=row['unit'];control=records[unit['linked_valid_control']]
        gate=control['paired'] and control['cleanup'] and all(x['outcome']=='clean' and not x['consistency'] and not x['representation_signal'] for x in control['outcomes'].values())
        row['linked_valid_qualified']=gate;row['qualified']=gate and row['paired'] and row['cleanup'];a,b=[row['outcomes'][c] for c in ['api','ui']];shared=bool(a['consistency'] or b['consistency']);row['shared_consistency_signal']=shared
        if not row['qualified'] or 'unresolved' in [a['outcome'],b['outcome']]:category='unresolved'
        elif a['outcome']==b['outcome']=='producer_rejected':category='producer_rejected'
        elif a['outcome']==b['outcome']=='clean':category='both_clean'
        else:category='channel_or_preservation_difference'
        row['category']=category;row['api_signal']=shared or a['outcome'] not in ['clean','producer_rejected'];row['native_signal']=shared or b['representation_signal'] or b['outcome'] not in ['clean','producer_rejected'];row['native_only_signal']=row['qualified'] and row['native_signal'] and not row['api_signal'] and category!='unresolved'
        counts[category]=counts.get(category,0)+1
        if unit['cohort']=='boundary' and (category in ['unresolved','channel_or_preservation_difference'] or shared):followups.append(uid)
    return dict(kind='gitea_finite_results_v1',registry_sha256=sha(registry),verifier_sha256=sha(__file__),run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,counts=counts,missing_units=sorted(missing),followup_candidates=sorted(followups),native_only_signals=sum(x['native_only_signal'] for x in records.values()))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',type=Path,default=ROOT/'manifests/gitea-execution-v1.json');p.add_argument('--output',type=Path);a=p.parse_args();v=build(a.root,a.registry)
    if a.output:need(not a.output.exists(),'Output exists');a.output.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['run_identity','counts','missing_units','followup_candidates','native_only_signals']},indent=2))
