"""Attach live reference-proof evidence; close only the exact qualified binding."""
from collections import Counter
from copy import deepcopy
from .coverage_review_v2 import require
from .evaluation import digest

EXPECTED=('legacy-000','legacy-001','legacy-004','legacy-005','legacy-006','legacy-007','legacy-008')
GAP='prospective_reference_comparison_binding'


def reconcile(previous,attempts):
    require(previous['execution_authorized'] is False and previous['primary_freeze_complete'] is False,
            'Previous review promoted')
    rows=deepcopy(previous['rows'])
    require(len(rows)==75 and not any(r['primary_dispatch_ready'] for r in rows),'Corpus changed or promoted')
    index={r['inventory_entry']['candidate_id']:r for r in rows if r['inventory_entry']['catalog']=='realworld_development'}
    require(tuple(a['job']['job_id'] for a in attempts)==EXPECTED,'Attempt inventory or order differs')
    closed=[]
    for a in attempts:
        job=a['job'];spec=a['spec'];cid=job['candidate_id'];require(cid in index,'Foreign candidate')
        row=index[cid]
        require(a['application_run']==42764442019 and a['source_commit']=='dbd73458aa2945ec9de932deee73ec54f716fa2f', 'Runtime source differs')
        require(a['new_primary_samples']==0 and a['primary_freeze_complete'] is False,'Attempt promoted')
        require(row['entry_kind']==job['entry_kind'] and spec['candidate_id']==cid,'Cardinality or candidate differs')
        require(job['source_case_sha256']==digest(spec) and all(b['source_case_sha256']==digest(spec) for b in row['branches']),'Source case differs')
        require([b['continuation'] for b in job['branches']]==a['channels'] and
                set(a['channels'])=={b['continuation_interface'] for b in row['branches']},'Channel inventory differs')
        require('observed_reference_runtime_attempts' not in row,'Duplicate candidate')
        value={k:deepcopy(v) for k,v in a.items() if k not in ('job','spec')};value['job_id']=job['job_id']
        row['observed_reference_runtime_attempts']=[value]
        row['reference_runtime_resolved_requirements']=[]
        if a['evidence'] not in row['recorded_engineering_evidence']:row['recorded_engineering_evidence'].append(a['evidence'])
        if GAP in row['remaining_execution_requirements']:
            proof=a['reference_comparison']
            require(cid=='article-update-duplicate-full' and job['entry_kind']=='pair','Unexpected reference binding')
            require(a['literal_kind']==proof['original_kind']=='incomparable_observation' and
                    a['terminal_kind']==proof['derived_kind']=='clean_observation' and
                    proof['reference_comparison_qualified'] is True and proof['local_bindings']=={'api':True,'ui':True} and
                    bool(proof['derived_gates']) and all(proof['derived_gates'].values()),'Reference proof does not qualify')
            require('legacy_primary_campaign_binding' in row['remaining_execution_requirements'],'Primary binding lost')
            row['remaining_execution_requirements'].remove(GAP)
            row['reference_runtime_resolved_requirements'].append(GAP);closed.append(cid)
    require(closed==['article-update-duplicate-full'],'Reference closure inventory differs')
    result=deepcopy(previous);result.update(schema_version=5,rows=rows)
    result['counts'].update(entries_with_recorded_engineering_evidence=sum(bool(r['recorded_engineering_evidence']) for r in rows),
                           reference_runtime_entries=7,reference_runtime_bindings_qualified=1)
    result['remaining_execution_requirement_counts']=dict(sorted(Counter(g for r in rows for g in r['remaining_execution_requirements']).items()))
    result['interpretation']='Live v10 evidence closes one exact prospective reference-comparison binding. Original archived incomparable classifications remain historical evidence. No catalog entry or independent sample is added, and primary-campaign requirements remain open. P2-P5 remain open.'
    return result
