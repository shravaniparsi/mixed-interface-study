#!/usr/bin/env python3
"""Validate bounded interrupted/deadline records and fresh Quartz controls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/ci'))
from run_quartz_repeat_campaign import read,sha,write
from validate_quartz_repeat_campaign import verify as verify_fresh
from run_quartz_lifecycle import QUALIFIED_SOURCES


def require(value,message):
    if not value:raise ValueError(message)


def validate_failure(stage,record,campaign,execution,summary):
    require(stage in ('external_sigterm','case_deadline'),'Unknown probe')
    require(record['returncode']==1,'Interrupted campaign unexpectedly successful')
    require(campaign['status']=='halted_executor_error' and len(campaign['dispatches'])==1,'Campaign failed to stop after first job')
    require(campaign['initial']==[] and campaign['repeated']==[] and 'followup_plan' not in campaign,'Incomplete attempt entered repetition accounting')
    require(campaign['dispatches'][0]['job']['job_id']=='initial-000' and campaign['dispatches'][0]['error'],'Missing failed dispatch record')
    require(execution['exit_confirmed'] and not execution['successful_exit'] and not execution['hard_kill'] and not execution['timed_out'],'Pair runner exit unresolved or outer timeout used')
    require(summary['mode']=='controls' and summary['status']=='incomplete' and len(summary['cases'])==1 and summary['case_count']==2,'Failure lost or next branch executed')
    require(summary['effective_options']['case_timeout_ms']==75000 and summary['validation_interrupt_at'] is None,'Ordinary deadline path was replaced')
    branch=summary['cases'][0]
    require(branch['completed'] is False and branch['status']=='interrupted','Interrupted branch marked complete')
    require(branch['application_port_released'] and branch['browser_process_absent'],'Branch cleanup incomplete')
    require(all(branch[k]['ok'] for k in ('node_cleanup','java_cleanup','browser_cleanup')),'Owned cleanup not confirmed')
    if stage=='external_sigterm':
        require(record['injection']=={'signal':'SIGTERM','target':'campaign'},'Wrong external signal target')
        require(execution['interrupted'] is True and 0<=record['exit_after_signal_s']<=120,'External stop deadline or signal attribution differs')
        require(summary.get('interruption')=='SIGTERM','Pair runner did not receive SIGTERM')
    else:
        require(record['injection']['signal']=='SIGSTOP' and record['injection']['target']=='owned_adapter','Wrong deadline injection')
        stopped=record['injection']['suspended_identity'];adapter=record['checkpoint']['adapter']
        require((stopped['pid'],stopped['start_ticks'])==(adapter['pid'],adapter['start_ticks']) and stopped['state'] in ('T','t'),'Suspension identity not confirmed')
        require(execution['interrupted'] is False and branch['timed_out'] is True,'Ordinary case timeout not observed')
        require(branch['child_exit']['signal']=='SIGKILL','Hard deadline path not exercised')
        require(75000<=branch['elapsed_ms']<=105000,'Case deadline exceeded declared bounded envelope')
        require(record['elapsed_s']<=130,'Deadline stage exceeded bound')
    return branch


def verify(directory):
    directory=Path(directory);plan=read(directory/'plan.json');report=read(directory/'report.json')
    require(report['status']=='observations_complete' and not report['rescue_actions'],'Incomplete probes or rescue used')
    require(report['source_commit']==plan['source_commit'] and report['source_sha256']==plan['source_sha256'],'Plan/source mismatch')
    require(set(plan['source_sha256'])==set(QUALIFIED_SOURCES),'Source inventory mismatch')
    for name,h in plan['source_sha256'].items():
        require(sha(ROOT/name)==h==sha(directory/'sources'/name),'Source mismatch: '+name)
    require(list(report['stages'])==['external_sigterm','case_deadline','fresh'],'Stage order differs')
    durations={}
    for stage,record in report['stages'].items():
        require(record['status']=='observed','Stage observation incomplete')
        cleanup=record['cleanup'];require(cleanup['observed_processes'] and not cleanup['live_survivors'] and cleanup['application_port_open'] is False,'Post-stage cleanup failed')
        if stage=='fresh':
            require(record['returncode']==0,'Fresh controls failed')
            require(verify_fresh(directory/stage)==record['fresh_verification'],'Fresh verification does not reproduce')
            continue
        point=record['checkpoint'];require(point['elapsed_s']<=90,'Checkpoint deadline exceeded')
        metadata_path=directory/stage/point['metadata_path']
        require(metadata_path.resolve().is_relative_to((directory/stage).resolve()),'Metadata path escapes stage')
        require(read(metadata_path)==point['browser_metadata'],'Archived browser identity differs')
        require(point['browser_metadata']['marker'] in point['browser']['command'] and point['browser_metadata']['pid']==point['browser']['pid'],'Browser identity differs')
        require('quartz_generated_case.mjs' in point['adapter']['command'] and 'PropertiesLauncher' in point['java']['command'],'Checkpoint lacks owned adapter/JVM')
        known={(p['pid'],p['start_ticks']) for p in point['observed_descendants']}
        require(all((point[k]['pid'],point[k]['start_ticks']) in known for k in ('adapter','java','browser')),'Checkpoint identity not observed')
        folder=directory/stage;campaign=read(folder/'campaign.json');job=folder/'initial-000';execution=read(job/'execution.json');summary=read(job/'run/summary.json')
        branch=validate_failure(stage,record,campaign,execution,summary)
        require(read(job/'run'/Path(branch['evidence_directory']).name/'run.json')==branch,'Branch/summary differs')
        require([b['case_id'] for b in campaign['dispatches'][0]['job']['branches']]==summary['ordering']['case_ids'],'Dispatched pair differs')
        require(read(job/'dispatch.json')['job']==campaign['dispatches'][0]['job'],'Dispatch record differs')
        require(branch['case_id']==summary['ordering']['case_ids'][0],'Unexpected attempted branch')
        require({p.name for p in folder.iterdir() if p.is_dir()}=={'sources','initial-000'},'Unaccounted or continued jobs')
        for source,archived in [('scripts/run_quartz_pair_job.mjs','executed-runner.mjs'),('scripts/quartz_generated_case.mjs','executed-adapter.mjs'),('manifests/quartz-job-generated-pool-v2.json','executed-registry.json'),('scripts/quartz_browser_cleanup.py','executed-quartz_browser_cleanup.py'),('scripts/realworld_case_worker.py','executed-realworld_case_worker.py')]:
            require(sha(job/'run'/archived)==plan['source_sha256'][source],'Executed source differs')
        durations[stage]={'campaign_s':record['elapsed_s'],'branch_s':branch['elapsed_ms']/1000}
    return {'status':'verified','source_commit':report['source_commit'],'probes':durations,
            'external_exit_after_signal_s':report['stages']['external_sigterm']['exit_after_signal_s'],
            'fresh_pairs':2,'fresh_branches':4,'rescue_actions':0,'boundary_branches_executed':0,
            'primary_freeze_complete':False,'scope':'One live-browser SIGTERM checkpoint and one suspended-adapter ordinary deadline probe, then four fresh controls.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    result=verify(args.directory);write(args.directory/'verification.json',result);print(json.dumps(result,indent=2))
