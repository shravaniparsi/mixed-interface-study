#!/usr/bin/env python3
"""Qualify scheduled Quartz dispatch on ordinary controls only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mixed_interface.campaign_v2 import build_plan
from mixed_interface.campaign_v2 import drive
from run_quartz_pairs import run_bounded
from quartz_terminal_outcomes import read_job

SOURCES = ['scripts/quartz_terminal_outcomes.py', 'src/mixed_interface/terminal_outcomes.py', 'src/mixed_interface/campaign_v2.py', 'protocol/terminal-outcomes-v2.md', 'protocol/quartz-terminal-integration-v2.md', 'scripts/validate_quartz_terminal_campaign.py', 'scripts/run_quartz_terminal_campaign.py', 'scripts/run_quartz_pair_job_v2.mjs',
 'scripts/quartz_repeat_outcomes.py', 'scripts/run_quartz_pairs.py', 'scripts/quartz_generated_case.mjs',
 'scripts/summarize_quartz_oracle_components.py','scripts/quartz_browser_cleanup.py','scripts/realworld_case_worker.py',
 'src/mixed_interface/repetition.py','src/mixed_interface/campaign.py',
 'manifests/quartz-job-generated-pool-v2.json','manifests/paired-candidate-inventory-v1.json',
 'manifests/quartz-artifact-lock.json','protocol/quartz-repeat-integration-v1.md']


def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','java','node','output','playwright-module','chrome-executable','environment-file','browser-info'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--python',default=sys.executable)
    args=parser.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    registry=read(ROOT/'manifests/quartz-job-generated-pool-v2.json')
    pairs=[p for p in read(ROOT/'manifests/paired-candidate-inventory-v1.json')['pairs'] if p['catalog']=='quartz_generated_v2' and p['intervention']=='route_only']
    if len(pairs)!=2:raise ValueError('Expected two ordinary control pairs')
    plan=build_plan(pairs)
    certificate={'kind':'quartz_terminal_dispatch_control_qualification','source_commit':os.environ.get('GITHUB_SHA'),
                 'source_sha256':{p:sha(ROOT/p) for p in SOURCES},'plan':plan,'primary_freeze_complete':False,
                 'scope':'Ordinary controls only; boundary dispatch is not enabled by this entry point.',
                 'case_timeout_ms':75000,'pair_timeout_s':180,'shutdown_grace_s':110,'kill_wait_s':5}
    for name in SOURCES:
        dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    for name,path in [('environment.json',args.environment_file),('browser.json',args.browser_info)]:shutil.copyfile(path,out/name)
    certificate['environment_sha256']={n:sha(out/n) for n in ('environment.json','browser.json')}
    write(out/'plan.json',certificate)
    def checkpoint(state):write(out/'campaign.json',state)
    def execute(job):
        for name,h in certificate['source_sha256'].items():
            if sha(ROOT/name)!=h:raise ValueError('Live source changed: '+name)
        directory=out/job['job_id'];directory.mkdir(exist_ok=False)
        order={'schema_version':1,'scope':'quartz_repeat_pair','registry_sha256':certificate['source_sha256']['manifests/quartz-job-generated-pool-v2.json'],'case_ids':[b['case_id'] for b in job['branches']]}
        write(directory/'order.json',order)
        command=[args.node,str(ROOT/'scripts/run_quartz_pair_job_v2.mjs'),'--runtime',str(Path(args.runtime).resolve()),'--java',args.java,'--node',args.node,'--python',args.python,
                 '--registry',str(ROOT/'manifests/quartz-job-generated-pool-v2.json'),'--output',str(directory/'run'),'--mode','controls',
                 '--case-order-file',str(directory/'order.json'),'--case-timeout-ms','75000','--playwright-module',args.playwright_module,'--chrome-executable',args.chrome_executable]
        write(directory/'dispatch.json',{'job':job,'command':command,'order_sha256':sha(directory/'order.json')})
        execution=run_bounded(command,ROOT,directory/'runner.log',timeout=180,grace=110,kill_wait=5);write(directory/'execution.json',execution)
        if not execution['exit_confirmed'] or execution['hard_kill'] or execution['timed_out'] or execution['interrupted'] or execution.get('returncode') not in (0,1):raise RuntimeError('Runner deadline or exit unconfirmed; retain attempt and stop')
        result=read_job(directory/'run',job,registry,certificate['source_sha256']['scripts/run_quartz_pair_job_v2.mjs'])
        browser=read(out/'browser.json');summary=read(directory/'run/summary.json')
        if summary['node_version'].strip()!=read(out/'environment.json')['node']['output'].strip():raise ValueError('Node environment differs')
        for e in summary['cases']:
            raw=read(directory/'run'/Path(e['evidence_directory']).name/'result.json')
            if raw['browser_version']!=browser['declared']['browserVersion']:raise ValueError('Browser environment differs')
        for source, archived in [('scripts/quartz_browser_cleanup.py','executed-quartz_browser_cleanup.py'),('scripts/realworld_case_worker.py','executed-realworld_case_worker.py')]:
            if sha(directory/'run'/archived)!=certificate['source_sha256'][source]:raise ValueError('Cleanup source differs')
        write(directory/'observations.json',result)
        return result['terminal']
    previous=signal.getsignal(signal.SIGTERM)
    def interrupt(*_):raise KeyboardInterrupt('Campaign interrupted')
    signal.signal(signal.SIGTERM,interrupt)
    try:state=drive(plan,execute,checkpoint)
    finally:signal.signal(signal.SIGTERM,previous)
    print(json.dumps({'status':state['status'],'initial_pairs':len(state['initial']),'repeat_jobs':len(state.get('repeated',[])),'output':str(out)}))
    if state['status']!='completed_observations' or any(o['kind']!='clean_observation' for o in state['initial']+state['repeated']):return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
