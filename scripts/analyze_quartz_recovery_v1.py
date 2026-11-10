#!/usr/bin/env python3
"""Descriptive source-component overlap and timing strata; no defect adjudication."""
import argparse,json,statistics,math
from collections import Counter,defaultdict
from pathlib import Path
from quartz_recovery_preflight_v1 import ROOT,PREPARATION,read,sha
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import digest
from verify_quartz_recovery_collection_v1 import verify
from summarize_primary_units_v1 import summarize
from audit_quartz_form_measurement_v1 import measurement_issue

def component_overlap(loaded):
    result=loaded['runtime_result'];result=result.get('legacy_result',result)
    if 'terminal' not in result:return {'category':'singleton','signals':{}}
    terminal=result['terminal'];branches=result.get('branches',result.get('branch_classifications',{}));signals={}
    for channel,branch in branches.items():
        components=branch.get('components',{}).get('components',{})
        signals[channel]={name:{k:value.get(k) for k in ('status','comparison_eligible','mismatch_observed','failed_check_ids')} for name,value in components.items()}
    base={'signals':signals,'terminal_kind':terminal['kind']}
    if terminal['kind']=='matched_rejection':return {**base,'category':'prefix_rejected'}
    if terminal['kind'] not in ('clean_observation','completed_mismatch') or terminal['outcome']['prefix']!='accepted':return {**base,'category':'unresolved'}
    selected=[signals.get(c,{}).get('assigned_api_continuation' if c=='api' else 'assigned_native_continuation',{}) for c in ('api','ui')]
    if not all(v.get('comparison_eligible') is True and type(v.get('mismatch_observed')) is bool for v in selected):return {**base,'category':'not_comparison_eligible'}
    a,u=[v['mismatch_observed'] for v in selected]
    category='both_assigned_mismatch' if a and u else 'api_only_assigned_mismatch' if a else 'ui_only_assigned_mismatch' if u else 'neither_assigned_mismatch'
    return {**base,'category':category}

