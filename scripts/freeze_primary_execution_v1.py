#!/usr/bin/env python3
"""Issue a dated freeze only after complete exposed smoke reconstruction."""
import argparse,datetime
from primary_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha,sources
from verify_primary_collection_v1 import verify
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require

def freeze(smoke_manifest,unit_run):
    require(not FREEZE.exists(),'A primary freeze already exists; never overwrite it')
    prep=read(PREPARATION);sources(prep);smoke=read(smoke_manifest);v=verify(smoke_manifest)
    require(v['mode']=='smoke' and v['all_units_qualified'] and v['preparation_sha256']==sha(PREPARATION),'Smoke qualification incomplete or foreign')
    require(set(v['records'])=={u['batch_id'] for u in prep['smoke_units']},'Smoke inventory differs')
    for record in v['records'].values():
        require(record['status']=='completed_observations' and len(record['observations'])==2 and all(o['terminal']['kind']=='clean_observation' for o in record['observations']),'Smoke controls not clean')
    value={'kind':'dated_primary_diagnostic_freeze_v1','frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'preparation_sha256':sha(PREPARATION),'plan_sha256':prep['plan']['plan_sha256'],
           'smoke_manifest':str(smoke_manifest.relative_to(ROOT)),'smoke_manifest_sha256':sha(smoke_manifest),
           'smoke_application_run':smoke['application_run'],'source_ci_run':unit_run,'qualified_source_commit':smoke['source_commit'],
           'selected_entries':[u['target_pair_id'] for u in prep['plan']['initial_batches']],
           'initial_units':75,'potential_followup_units':146,'primary_freeze_complete':True,
           'scope':'Descriptive equal-candidate diagnostic observations; no selector efficacy or confirmed-defect claim.',
           'unsupported_outcomes':'Registered unsupported accepted states, unreadable states, missing evidence and unknown policies remain blocked/unresolved; no synthetic coverage or outcome repair.',
           'adjudication_pending':['independent human requirement/root-cause adjudication','prior-report novelty assessment'],
           'environment_acceptance':prep['environment'],'replacement_or_resume_allowed':False,
           'budget':{'maximum_initial_and_followup_hosted_minutes':6630,'linux_list_rate_usd_per_minute':0.006,
                     'maximum_initial_and_followup_compute_usd':39.78,'additional_storage_and_validation_reserve_usd':10,
                     'pricing_source':'https://docs.github.com/en/billing/reference/actions-runner-pricing',
                     'account_invoice_verified':False,'interpretation':'Conservative job-ceiling estimate before included minutes, not an invoice or measured spend.'}}
    write(FREEZE,value);return value
if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--smoke-manifest',type=Path,required=True);p.add_argument('--unit-run',type=int,required=True);a=p.parse_args()
    v=freeze(a.smoke_manifest.resolve(),a.unit_run);print(v['frozen_at_utc'])
