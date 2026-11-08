#!/usr/bin/env python3
"""Generate the Quartz schedule and synthetic policy checks; never execute cases."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mixed_interface.repetition import build_plan, followups, summarize


def synthetic(job, failed=False):
    return {'job_id': job['job_id'], 'execution': 'complete', 'prefix': 'accepted',
            'channel_discrepancy': False, 'check_failure': failed, 'cleanup_confirmed': True,
            'observation_signature': {'synthetic_verdict': 'mismatch' if failed else 'no_mismatch'}}


def build():
    inventory = json.loads((ROOT/'manifests/paired-candidate-inventory-v1.json').read_bytes())
    pairs = [p for p in inventory['pairs'] if p['catalog'] == 'quartz_generated_v2']
    if len(pairs) != 22 or sum(p['intervention'] == 'route_only' for p in pairs) != 2:
        raise ValueError('Unexpected Quartz inventory')
    plan = build_plan(pairs)
    initial = [synthetic(j) for j in plan['initial_jobs']]
    flagged = deepcopy(initial); selected = next(i for i,p in enumerate(pairs) if p['intervention'] == 'payload_mutation')
    flagged[selected] = synthetic(plan['initial_jobs'][selected], True)
    repeated = followups(plan, flagged)
    records = [synthetic(j, j['role'] == 'candidate_repeat') for j in repeated['jobs']]
    variable = deepcopy(records); variable[0]['observation_signature'] = {'synthetic_verdict': 'changed'}
    unsafe = deepcopy(initial); unsafe[-1]['cleanup_confirmed'] = False
    paths = ['src/mixed_interface/repetition.py','scripts/prepare_quartz_repeat_policy.py',
             'manifests/paired-candidate-inventory-v1.json','manifests/quartz-job-generated-pool-v2.json',
             'protocol/boundary-repeat-policy-v1.md']
    return {'kind':'repeat_policy_planning_and_synthetic_verification','applications_executed':0,
            'unexecuted_quartz_boundary_branches':40,'primary_freeze_complete':False,
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'plan':plan,'initial_branch_slots':sum(len(j['branches']) for j in plan['initial_jobs']),
            'synthetic_scenarios':{'all_clean':followups(plan,initial),'one_flagged':repeated,
              'stable_repeats':summarize(plan,flagged,records),'variable_repeats':summarize(plan,flagged,variable),
              'missing_repeat':summarize(plan,flagged,records[:-1]),'partial_sweep':followups(plan,initial[:-1]),
              'unconfirmed_cleanup':followups(plan,unsafe)},
            'limits':'Synthetic state-machine checks are not application results. Source-qualified boundary outcome extraction, runner integration and execution freeze remain open.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=build();path=ROOT/'results/quartz-repeat-policy-20261108/analysis.json'
    if args.verify:
        if json.loads(path.read_bytes())!=result:raise ValueError('Saved schedule differs')
    else:
        path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'verified' if args.verify else 'prepared','initial_pair_slots':len(result['plan']['initial_jobs']),'initial_branch_slots':result['initial_branch_slots'],'applications_executed':0,'primary_freeze_complete':False}))
if __name__=='__main__':main()
