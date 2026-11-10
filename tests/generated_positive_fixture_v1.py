"""Complete synthetic generated traces. Never presented as application evidence."""
from copy import deepcopy
from test_realworld_oracle_components import positive, reducer
from realworld_generated_bindings_v1 import selection


def complete(producer='api', consumer='api'):
    raw,run,_,_=positive(consumer=consumer,generated=True)
    spec=deepcopy(next(c for c in selection()['cases'] if c['intervention']=='route_only' and
                       [o['interface'] for o in c['operations']]==[producer,consumer]))
    raw['case_id']=run['case_id']=spec['case_id'];raw['route']=run['route']=[producer,consumer]
    raw['prefix_interface']=producer
    trace=raw['trace'];created=next(e for e in trace if e['type']=='response' and e['method']=='POST' and e['path']=='/api/articles')['data']['article']
    create_request=next(e for e in trace if e['type']=='request' and e['method']=='POST' and e['path']=='/api/articles')
    create_sequence=create_request['sequence']
    edit_sequence=next(e['sequence'] for e in trace if e.get('method')=='PUT')
    for e in trace:
        seq=e['sequence'];e['phase']='producer' if create_sequence<=seq<create_sequence+2 else 'consumer' if create_sequence+2<=seq<=edit_sequence+1 else 'setup' if seq<create_sequence else 'oracle'
        if producer=='ui' and e.get('path')=='/api/articles' and e.get('method')=='POST':
            e['source']='ui';e['type']='declared_ui_request' if e['type']=='request' else 'ui_response'
    if producer=='ui':raw['checks'].append({'name':'producer_actual_payload','passed':True,'expected':spec['operations'][0]['input']['article'],'observed':spec['operations'][0]['input']['article']})
    # Separate state-probe exchanges precede the producer and project exactly.
    values=[('/api/user',{'user':{'username':'pilotresearch','email':'pilot@example.com','bio':None,'image':None}}),
            ('/api/articles?author=pilotresearch',{'articles':[],'articlesCount':0}),('/api/tags',{'tags':[]})]
    probes=[];reads=[]
    for path,data in values:
        probes.append({'type':'request','source':'state_probe','phase':'setup','method':'GET','path':path})
        probes.append({'type':'response','source':'state_probe','phase':'setup','method':'GET','path':path,'status':200,'data':data})
        reads.append({'path':path,'status':200,'data':deepcopy(data),'response_sequence':len(probes)})
    expanded=probes;request_id=0;pending={}
    for e in trace:
        if e['type']=='declared_ui_request':
            request_id+=1;meta={'capture_request_id':f'synthetic:{request_id}','context_id':'synthetic','request_phase':e['phase']}
            captured={**deepcopy(e),**meta,'type':'ui_request'};expanded.append(captured)
            pending.setdefault((e['method'],e['path']),[]).append(meta)
        elif e['type']=='ui_response':e.update(pending[(e['method'],e['path'])].pop(0))
        expanded.append(e)
    context={'context_id':'synthetic','complete':True,'timed_out':False,'outstanding':[],'failures':0,'admitted':request_id,'completed':request_id}
    expanded.append({'type':'capture_drain',**context})
    for i,e in enumerate(expanded,1):e['sequence']=i
    raw['trace']=expanded;raw['capture_integrity']={'version':1,'helper_sha256':reducer.CAPTURE_HELPER,'complete':True,'contexts':[context]}
    def guard(name,stage,source,value):return {'name':name,'stage':stage,'source':source,'expected':deepcopy(value),'observed':deepcopy(value),'passed':True}
    guards=[guard('pre_state_readable','setup','shared_api',True)]
    for stage,source,method in [('prefix',producer,'POST'),('continuation',consumer,'PUT')]:
        e=next(e for e in expanded if e['type'] in ('request','declared_ui_request') and e.get('source')==source and e.get('method')==method and e.get('path','').startswith('/api/articles'))
        guards.append(guard('submitted_command',stage,source,{k:e[k] for k in ('method','path','payload')}))
    guards.append(guard('loaded_article_binding','continuation',consumer,reducer.article_state(created,generated=True,slug=True)))
    raw['integrity']={'version':1,'helper_sha256':reducer.INTEGRITY_HELPER,'before':{'readable':True,'reads':reads,'data':reducer.project_integrity_snapshot(reads)},'guards':guards,'rejection':None}
    run.update(cleanup_confirmed=True,reset_sha256='a'*64)
    return raw,run,spec
