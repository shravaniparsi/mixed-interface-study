"""Offline generated-case intent and extraction bindings; no dispatch permission."""
from copy import deepcopy
import hashlib, json, sys
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.evaluation import digest, generated_pairs
from mixed_interface.repetition import require
import summarize_realworld_oracle_components as reducer
POOL='manifests/realworld-article-generated-pool-v1.json'
POOL_SHA='e30df6147de81937de728f743607b250755f3b6438d9f1518d0898272b121acc'


def selection():
    data=(ROOT/POOL).read_bytes()
    require(hashlib.sha256(data).hexdigest()==POOL_SHA,'Generated pool changed')
    return json.loads(data)


def plan():
    pool=selection();specs={c['case_id']:c for c in pool['cases']}
    pairs=generated_pairs(pool,'realworld_generated_integration','realworld.article_create_body_edit',
                          {'route_only':'examined_engineering_control','payload_mutation':'examined_engineering_candidate'})
    require(len(pairs)==9 and len(specs)==18,'Generated inventory differs')
    controls={p['producer_interface']:p['pair_id'] for p in pairs if p['intervention']=='route_only'}
    require(set(controls)=={'api','ui'},'Missing same-producer controls')
    jobs=[]
    for i,p in enumerate(pairs):
        order=('api','ui') if i%2==0 else ('ui','api')
        jobs.append({'job_id':f'generated-{i:03d}', 'pair':p,
                     'reference_pair_id':controls[p['producer_interface']],
                     'repetition':1,'branches':[{'channel':c,'case_id':p['case_ids'][c],
                        'source_case_sha256':digest(specs[p['case_ids'][c]]),'fresh_reset_required':True} for c in order]})
    return {'kind':'offline_generated_job_bindings_v1','pool_sha256':POOL_SHA,'jobs':jobs,
            'pairs':9,'branches':18,'execution_authorized':False,'primary_freeze_complete':False,
            'runtime_dispatch_qualified':False,'new_application_executions':0}


def case_for(job, channel):
    require(job in plan()['jobs'],'Foreign or altered generated job')
    require(channel in ('api','ui'),'Invalid continuation channel')
    branch=next(b for b in job['branches'] if b['channel']==channel)
    spec=next(c for c in selection()['cases'] if c['case_id']==branch['case_id'])
    require(digest(spec)==branch['source_case_sha256'],'Source case changed')
    require([o['operation_id'] for o in spec['operations']]==['create_article','edit_article_body'],'Operations differ')
    return spec


def resolve(job, channel, prefix_status, returned_article=None):
    """Preserve exact JSON input; resolve an edit only from an accepted response."""
    spec=case_for(job,channel);producer,consumer=spec['operations']
    result={'case_id':spec['case_id'],'producer_interface':producer['interface'],
            'producer_payload':deepcopy(producer['input']),'requirement_policy':deepcopy(spec['expectation']),
            'consumer_interface':consumer['interface'],'consumer_command':None}
    require(type(prefix_status) is int,'Missing HTTP status')
    if prefix_status!=201:
        result['resolution']='prefix_unsuccessful';return result
    require(isinstance(returned_article,dict),'Missing accepted article')
    slug=returned_article.get('slug')
    if not isinstance(slug,str) or not slug.strip():
        result['resolution']='empty_or_invalid_reference';return result
    require(all(isinstance(returned_article.get(k),str) for k in ('title','description','body')),'Incomplete returned fields')
    tags=returned_article.get('tagList')
    require(isinstance(tags,list) and all(isinstance(t,str) for t in tags),'Invalid returned tags')
    require(returned_article.get('author',{}).get('username')=='pilotresearch','Returned actor differs')
    edit={k:deepcopy(returned_article[k]) for k in ('title','description','tagList')}
    edit['body']=consumer['input']['article']['body']
    result.update(resolution='resolved_intent_only',reference=slug,
                  consumer_command={'method':'PUT','path':'/api/articles/'+quote(slug,safe="~()*!.'-"),'payload':{'article':edit}})
    return result


def extract(job, channel, raw, run):
    """Pure, fail-closed component extraction. Caller must qualify source artifacts.

    A complete component result is not a terminal pair, cleanup certificate,
    runtime qualification or authorization to execute the plan.
    """
    spec=case_for(job,channel)
    require(raw.get('case_id')==run.get('case_id')==spec['case_id'],'Evidence case differs')
    require(raw.get('route')==run.get('route')==[o['interface'] for o in spec['operations']],'Evidence route differs')
    issues=reducer.capture_integrity_issues(raw,required=True)+reducer.execution_integrity_issues(raw,required=True)
    result=reducer.reduce_case(raw,run,spec,family='generated',provenance_issues=issues)
    return {'source_case_sha256':digest(spec),'components':result,
            'runtime_dispatch_qualified':False,'primary_freeze_complete':False,
            'scope':'pure extraction; source-qualified file loader and pair terminal bridge still required'}
