#!/usr/bin/env python3
"""Independent reconstruction from retained HTTP, DOM and scoped Fetch observations."""
import argparse,hashlib,json,re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/vikunja-execution-v1.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):
    x=json.loads(json.dumps(v))
    for k in ['created','updated']:x.pop(k,None)
    if x.get('subscription'):x['subscription'].pop('created',None)
    for key in ['owner','created_by']:
        if x.get(key):
            for k in ['created','updated']:x[key].pop(k,None)
    for view in x.get('views',[]):
        for k in ['created','updated']:view.pop(k,None)
    return x
def stable(v):return {k:x for k,x in v.items() if k!='updated'}
class Inputs(HTMLParser):
    def __init__(self):super().__init__();self.inputs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='input':self.inputs.append(dict(attrs))
def canonical(value):
    if not isinstance(value,str):return None
    v=value[1:] if value.startswith('#') else value
    if re.fullmatch('[a-fA-F0-9]{3}',v):v=''.join(ch*2 for ch in v)
    return '#'+v.lower() if re.fullmatch('[a-fA-F0-9]{6}',v) else None

def rebuild(o,c,reg):
    s=next(w for w in reg['workflows'] if w['id']==c['workflow']);task=s['id']=='task';method='PATCH' if task else 'PUT'
    result=dict(outcome='unresolved',contract=[],consistency=[],representation_signal=False,documented_normalization=False)
    need(o['case_id']==c['id'] and o['workflow']==c['workflow'],'Case identity')
    requests=o.get('requests',[])
    if 'instance' in o:need(o['instance']['version']==reg['version'],'Version')
    if 'actor' in o:
        need(o['actor']=={'id':2,'username':'study-actor','is_admin':False},'Ordinary actor')
        users=[r for r in requests if r['method']=='GET' and r['path']=='/api/v2/user'];need(len(users)==1 and users[0]['status']==200 and users[0]['response']['id']==2 and users[0]['response']['is_admin'] is False,'Actor raw proof')
    if 'producer_body' not in o:return result
    body={**s['payload']};createpath=s['collection'];fixturepath=None
    if task:
        fixtures=[r for r in requests if r['method']=='POST' and r['path']=='/api/v2/projects'];need(len(fixtures)==1 and fixtures[0]['status']==201 and fixtures[0]['body']==reg['project_fixture'] and fixtures[0]['response']==o['fixture_created'],'Fixture producer')
        fixturepath='/api/v2/projects/'+str(o['fixture_created']['id']);createpath=fixturepath+'/tasks';body['project_id']=o['fixture_created']['id']
        fixture_reads=[r for r in requests if r['method']=='GET' and r['path']==fixturepath and r['status']==200];need(fixture_reads and fixture_reads[0]['response']==o['fixture_initial'],'Fixture initial raw')
    if c['cohort']=='boundary':
        if c['mutation']=='omitted':body.pop(c['field'])
        else:body[c['field']]=c['value']
    need(o['producer_body']==body,'Declared producer')
    collections=[r for r in requests if r['method']=='GET' and r['path']==s['collection'] and r['status']==200];need(collections and collections[0]['response']==o['initial_raw'],'Initial raw collection')
    raw=o['initial_raw'];need(o['initial_business_state']=={**raw,'items':[business(v) for v in raw['items']]},'Initial business projection')
    writes=[r for r in requests if r['method']=='POST' and r['path']==createpath]
    if not writes:return result
    need(len(writes)==1 and writes[0]['body']==body and writes[0]['status']==o['producer_status'],'Producer trace');made=writes[0]
    if made['status']!=201:
        if 'after_failed_producer' not in o:return result
        need(len(collections)==2 and collections[-1]['response']==o['after_failed_producer'],'Rejected producer readback')
        unchanged=o['after_failed_producer']==o['initial_raw']
        if task:
            need(fixture_reads[-1]['response']==o['fixture_final'],'Rejected fixture readback');unchanged=unchanged and o['fixture_final']==o['fixture_initial']
        if made['status'] in [400,409,422] and unchanged and o['status']=='observed' and o.get('browser_cleanup_confirmed'):result['outcome']='producer_rejected'
        return result
    prefix=o.get('prefix')
    if prefix is None:return result
    path=s['collection']+'/'+str(made['response']['id']);reads=[r for r in requests if r['method']=='GET' and r['path']==path and r['status']==200]
    need(reads and reads[0]['response']==prefix and prefix[s['owner_field']]['id']==2,'Persisted prefix identity');need(o['prefix_business']==business(prefix),'Prefix projection')
    if task:
        need(prefix['project_id']==o['fixture_created']['id'],'Task project')
        need(len(fixture_reads)>=2 and fixture_reads[1]['response']==o['fixture_prefix'] and o['fixture_business']==business(o['fixture_prefix']),'Fixture prefix projection')
    title=prefix.get('title');limit=1000 if task else 250
    if not isinstance(title,str) or len(title)<1 or len(title)>limit:result['contract'].append('title:length')
    if s['id']=='project':
        identifier=prefix.get('identifier')
        if not isinstance(identifier,str) or len(identifier)>10:result['contract'].append('identifier:length');result['consistency'].append('identifier:native_maxlength')
    color=prefix.get('hex_color')
    if not isinstance(color,str) or (color!='' and canonical(color) is None):result['contract'].append('hex_color:optional_hex')
    if not task and (not isinstance(color,str) or (color!='' and canonical(color) is None)):result['consistency'].append('hex_color:native_color')
    if task and (not isinstance(title,str) or not title.strip()):result['consistency'].append('title:trimmed_nonempty')
    expected={**prefix,('description' if task else 'title'):s['edit_value']};final=o.get('final')
    if final is not None:need(reads[-1]['response']==final and o['final_business']==business(final),'Final raw record')
    status=None
    if o['channel']=='api':
        mutations=[r for r in requests if r['method']==method and r['path']==path]
        if mutations:
            want=[{'op':'add','path':'/'+k,'value':(expected[k] if expected[k] is not None else []) if k=='reminders' else expected[k]} for k in s['fields']] if task else {k:expected[k] for k in s['fields']}
            need(len(mutations)==1 and mutations[0]['body']==want,'Full API semantic body');status=mutations[0]['status'];need(status==o['continuation_status'],'API status')
    else:
        forms=o.get('forms',[]);loaded=next((f for f in forms if f['label']=='loaded'),None)
        if loaded:
            result['representation_signal']=loaded['title']!=(title.strip() if task and isinstance(title,str) else title) or loaded['description_text']!='Ordinary description'
            if not task:
                parser=Inputs();parser.feed(loaded['color_html']);need(len(parser.inputs)==1 and parser.inputs[0]['type']=='color','Bound native color')
                need(loaded['color_empty']==('is-empty' in parser.inputs[0].get('class','').split()),'Color empty flag')
                representable=(color=='' and loaded['color_empty']) or (not loaded['color_empty'] and loaded['color']==canonical(color));result['representation_signal']|=not representable
                if s['id']=='project':need(loaded['identifier_attributes']['maxLength']==10,'Bound native identifier');result['representation_signal']|=loaded['identifier']!=prefix.get('identifier')
        native=o.get('native_requests',[]);fetch=o.get('fetch_requests',[])
        for raw in native:need(raw['method']==method and raw['path']==path,'Native transport identity')
        for raw in fetch:need(raw['method']==method and raw['path']==path,'Fetch identity')
        if len(native)==len(fetch)==1:
            need(native[0]['status']==fetch[0]['status'] and (native[0]['body'] is None or native[0]['body']==fetch[0]['body']),'Independent capture agreement')
            payload=json.loads(fetch[0]['body']);edit='description' if task else 'title'
            if task:
                need(isinstance(payload,list),'Native patch format');edited=[x for x in payload if x.get('path')=='/description'];need(len(edited)==1 and edited[0].get('op')=='add' and edited[0].get('value')==s['edit_value'],'Native intended edit')
            else:need(payload.get(edit)==s['edit_value'],'Native intended edit')
            status=native[0]['status'];need(status==o.get('continuation_status'),'Native status')
            if status==200:need([f['label'] for f in forms]==['loaded','before_submit','fresh_final'],'Successful native views')
        elif native or fetch:return result
        elif o.get('save_control',{}).get('disabled') and o.get('no_request_window_ms')==1500 and final==prefix:status='blocked'
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed') or final is None:return result
    if task:
        need(fixture_reads[-1]['response']==o['fixture_final'],'Fixture final raw')
        if stable(o['fixture_final'])!=stable(o['fixture_prefix']):result['outcome']='preservation_or_edit_discrepancy';return result
    if status==200:
        if stable(final)==stable(expected):result['outcome']='clean'
        elif task and o['channel']=='ui' and isinstance(title,str) and title!=title.strip() and stable(final)==stable({**expected,'title':title.strip()}):result.update(outcome='documented_normalization',documented_normalization=True)
        else:result['outcome']='preservation_or_edit_discrepancy'
    elif status in [400,409,422] and final==prefix:result['outcome']='continuation_rejected'
    elif status=='blocked':result['outcome']='blocked_native_control'
    return result

