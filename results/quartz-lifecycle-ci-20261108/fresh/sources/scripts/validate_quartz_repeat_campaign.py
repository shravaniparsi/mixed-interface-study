#!/usr/bin/env python3
"""Independently regenerate the controls-only dispatch ledger from raw evidence."""
import argparse
import json
from pathlib import Path
from run_quartz_repeat_campaign import ROOT, SOURCES, read, sha, write
from mixed_interface.campaign import drive
from mixed_interface.repetition import build_plan
from quartz_repeat_outcomes import read_job


def verify(directory):
    directory=Path(directory);certificate=read(directory/'plan.json')
    if set(certificate['source_sha256'])!=set(SOURCES):raise ValueError('Source inventory differs')
    for name,h in certificate['source_sha256'].items():
        if sha(directory/'sources'/name)!=h or sha(ROOT/name)!=h:raise ValueError('Source differs: '+name)
    for name,h in certificate['environment_sha256'].items():
        if sha(directory/name)!=h:raise ValueError('Environment sidecar differs')
    inventory=read(directory/'sources/manifests/paired-candidate-inventory-v1.json')
    expected=build_plan([p for p in inventory['pairs'] if p['catalog']=='quartz_generated_v2' and p['intervention']=='route_only'])
    if certificate['plan']!=expected or len(expected['pairs'])!=2:raise ValueError('Control plan differs')
    registry=read(directory/'sources/manifests/quartz-job-generated-pool-v2.json')
    observed=[]
    def execute(job):
        folder=directory/job['job_id'];dispatch=read(folder/'dispatch.json');execution=read(folder/'execution.json')
        if dispatch['job']!=job or dispatch['order_sha256']!=sha(folder/'order.json'):raise ValueError('Dispatch differs')
        command=dispatch['command']
        if command[command.index('--mode')+1]!='controls':raise ValueError('Unexpected boundary dispatch')
        if not execution['successful_exit'] or not execution['exit_confirmed'] or execution['hard_kill'] or execution['timed_out']:raise ValueError('Incomplete runner')
        result=read_job(folder/'run',job,registry,certificate['source_sha256']['scripts/run_quartz_pair_job.mjs'])
        if result!=read(folder/'observations.json'):raise ValueError('Extracted observations differ')
        summary=read(folder/'run/summary.json')
        if summary['effective_options']['mode']!='controls' or summary['effective_options']['case_timeout_ms']!=75000:raise ValueError('Effective options differ')
        if summary['node_version'].strip()!=read(directory/'environment.json')['node']['output'].strip():raise ValueError('Node version differs')
        for source,archived in [('scripts/quartz_browser_cleanup.py','executed-quartz_browser_cleanup.py'),('scripts/realworld_case_worker.py','executed-realworld_case_worker.py')]:
            if sha(folder/'run'/archived)!=certificate['source_sha256'][source]:raise ValueError('Cleanup helper differs')
        for entry in summary['cases']:
            raw=read(folder/'run'/Path(entry['evidence_directory']).name/'result.json')
            if raw['browser_version']!=read(directory/'browser.json')['declared']['browserVersion']:raise ValueError('Browser version differs')
        observed.append(job['job_id']);return result['outcome']
    regenerated=drive(expected,execute,lambda state:None)
    if regenerated!=read(directory/'campaign.json'):raise ValueError('Campaign ledger differs')
    if regenerated['status']!='completed_observations' or len(regenerated['initial'])!=2 or regenerated['repeated']:raise ValueError('Ordinary control qualification differs')
    if any(o['check_failure'] or o['channel_discrepancy'] or o['prefix']!='accepted' for o in regenerated['initial']):raise ValueError('Control outcome failed')
    actual={p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources'}
    if actual!=set(observed):raise ValueError('Unaccounted job directory')
    return {'status':'verified','source_commit':certificate['source_commit'],'complete_pairs':2,'branches':4,'followup_jobs':0,
            'scope':'Ordinary dispatch qualification; flagged follow-ups exercised by synthetic tests only.',
            'primary_freeze_complete':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    result=verify(args.directory);write(args.directory/'verification.json',result);print(json.dumps(result,indent=2))
