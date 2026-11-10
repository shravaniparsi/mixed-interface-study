#!/usr/bin/env python3
"""Descriptive phase accounting; never infer independent defects from repeated symptoms."""
from collections import Counter
from mixed_interface.terminal_outcomes import decision,observation_signature
from mixed_interface.repetition import digest,require

def summarize(preparation,initial,second=None,third=None):
    units=preparation['plan']['initial_batches'];require(set(initial)=={u['batch_id'] for u in units},'Initial inventory differs')
    second=second or {};third=third or {};rows=[]
    for unit in units:
        record=initial[unit['batch_id']];obs=record['observations'];candidate=obs[0] if obs else None
        row={'pair_id':unit['target_pair_id'],'entry_kind':unit['jobs'][0]['entry_kind'],'application':unit['application'],
             'initial_status':record['status'],'initial_candidate_observed':candidate is not None,
             'terminal_kind':candidate.get('terminal',{}).get('kind') if candidate else None,
             'repetition_status':'not_triggered','independent_defect_adjudicated':False}
        if row['entry_kind']=='singleton':row['paired_comparison_eligible']=False;rows.append(row);continue
        initial_candidate=candidate.get('terminal') if candidate else None
        if initial_candidate and decision(initial_candidate)['repeat']:
            candidates=[initial_candidate];controls=[]
            if len(obs)==len(unit['jobs']):controls.append(obs[-1]['terminal'])
            for r,data in ((2,second),(3,third)):
                repeated=data.get(unit['batch_id'][:-1]+str(r))
                if repeated:
                    values=repeated['observations']
                    if values:candidates.append(values[0]['terminal'])
                    if len(values)==len(unit['jobs']):controls.append(values[-1]['terminal'])
            complete=len(candidates)==len(controls)==3
            semantic=complete and all(decision(v)['semantic_evidence_complete'] for v in candidates+controls)
            control_clean=all(v['kind']=='clean_observation' for v in controls)
            variable=len({digest(observation_signature(v)) for v in candidates})>1
            row.update(candidate_attempts_observed=len(candidates),control_attempts_observed=len(controls),variability_observed=variable,
                       repetition_status='incomplete_or_blocked' if not complete else 'unresolved_execution' if not semantic else 'unresolved_control_failure' if not control_clean else 'variable_observations' if variable else 'stable_observations')
        rows.append(row)
    return {'kind':'descriptive_primary_unit_summary_v1','rows':rows,'counts':{'entries':len(rows),'pairs':sum(r['entry_kind']=='pair' for r in rows),
            'singletons':sum(r['entry_kind']=='singleton' for r in rows),'initial_candidate_observations':sum(r['initial_candidate_observed'] for r in rows),
            'terminal_kinds':dict(Counter(r['terminal_kind'] or 'unavailable' for r in rows if r['entry_kind']=='pair')),
            'repetition_status':dict(Counter(r['repetition_status'] for r in rows))},'independent_sample_size':None,
            'defects_confirmed':None,'claim_scope':'Source-check and continuation observations; repeated symptoms are not independent defects.'}
