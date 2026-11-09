"""Source-qualified identity pair observations translated to common terminal v2."""
from realworld_identity_extract_v1 import extract
from mixed_interface.terminal_outcomes import terminal


def pair_result(job,branches,spec,fixture,fixture_sha,cleanup,evidence):
    classified={}
    for channel,(raw,run) in branches.items():
        if cleanup is not True or run.get('backend_exit_confirmed') is not True:value={'kind':'cleanup_unconfirmed'}
        elif run.get('interrupted'):value={'kind':'interrupted'}
        elif run.get('timed_out'):value={'kind':'case_timeout'}
        elif raw.get('execution_status')!='completed' or raw.get('error') or run.get('status')!='completed' or type(run.get('exit_code')) is not int or run['exit_code']!=0:value={'kind':'environment_failure'}
        elif raw.get('continuation_interface')!=channel:value={'kind':'missing_evidence'}
        else:value=extract(raw,spec,fixture)
        classified[channel]=value
    kinds=[v['kind'] for v in classified.values()]
    accepted=[v.get('accepted') for v in classified.values()]
    prefix='unobserved' if not accepted or None in accepted else 'accepted' if all(accepted) else 'rejected' if not any(accepted) else 'mixed'
    gates={};observable={'clean_observation','completed_mismatch','matched_rejection','unresolved_policy'}
    if set(branches)=={'api','ui'} and all(k in observable for k in kinds):
        a,ar=branches['api'];u,ur=branches['ui']
        def command(raw,phase):
            matches=[e for e in raw['trace'] if e['type']=='request' and e.get('method')=='PUT' and e.get('path')=='/api/user' and e.get('request_phase',e['phase'])==phase]
            return matches[0]['payload'] if len(matches)==1 else None
        gates={'same_actor':a['actor']==u['actor'],'same_pre_state':a['identity']['before']['data']==u['identity']['before']['data'],
               'same_prefix_command':command(a,'prefix') is not None and command(a,'prefix')==command(u,'prefix'),
               'same_prefix_status':a['observations']['prefix_status']==u['observations']['prefix_status'],
               'same_reset':isinstance(fixture_sha,str) and len(fixture_sha)==64 and all(c in '0123456789abcdef' for c in fixture_sha) and ar.get('reset_sha256')==ur.get('reset_sha256')==fixture_sha,
               'distinct_branches':ar['case_id']!=ur['case_id'] and ar['evidence']!=ur['evidence'],
               'same_prefix_state':prefix=='rejected' or a.get('prefix_state')==u.get('prefix_state'),
               'same_consumer_command':prefix=='rejected' or (command(a,'continuation') is not None and command(a,'continuation')==command(u,'continuation'))}
    kind=next((k for k in ('cleanup_unconfirmed','interrupted','case_timeout','environment_failure','missing_evidence') if k in kinds),None)
    if cleanup is not True:kind='cleanup_unconfirmed'
    if kind is None and set(branches)!={'api','ui'}:kind='missing_evidence'
    if kind is None and 'application_response_failure' in kinds:kind='application_response_failure'
    if kind is None and (not gates or not all(gates.values()) or prefix=='mixed'):kind='incomparable_observation'
    signals={c:any(v is False for v in result.get('checks',{}).values()) for c,result in classified.items()}
    failure=any(signals.values()) or 'completed_mismatch' in kinds
    if kind is None:kind='completed_mismatch' if failure else 'unresolved_policy' if 'unresolved_policy' in kinds else 'clean_observation' if prefix=='accepted' else 'matched_rejection'
    comparable=bool(gates) and all(gates.values()) and kind in observable
    signature={'branches':classified,'gates':gates,'prefix_http_status':{c:raw.get('observations',{}).get('prefix_status') for c,(raw,_) in branches.items()}}
    outcome={'job_id':job['job_id'],'execution':'complete' if comparable else 'incomplete','prefix':prefix,
             'channel_discrepancy':signals.get('api')!=signals.get('ui') if comparable else None,
             'check_failure':failure if comparable else None,'cleanup_confirmed':cleanup is True and 'cleanup_unconfirmed' not in kinds,
             'observation_signature':signature}
    return {'terminal':terminal(outcome,kind,evidence),'comparability':gates,'branches':classified}
