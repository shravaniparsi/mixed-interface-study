"""Explicit synthetic acceptance/rejection alternatives for registered mutations."""
from copy import deepcopy
from generated_positive_fixture_v1 import complete
from realworld_generated_bindings_v1 import case_for
from test_realworld_oracle_components import reducer


def accepted(job,channel):
    raw,run,_=complete('api',channel);spec=case_for(job,channel);inputs=spec['operations'][0]['input']['article']
    raw['case_id']=run['case_id']=spec['case_id'];raw['expectation']=deepcopy(spec['expectation'])
    before_body=inputs.get('body') if isinstance(inputs.get('body'),str) else ''
    # Explicit hypothetical normalization for unexpected null/omitted acceptance.
    tags=inputs.get('tagList',[]);body=spec['operations'][1]['input']['article']['body']
    def transform(value):
        if isinstance(value,dict):
            result={k:transform(v) for k,v in value.items()}
            if all(k in value for k in ('title','description','body')):
                result.update(title=inputs['title'],description=inputs['description'],body=body if value['body']==body else before_body)
                if 'tagList' in value:result['tagList']=deepcopy(tags)
            return result
        if isinstance(value,list):return [transform(v) for v in value]
        return value
    raw=transform(raw)
    for e in raw['trace']:
        if e.get('type')=='request' and e.get('method')=='POST' and e.get('path')=='/api/articles':e['payload']=deepcopy(spec['operations'][0]['input'])
    for g in raw['integrity']['guards']:
        if g['name']=='submitted_command' and g['stage']=='prefix':
            g['expected']['payload']=deepcopy(spec['operations'][0]['input']);g['observed']=deepcopy(g['expected'])
    fields_match=inputs.get('body')==before_body
    for check in raw['checks']:
        if check['name'] in ('producer_fields','consumer_loaded_state'):check['passed']=fields_match
    raw['coverage']['state_consumed']=fields_match
    raw['application_outcome']='passed' if all(c['passed'] for c in raw['checks']) else 'state_mismatch'
    return raw,run


def rejected(job,channel,status=422,readable=True):
    raw,run=accepted(job,channel)
    prefix=next(e['sequence'] for e in raw['trace'] if e.get('type')=='response' and e.get('method')=='POST' and e.get('path')=='/api/articles')
    trace=[deepcopy(e) for e in raw['trace'] if e['sequence']<=prefix and e.get('source')!='ui' and e['type'] not in ('ui_request','ui_response','declared_ui_request')]
    response=trace[-1];response['status']=status;response['data']={'errors':{'body':['synthetic rejection']}}
    for i,e in enumerate(trace,1):e['sequence']=i
    def call(path,data,source='api',code=200):
        trace.append({'sequence':len(trace)+1,'type':'request','source':source,'phase':'oracle','method':'GET','path':path})
        trace.append({'sequence':len(trace)+1,'type':'response','source':source,'phase':'oracle','method':'GET','path':path,'status':code,'data':deepcopy(data)})
        return trace[-1]
    follow={'articles':[],'articlesCount':0} if readable else {'errors':{'synthetic':['unreadable']}}
    code=200 if readable else 500
    call('/api/articles?author=pilotresearch',follow,code=code)
    raw['failed_prefix_followup']={'status':code,'data':follow}
    reads=[]
    for old in raw['integrity']['before']['reads']:
        e=call(old['path'],old['data'] if readable else follow,'state_probe',code)
        reads.append({k:deepcopy(e[k]) for k in ('path','status','data')}|{'response_sequence':e['sequence']})
    raw['integrity']['rejection']={'status':'unchanged' if readable else 'unreadable','after':{'readable':readable,'reads':reads,'data':reducer.project_integrity_snapshot(reads) if readable else None}}
    raw['integrity']['guards']=[g for g in raw['integrity']['guards'] if g['stage'] in ('setup','prefix')]
    raw.update(trace=trace,checks=[],prefix_status=status,application_outcome='prefix_server_error' if status>=500 else 'prefix_rejected',coverage={'data_consumed':False,'state_consumed':False,'reached_operations':['create_article']},capture_integrity={'version':1,'helper_sha256':reducer.CAPTURE_HELPER,'complete':True,'contexts':[]})
    for k in ('accepted_producer','resource_reference','resolved_consumer_input','consumer_status','final_state'):raw.pop(k,None)
    return raw,run