def build(root):
    reg=read(REGISTRY);units={u['id']:u for u in reg['units']};cases={c['id']:c for c in reg['cases']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source/proof: '+p)
    for p in sorted(Path(root).rglob('report.json')):
        report=read(p);u=report['unit'];uid=u['id'];need(uid in units and uid not in records and u==units[uid],'Unit inventory');need(report['registry_sha256']==sha(REGISTRY),'Registry');runs.add(report['run_identity']);commits.add(report['source_commit'])
        for rel,h in report['files_sha256'].items():need(sha(p.parent/rel)==h,'Raw hash')
        if 'image' in report:need(report['image']['id']==reg['image_id'],'Image')
        observations={};channels={}
        for channel in ['api','ui']:
            f=p.parent/channel/'observation.json'
            if f.exists():observations[channel]=read(f);channels[channel]=rebuild(observations[channel],cases[u['case_id']],reg)
            else:channels[channel]=dict(outcome='unresolved',contract=[],consistency=[],representation_signal=False,documented_normalization=False)
        paired=len(observations)==2 and all(observations['api'].get(k)==observations['ui'].get(k) for k in ['initial_business_state','producer_status','prefix_business','fixture_business']) and report.get('cleanup_confirmed')
        outcomes=[channels[c]['outcome'] for c in ['api','ui']];shared=any(r['contract'] or r['consistency'] for r in channels.values());representation=channels['ui']['representation_signal']
        if not paired or 'unresolved' in outcomes:category='unresolved'
        elif outcomes==['producer_rejected']*2:category='producer_rejected'
        elif outcomes==['clean']*2:category='both_clean'
        elif outcomes==['clean','documented_normalization']:category='documented_native_normalization'
        elif outcomes[0]!=outcomes[1]:category='channel_difference'
        else:category='matching_nonclean'
        eligible=category not in ['producer_rejected','unresolved'];api_signal=shared or outcomes[0]!='clean';native_signal=shared or outcomes[1] not in ['clean','documented_normalization'] or representation
        overlap=('both' if api_signal and native_signal else 'api_only' if api_signal else 'native_only' if native_signal else 'neither') if eligible else 'not_eligible'
        records[uid]=dict(case_id=u['case_id'],cohort=u['cohort'],classification=category,channels=channels,paired=bool(paired),baseline_overlap=overlap,repeat_required=category not in ['both_clean','producer_rejected'] or shared or representation,report_sha256=sha(p))
    need(set(records)==set(units),'Incomplete full inventory');need(len(runs)==len(commits)==1,'Mixed run/source')
    return dict(kind='vikunja_finite_results_v1',run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,counts={cohort:dict(Counter(v['classification'] for v in records.values() if v['cohort']==cohort)) for cohort in ['valid_control','boundary']},repeat_case_ids=sorted({v['case_id'] for v in records.values() if v['cohort']=='boundary' and v['repeat_required']}),natural_defects_confirmed=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['counts'],indent=2))
