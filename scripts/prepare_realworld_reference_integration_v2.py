#!/usr/bin/env python3
"""Replay the prospective bridge and scheduler over a verified immutable archive."""
import argparse,json
from realworld_terminal_campaign import ROOT,read,sha
from verify_realworld_fresh_legacy_archive import verify,MANIFEST
from realworld_legacy_jobs_v8 import selection
from realworld_legacy_jobs_v10 import read_job
from realworld_legacy_campaign_v10 import drive,plan_for
from validate_realworld_legacy_campaign_v10 import verify_accounting
from run_realworld_legacy_campaign_v10 import SOURCES
OUTPUT=ROOT/'manifests/realworld-reference-integration-v2.json'
INPUTS=sorted(set(SOURCES+['scripts/prepare_realworld_reference_integration_v2.py',
    'tests/test_realworld_reference_integration_v2.py','manifests/realworld-fresh-legacy-integration.json']))


def build():
    verify();registry=selection();root=ROOT/read(MANIFEST)['archive_root']/'realworld-legacy-v9'
    observations={};results=[]
    for job in plan_for(registry)['jobs']:
        d=root/job['job_id'];value=read_job(d,job,registry,read(d/'execution.json'))
        observations[job['job_id']]=value
        original=read(d/'observations.json')
        paired=job['entry_kind']=='pair'
        results.append({'job_id':job['job_id'],'entry_kind':job['entry_kind'],
            'original_kind':original['terminal']['kind'] if paired else original['branch']['kind'],
            'integrated_kind':value['terminal']['kind'] if paired else value['branch']['kind'],
            'reference_comparison_qualified':value['reference_comparison']['reference_comparison_qualified'] if paired else False,
            'singleton_unchanged':value==original if not paired else None})
    report=drive(registry,lambda job:observations[job['job_id']],lambda _:None)
    verify_accounting(registry,report,observations)
    return {'kind':'prospective_reference_bridge_archive_replay_v2','source_sha256':{s:sha(ROOT/s) for s in INPUTS},
        'replayed_application_run':42708069641,'jobs':results,'replayed_ledger':report,
        'prospective_terminal_bridge_integrated':True,'runtime_dispatch_qualified':False,
        'original_archive_modified':False,'new_application_executions':0,'new_primary_samples':0,'primary_freeze_complete':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();v=build()
    if args.verify:
        if v!=read(OUTPUT):raise ValueError('Reference integration replay differs')
    else:OUTPUT.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['jobs'],indent=2))
