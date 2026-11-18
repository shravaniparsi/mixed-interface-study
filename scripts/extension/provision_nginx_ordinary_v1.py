"""Provision two ordinary scenarios after a verified build, inside registered CI.

No CLI/dispatch or standalone qualification authority. Parent supplies the shared
job deadline, published registration, verified build and pinned browser tools.
Results remain runtime-unqualified until parent evidence gates are completed.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from nginx_browser_bridge_v1 import BrowserBridge
from nginx_coordinated_checkpoint_v1 import NginxCheckpoint, ROOT
from nginx_checkpoint_container_guard_v1 import LABEL, VALUE
from run_nginx_ordinary_scenario_v1 import OrdinaryScenario

BROWSER='mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac'
BROWSER_ID='sha256:fee853fafa59550d162cef52bca02d907694b44ebf6ef9fb075bcc0c65d8dedb'
NETWORK='study-nginx-isolated'
APP='study-nginx-ordinary'
CLIENT='study-nginx-browser'


def verify_topology(network, app, client, image_id, roots):
    if network.get('Internal') is not True or network.get('Driver')!='bridge':
        raise ValueError('Original isolated bridge required')
    if network.get('EnableIPv6') is not False or network['IPAM']['Config']!=[{'Subnet':'172.28.0.0/24','Gateway':'172.28.0.1'}]:
        raise ValueError('Unexpected registered subnet')
    if set(network['Containers'])!={app['Id'],client['Id']}:
        raise ValueError('Unexpected network participant')
    for item,expected_image,address in ((app,image_id,'172.28.0.2'),(client,BROWSER_ID,'172.28.0.3')):
        if item['Image']!=expected_image or item['Config'].get('Labels',{}).get(LABEL)!=VALUE:
            raise ValueError('Image/study identity mismatch')
        if item.get('State',{}).get('Running') is not True or item['State'].get('Paused') or item['State'].get('Restarting') or item['State'].get('Dead'):
            raise ValueError('Runtime participant is not stably running')
        host=item['HostConfig']
        if host.get('Privileged') or host.get('PortBindings') or host.get('PublishAllPorts') or host['RestartPolicy']['Name'] not in ('','no'):
            raise ValueError('Unregistered runtime privilege, port or restart policy')
        networks=item['NetworkSettings']['Networks']
        if set(networks)!={NETWORK} or networks[NETWORK]['IPAddress']!=address or networks[NETWORK]['NetworkID']!=network['Id']:
            raise ValueError('Runtime network/address mismatch')
    mounts={m['Destination']:m for m in app['Mounts']}
    for destination,source in roots.items():
        if destination not in mounts or mounts[destination]['Type']!='bind' or mounts[destination]['Source']!=str(source) or mounts[destination]['RW'] is not True:
            raise ValueError('Original state mount mismatch')
    return {'status':'isolated_runtime_topology_checked','application_ip':'172.28.0.2','browser_ip':'172.28.0.3','published_ports':False,'internal':True}


def provision_ordinary_scenarios(image_id, frontend, tools, evidence, deadline):
    evidence=Path(evidence).resolve(); evidence.mkdir(mode=0o700,exist_ok=False)
    frontend,tools=Path(frontend).resolve(),Path(tools).resolve()
    schedule=json.loads((ROOT/'manifests/catalog-nginx-input-schedule-v1.json').read_text())
    ordinary=next(c for c in schedule['cases'] if c['case']=='ordinary')
    if len(ordinary['independent_continuations'])!=2: raise ValueError('Two frozen ordinary scenarios required')
    def command(args,seconds=30):
        remaining=deadline-time.monotonic()
        if remaining<=0: raise TimeoutError('Original job deadline expired')
        return subprocess.check_output(['docker',*args],stderr=subprocess.PIPE,timeout=min(remaining,seconds))
    def inspect(kind,name):
        return json.loads(command([kind,'inspect',name]) if kind=='network' else command(['inspect','--type','container',name]))[0]
    def save(path,item):
        with path.open('x') as stream: json.dump(item,stream,indent=2);stream.write('\n')
    report={'status':'provisioning','scenarios':[],'scientific_inputs':0}
    try:
        browser_image=json.loads(command(['image','inspect',BROWSER]))[0]
        if browser_image['Id']!=BROWSER_ID or browser_image['Os']!='linux' or browser_image['Architecture']!='amd64':
            raise ValueError('Pinned browser image differs')
        for index,edit in enumerate(ordinary['independent_continuations'],1):
            current=evidence/f'scenario-{index}';current.mkdir(mode=0o700)
            data=current/'data';certificates=current/'certificates'
            data.mkdir();certificates.mkdir()
            roots={'/data':data,'/etc/letsencrypt':certificates}
            # Each scenario has a fresh database, key pair and actor. Never share
            # mutable state between the two independently warm checkpoints.
            secret='Study-Only-'+secrets.token_hex(18)+'!aA1'
            identity='study-admin@example.invalid'
            env=current/'application.env'
            env.write_text('\n'.join([f'PUID={os.getuid()}',f'PGID={os.getgid()}',
                'NODE_ENV=production','TZ=UTC','IP_RANGES_FETCH_ENABLED=false','DISABLE_IPV6=true',
                f'INITIAL_ADMIN_EMAIL={identity}',f'INITIAL_ADMIN_PASSWORD={secret}'])+'\n')
            env.chmod(0o600)
            bridge=None
            try:
                command(['network','create','--internal','--driver','bridge','--subnet','172.28.0.0/24','--gateway','172.28.0.1',NETWORK])
                command(['run','-d','--name',APP,'--label',f'{LABEL}={VALUE}','--restart','no',
                    '--network',NETWORK,'--ip','172.28.0.2','--env-file',str(env),
                    '-v',f'{data}:/data:rw','-v',f'{certificates}:/etc/letsencrypt:rw',
                    '-v',f'{ROOT}:{ROOT}:ro','-v',f'{current}:{current}:ro',image_id])
                # Browser runtime already contains its pinned binary. There is
                # no install/download/network fallback inside this network.
                command(['run','-d','--name',CLIENT,'--label',f'{LABEL}={VALUE}','--restart','no',
                    '--network',NETWORK,'--ip','172.28.0.3','--user',f'{os.getuid()}:{os.getgid()}',
                    '--shm-size','256m','-v',f'{ROOT}:{ROOT}:ro','-v',f'{frontend}:{frontend}:ro',
                    '-v',f'{tools}:{tools}:ro','-v',f'{current}:{current}:rw',
                    '--entrypoint','node',BROWSER,'-e','setInterval(() => {}, 1000)'])
                network,app,client=inspect('network',NETWORK),inspect('container',APP),inspect('container',CLIENT)
                save(current/'initial-network.json',network);save(current/'initial-application.json',app);save(current/'initial-browser.json',client)
                save(current/'topology.json',verify_topology(network,app,client,image_id,roots))
                bridge=BrowserBridge(['docker','exec','-i',CLIENT,'node',str(ROOT/'scripts/extension/nginx_ordinary_browser_worker_v1.mjs'),str(tools),str(frontend),str(current/'browser-evidence')],current/'browser-transport')
                bridge.await_ready(min(45,max(0,deadline-time.monotonic())))
                checkpoint=NginxCheckpoint(APP,image_id,data,certificates)
                scenario=OrdinaryScenario(checkpoint,bridge,current/'sequence',deadline)
                outcome=scenario.run(identity,secret,ordinary['producer_body'],edit)
                final_network,final_app,final_client=inspect('network',NETWORK),inspect('container',APP),inspect('container',CLIENT)
                save(current/'final-network.json',final_network);save(current/'final-application.json',final_app);save(current/'final-browser.json',final_client)
                verify_topology(final_network,final_app,final_client,image_id,roots)
                if final_app['Id']!=app['Id'] or final_client['Id']!=client['Id']:
                    raise ValueError('Scenario container replaced')
                report['scenarios'].append(outcome)
            finally:
                pending_error=sys.exc_info()[0] is not None
                worker_closed=True
                try:
                    if bridge is not None: bridge.close()
                except Exception:
                    worker_closed=False  # Container removal must still run.
                # Cleanup is independent of the exhausted experiment deadline.
                subprocess.run(['docker','rm','-f',CLIENT,APP],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25,check=False)
                subprocess.run(['docker','network','rm',NETWORK],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=False)
                cleanup={'containers_absent':False,'network_absent':False,'worker_closed':worker_closed}
                try:
                    names=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],stderr=subprocess.PIPE,timeout=15).decode().splitlines()
                    networks=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],stderr=subprocess.PIPE,timeout=15).decode().splitlines()
                    cleanup.update(containers_absent=APP not in names and CLIENT not in names,network_absent=NETWORK not in networks)
                except Exception as error:
                    cleanup['inspection_error_type']=type(error).__name__
                save(current/'cleanup.json',cleanup)
                if not all(cleanup.get(k) is True for k in ('containers_absent','network_absent','worker_closed')) and not pending_error:
                    raise RuntimeError('Dedicated runtime cleanup could not be verified')
        report['status']='two_ordinary_sequences_executed_root_layer_and_parent_gates_unqualified'
        return report
    except Exception as error:
        report.update(status='provisioning_or_scenario_failed_no_retry',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        save(evidence/'provisioning-result.json',report)
