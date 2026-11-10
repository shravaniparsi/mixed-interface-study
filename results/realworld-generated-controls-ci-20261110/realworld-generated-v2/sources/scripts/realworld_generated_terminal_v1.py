"""Generated branch and pair terminal semantics; no runtime authorization."""
from realworld_generated_bindings_v1 import extract, case_for
from mixed_interface.terminal_outcomes import terminal


def classify(job, channel, raw, run):
    if run.get('cleanup_confirmed') is not True:
        return {'kind':'cleanup_unconfirmed','issues':['owned_cleanup_not_confirmed']}
    for field,kind in [('interrupted','interrupted'),('timed_out','case_timeout')]:
        if run.get(field) is True:return {'kind':kind,'issues':[field]}
    if not raw:return {'kind':'missing_evidence','issues':['missing_raw_evidence']}
    if run.get('exit_code')!=0 or raw.get('status')!='completed' or raw.get('error'):
        return {'kind':'environment_failure','issues':['unclassified_worker_failure']}
    try:
        reduced=extract(job,channel,raw,run)['components']
    except (ValueError,KeyError,TypeError,AttributeError,IndexError):
        return {'kind':'missing_evidence','issues':['invalid_bound_evidence']}
    issues=list(reduced['evidence_issues'])
    if not reduced['accepted_prefix']:
        rejection=raw.get('integrity',{}).get('rejection') or {}
        if rejection.get('status') not in ('unchanged','changed') or rejection.get('after',{}).get('readable') is not True:
            issues.append('rejected_state_not_readable')
    if issues:return {'kind':'missing_evidence','issues':sorted(set(issues)),'components':reduced}
    failed=any(p['mismatch_observed'] for k,p in reduced['components'].items()
               if k not in ('environment_reset_cleanup','unresolved_policy'))
    kind=('completed_mismatch' if failed else 'unresolved_policy' if reduced['policy_unresolved']
          else 'clean_observation' if reduced['accepted_prefix'] else 'matched_rejection')
    return {'kind':kind,'issues':[],'components':reduced}


def command(raw,stage):
    guards=[g for g in raw.get('integrity',{}).get('guards',[]) if g.get('name')=='submitted_command' and g.get('stage')==stage]
    return guards[0]['observed'] if len(guards)==1 and guards[0].get('passed') is True else None


def combine(job, classified, gates, evidence):
    """Pure terminal decision over already classified branches and comparison gates."""
    kinds=[v['kind'] for v in classified.values()]
    cleanup='cleanup_unconfirmed' not in kinds
    prefix_values=[v.get('components',{}).get('accepted_prefix') for v in classified.values()]
    prefix=('unobserved' if len(prefix_values)!=2 or None in prefix_values else
            'accepted' if all(prefix_values) else 'rejected' if not any(prefix_values) else 'mixed')
    kind=next((k for k in ('cleanup_unconfirmed','interrupted','case_timeout','environment_failure','missing_evidence') if k in kinds),None)
    if kind is None and set(classified)!={'api','ui'}:kind='missing_evidence'
    if kind is None and (not gates or not all(gates.values()) or prefix in ('mixed','unobserved')):kind='incomparable_observation'
    if kind is None:kind=('completed_mismatch' if 'completed_mismatch' in kinds else 'unresolved_policy' if 'unresolved_policy' in kinds else 'clean_observation' if prefix=='accepted' else 'matched_rejection')
    comparable=kind in ('clean_observation','matched_rejection','completed_mismatch','unresolved_policy')
    signals={c:v.get('components',{}).get('components',{}).get('assigned_api_continuation' if c=='api' else 'assigned_native_continuation',{}).get('mismatch_observed') for c,v in classified.items()}
    outcome={'job_id':job['job_id'],'execution':'complete' if comparable else 'incomplete','prefix':prefix,
             'cleanup_confirmed':cleanup,'channel_discrepancy':signals.get('api')!=signals.get('ui') if comparable else None,
             'check_failure':'completed_mismatch' in kinds if comparable else None,
             'observation_signature':{'branch_kinds':{c:v['kind'] for c,v in classified.items()},'gates':gates,
                 'checks':{c:{name:[[x['id'],x['passed'],x['scope']] for x in part.get('checks',[])]
                              for name,part in v.get('components',{}).get('components',{}).items()}
                           for c,v in classified.items()}}}
    return terminal(outcome,kind,evidence)


def compare(job,branches,evidence):
    for channel in branches:case_for(job,channel)
    classified={c:classify(job,c,*value) for c,value in branches.items()}
    complete={'clean_observation','matched_rejection','completed_mismatch','unresolved_policy'}
    gates={}
    if set(branches)=={'api','ui'} and all(v['kind'] in complete for v in classified.values()):
        a,ar=branches['api'];u,ur=branches['ui'];accepted=all(v['components']['accepted_prefix'] for v in classified.values())
        gates={'same_reset':bool(ar.get('reset_sha256')) and ar.get('reset_sha256')==ur.get('reset_sha256'),
               'distinct_branch':ar.get('case_id')!=ur.get('case_id'),
               'same_pre_state':a['integrity']['before']==u['integrity']['before'],
               'same_prefix_status':a['prefix_status']==u['prefix_status'],
               'same_prefix_command':command(a,'prefix') is not None and command(a,'prefix')==command(u,'prefix'),
               'same_prefix_state':not accepted or a.get('accepted_producer')==u.get('accepted_producer'),
               'same_reference':not accepted or bool(a.get('resource_reference')) and a.get('resource_reference')==u.get('resource_reference'),
               'same_consumer_command':not accepted or command(a,'continuation') is not None and command(a,'continuation')==command(u,'continuation')}
    return {'terminal':combine(job,classified,gates,evidence),'branches':classified,'comparability':gates,
            'runtime_dispatch_qualified':False,'primary_freeze_complete':False}
