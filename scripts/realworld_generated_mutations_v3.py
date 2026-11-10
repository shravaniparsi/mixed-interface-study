"""Bounded mutation qualification plan and terminal-controlled offline driver."""
from copy import deepcopy
from realworld_generated_bindings_v1 import plan as all_jobs,case_for
from mixed_interface.repetition import require,digest
from mixed_interface.terminal_outcomes import decision,POLICY_SHA256
IDS=tuple(f'generated-{i:03d}' for i in range(1,9))
MUTATIONS=('article-body-empty','article-body-null','article-body-omitted','article-body-whitespace',
           'article-tags-omitted','article-title-150','article-title-151')


def plan():
    jobs=[j for j in all_jobs()['jobs'] if j['job_id'] in IDS]
    require(tuple(j['job_id'] for j in jobs)==IDS,'Mutation job inventory differs')
    require(jobs[0]['pair']['intervention']=='route_only' and jobs[0]['pair']['producer_interface']=='api','Reference differs')
    require(tuple(j['pair']['mutation']['transformation_id'] for j in jobs[1:])==MUTATIONS,'Mutation selection differs')
    require(all(j['reference_pair_id']==jobs[0]['pair']['pair_id'] for j in jobs),'Reference bindings differ')
    return {'kind':'exposed_generated_mutation_qualification_v3','jobs':jobs,'candidate_pairs':7,
            'reference_pairs':1,'branches':16,'worker_timeout_s':80,'pair_budget_s':190,
            'outer_timeout_s':1800,'automatic_repeats':False,'resume':False,
            'primary_freeze_complete':False,'application_execution_authorized_by_this_plan':False}


def drive(execute,checkpoint):
    selected=plan();require(len(selected['jobs'])*selected['pair_budget_s']+180<selected['outer_timeout_s'],'Outer budget insufficient')
    report={'status':'running','plan_sha256':digest(selected),'policy_sha256':POLICY_SHA256,
            'started_jobs':[],'completed_jobs':[],'decisions':[],'new_primary_samples':0,'primary_freeze_complete':False}
    checkpoint(deepcopy(report))
    try:
        for job in selected['jobs']:
            report['started_jobs'].append(job['job_id']);checkpoint(deepcopy(report))
            result=execute(deepcopy(job));envelope=result['terminal']
            require(envelope['outcome']['job_id']==job['job_id'],'Result belongs to another job')
            action=decision(envelope)
            if job['job_id']==IDS[0] and envelope['kind']!='clean_observation':action={**action,'action':'halt'}
            report['completed_jobs'].append(job['job_id'])
            report['decisions'].append({'kind':envelope['kind'],**action,'repeat_dispatched':False})
            if action['action']=='halt':
                report['status']='halted_terminal_outcome';checkpoint(deepcopy(report));return report
            checkpoint(deepcopy(report))
        report['status']='completed_bounded_diagnostic';checkpoint(deepcopy(report));return report
    except BaseException as error:
        report.update(status='halted_executor_error',error_type=type(error).__name__,error=str(error));checkpoint(deepcopy(report));raise