def analyze(initial_manifest,second_manifest=None,third_manifest=None):
    manifests=[p for p in (initial_manifest,second_manifest,third_manifest) if p is not None]
    phases={};folders={};times=[];setup=[]
    catalog={b['entry']['pair_id']:b for b in read(ROOT/'manifests/primary-runtime-catalog-v1.json')['bindings']}
    for path in manifests:
        m=read(path);value=verify(path);phases[value['mode']]=value
        for request in sorted((ROOT/m['archive_root']).glob('*/requested-unit.json')):
            r=read(request);folder=request.parent/'quartz-recovery-unit-v1';folders[(value['mode'],r['batch'])]=folder
            if not (folder/'plan.json').exists():continue
            cert=read(folder/'plan.json');unit=cert['unit'];versions=read(folder/'runtime-versions.json')
            host={'image_version':versions['runner']['ImageVersion'],'platform':versions['platform']}
            if (folder/'setup.json').exists():setup.append({'mode':value['mode'],'batch_id':r['batch'],**host,**read(folder/'setup.json')})
            verified_attempts={o['attempt_id'] for o in value['records'][r['batch']]['observations']}
            for job in unit['jobs']:
                if job['attempt_id'] not in verified_attempts:continue
                p=folder/job['attempt_id']/'loaded.json'
                if not p.exists():continue
                loaded=read(p)
                for channel,cost in loaded['branch_total_s'].items():times.append({'mode':value['mode'],'batch_id':r['batch'],'attempt_id':job['attempt_id'],'role':job['role'],
                    'pair_id':job['entry_pair_id'],'workflow_id':catalog[job['entry_pair_id']]['entry']['workflow_id'],'runtime_context_sha256':digest(job['runtime']['context']),'profile':job['runtime']['profile'],'application':unit['application'],'channel':channel,'branch_total_s':cost,**host})
                if job['runtime']['profile'].startswith('rw_'):
                    for summary in sorted((p.parent/'runtime/run').glob('*/summary.json')):
                        raw=read(summary);setup.append({'mode':value['mode'],'batch_id':r['batch'],'attempt_id':job['attempt_id'],**host,
                            'native_common_fixture_frontend_setup_s':raw.get('common_fixture_frontend_setup_s'),'scope':'Native pair setup; separate from controller setup and branch costs'})
    result=summarize(read(PREPARATION),phases['initial']['records'],phases.get('repeat2',{}).get('records'),phases.get('repeat3',{}).get('records'))
    catalog={b['entry']['pair_id']:b for b in read(ROOT/'manifests/primary-runtime-catalog-v1.json')['bindings']}
    unit_by_pair={u['target_pair_id']:u for u in read(PREPARATION)['plan']['initial_batches']}
    for row in result['rows']:
        binding=catalog[row['pair_id']];unit=unit_by_pair[row['pair_id']];folder=folders[('initial',unit['batch_id'])]
        path=folder/unit['jobs'][0]['attempt_id']/'loaded.json'
        row.update(workflow_id=binding['entry']['workflow_id'],catalog=binding['entry']['catalog'],prior_exposure=binding['entry']['prior_exposure'],
                   assigned_overlap=component_overlap(read(path)) if row['initial_candidate_observed'] and path.exists() else {'category':'unavailable','signals':{}})
        if not phases['initial']['verification'][unit['batch_id']]['qualified_observations']:
            row['assigned_overlap'].update(category='unresolved',unit_acceptance='not_qualified')
        issue=measurement_issue(path.parent) if path.exists() else None
        if issue:
            row['measurement_issue']=issue
            row['recorded_assigned_overlap_category']=row['assigned_overlap']['category']
            row['assigned_overlap']['category']='measurement_invalid'
        row['original_catalog_prior_exposure']=row['prior_exposure']
        row['prior_exposure']='exposed_after_original_collection'
    result['kind']='descriptive_quartz_provider_recovery_summary_v1'
    result['cohort_scope']='Additional exposed provider-recovery cohort; distinct from both the original and incomplete corrected collection.'
    result['assigned_overlap_counts']=dict(Counter(r['assigned_overlap']['category'] for r in result['rows']))
    result['by_application']={app:dict(Counter(r['assigned_overlap']['category'] for r in result['rows'] if r['application']==app)) for app in sorted({r['application'] for r in result['rows']})}
    result['by_prior_exposure']={exposure:dict(Counter(r['assigned_overlap']['category'] for r in result['rows'] if r['prior_exposure']==exposure)) for exposure in sorted({r['prior_exposure'] for r in result['rows']})}
    result['phase_accounting']={mode:{
        'units_retained':len(phase['records']),
        'unit_statuses':dict(Counter(record['status'] for record in phase['records'].values())),
        'units_with_qualified_observations':sum(v['qualified_observations'] for v in phase['verification'].values()),
        'attempts_started':sum(len(record['started']) for record in phase['records'].values()),
        'sealed_pair_observations':sum(o['entry_kind']=='pair' for record in phase['records'].values() for o in record['observations']),
        'sealed_singleton_observations':sum(o['entry_kind']=='singleton' for record in phase['records'].values() for o in record['observations']),
        'sealed_branch_intervals':sum(t['mode']==mode for t in times)
    } for mode,phase in phases.items()}
    result['timing_measurements']=times;result['separately_recorded_setup']=setup
    strata=defaultdict(list)
    for t in times:strata[(t['profile'],t['image_version'],t['platform'],t['channel'],t['role'],t['workflow_id'],t['pair_id'],t['runtime_context_sha256'])].append(t['branch_total_s'])
    result['timing_strata']=[{'profile':k[0],'image_version':k[1],'platform':k[2],'channel':k[3],'role':k[4],'workflow_id':k[5],'pair_id':k[6],'runtime_context_sha256':k[7],
                            'observations':len(v),'median_s':statistics.median(v),'min_s':min(v),'max_s':max(v),'total_s':math.fsum(v)} for k,v in sorted(strata.items())]
    result['input_manifest_sha256']={str(p.relative_to(ROOT)):sha(p) for p in manifests}
    result['interpretation']='Assigned-component check signals only. Shared verification is reported separately and earns no channel-exclusive credit. Unknown, unavailable and rejected outcomes retain separate categories. Timings remain source/host strata and are not an efficacy comparison.'
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--initial',type=Path,required=True);p.add_argument('--second',type=Path);p.add_argument('--third',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    v=analyze(a.initial.resolve(),a.second.resolve() if a.second else None,a.third.resolve() if a.third else None);write(a.output,v);print(json.dumps(v['counts'],indent=2))
