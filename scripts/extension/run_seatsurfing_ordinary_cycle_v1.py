#!/usr/bin/env python3
"""One ordinary cycle; enclosing registered parent owns deadlines and cleanup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from seatsurfing_ordinary_coordinator_v1 import OrdinaryCoordinator, write_private
from seatsurfing_fixture_resources_v1 import inspect_resources, APP, PG, BROWSER
from run_seatsurfing_schema_probe_v1 import run_schema_probe

ROOT = Path(__file__).resolve().parents[2]
EDITS = ({'path':'/announcement','value':'Edit notice'},
         {'path':'/description','value':'Edit description'})


def execute_stages(coordinator, private_key, inventory, retain):
    """No outcome retry: a raised gate prevents every subsequent stage."""
    stages = [
        ('producers', coordinator.producer_stage, {}),
        ('checkpoint', coordinator.capture_checkpoint, {'private_key':private_key}),
        ('warm_edit', coordinator.warm_edit, {}),
        ('native_restore', coordinator.restore_native_editor, {'private_key':private_key}),
        ('native_edit', coordinator.restored_native_edit, {}),
        ('api_restore', coordinator.restore_api_inputs, {'private_key':private_key}),
        ('api_edit', coordinator.restored_api_edit, {}),
        ('request_comparison', coordinator.compare_retained_requests, {}),
        ('request_budget', coordinator.stop_and_check_request_budgets, {}),
        ('write_transport', coordinator.verify_write_transport, {}),
    ]
    completed = []
    for name, method, kwargs in stages:
        retain(name+'-before', inventory())
        method(**kwargs)
        retain(name+'-after', inventory())
        completed.append(name)
    if coordinator.phase != 'ordinary_write_transport_verified_parent_gates_pending':
        raise RuntimeError('Ordinary sequence did not reach its final comparison gate')
    return completed


def run_cycle(*, registration, build_report, directory, edit, node_binary='node'):
    if edit not in EDITS:raise ValueError('Edit is outside the frozen ordinary schedule')
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'shravaniparsi/mixed-interface-study':
        raise RuntimeError('Registered hosted CI only')
    directory=Path(directory).resolve();directory.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.umask(0o077)
    report={'status':'ordinary_cycle_in_progress','edit':edit,'scientific_cases_executed':0,
            'runtime_qualified':False,'stage':'initial_inventory'}
    coordinator=None
    try:
        if inspect_resources():raise RuntimeError('Fresh cycle requires absent prior fixture')
        report['stage']='provision'
        provision=directory/'provision'
        with (directory/'provision.stdout').open('wb') as stdout, (directory/'provision.stderr').open('wb') as stderr:
            subprocess.run([sys.executable,str(ROOT/'scripts/extension/provision_seatsurfing_ordinary_v1.py'),
                '--registration',str(Path(registration).resolve()),'--build-report',str(Path(build_report).resolve()),
                '--private',str(provision)],stdout=stdout,stderr=stderr,timeout=310,check=True)
        report['stage']='original_schema'
        schedule_path=ROOT/'manifests/catalog-seatsurfing-input-schedule-v1.json'
        schedule=json.loads(schedule_path.read_text())
        report['input_schedule_sha256']=hashlib.sha256(schedule_path.read_bytes()).hexdigest()
        schema=run_schema_probe(build_report,json.dumps(schedule['ordinary'],separators=(',',':')).encode(),directory/'schema.json')
        if schema.get('status')!='original_schema_observed' or schema['result']['accepted'] is not True:
            raise RuntimeError('Original schema did not accept the ordinary payload')
        coordinator=OrdinaryCoordinator(build_report=build_report,provision_report=provision/'provision-report.json',
            public_key=provision/'keys/public.pem',directory=directory/'coordinator',edit=edit,node_binary=node_binary)
        inventory_directory=directory/'inventories';inventory_directory.mkdir(mode=0o700)
        def inventory():
            owned=inspect_resources()
            if not {APP,PG}.issubset(owned):raise RuntimeError('Required fixture absent')
            return owned
        def retain(name, value):
            report['stage']=name
            write_private(inventory_directory/(name+'.json'),value)
        report['completed_stages']=execute_stages(coordinator,provision/'keys/private.pem',inventory,retain)
        final=inventory()
        if any(final[name]['State']['Running'] or final[name]['State'].get('Paused') for name in [APP,BROWSER]):
            raise RuntimeError('Ordinary writers remain active')
        report.update(status='ordinary_cycle_observed_pending_parent_retention_and_audit',
            namespace_inventory_scope='stage_boundaries_on_dedicated_runner_not_continuous_monitoring',
            schema_accepted=True,ordinary_branches=3)
    except Exception as error:
        report.update(status='ordinary_cycle_unavailable_no_retry',error_type=type(error).__name__)
        write_private(directory/'failure.json',{'stage':report['stage'],'type':type(error).__name__,'message':str(error)})
        raise
    finally:
        # Parent stops this entire process group before cleanup, including after
        # timeout; never replay a browser command or silently replace a fixture.
        if coordinator is not None:report['coordinator_phase']=coordinator.phase
        write_private(directory/'cycle-result.json',report)
    return report


def main():
    parser=argparse.ArgumentParser()
    for name in ['registration','build-report','private']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--edit-index',type=int,choices=[0,1],required=True)
    parser.add_argument('--node-binary',default='node')
    args=parser.parse_args()
    run_cycle(registration=args.registration,build_report=args.build_report,directory=args.private,
              edit=EDITS[args.edit_index],node_binary=args.node_binary)


if __name__=='__main__':main()
