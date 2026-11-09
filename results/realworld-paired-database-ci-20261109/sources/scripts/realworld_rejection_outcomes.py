"""Rejected-state completeness layered over the pinned v2 pair reducer."""
from realworld_terminal_campaign import pair_result as base_pair_result
from mixed_interface.terminal_outcomes import terminal


def pair_result(job,branches,spec,fixture,fixture_sha,cleanup,evidence):
    result=base_pair_result(job,branches,spec,fixture,fixture_sha,cleanup,evidence)
    envelope=result['terminal'];outcome=envelope['outcome'];issues={}
    outcome['observation_signature']['prefix_http_status']={c:raw.get('observations',{}).get('prefix_status') for c,(raw,run) in branches.items()}
    for c,(raw,run) in branches.items():
        status=raw.get('observations',{}).get('prefix_status')
        if type(status) is not int or 200<=status<300:continue
        found=[];rejection=raw.get('integrity',{}).get('rejection',{})
        if rejection.get('status') not in ('unchanged','changed') or rejection.get('after',{}).get('readable') is not True:
            found.append('rejected_state_not_readable')
        if any(e.get('phase')=='continuation' for e in raw.get('trace',[]) if isinstance(e,dict)):
            found.append('trace_has_continuation_after_rejection')
        if raw.get('observations',{}).get('continuation_outcome')!='not_executed_prefix_unsuccessful':
            found.append('missing_explicit_rejection_stop')
        if found:issues[c]=found
    kind=envelope['kind']
    if issues and kind not in ('cleanup_unconfirmed','interrupted','case_timeout','environment_failure','missing_evidence'):
        kind='missing_evidence';outcome.update(execution='incomplete',channel_discrepancy=None,check_failure=None)
    outcome['observation_signature']['rejection_completeness_issues']=issues
    result['terminal']=terminal(outcome,kind,evidence)
    result['rejection_completeness_issues']=issues
    return result
