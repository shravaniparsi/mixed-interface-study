"""Join ordinary scoring with runtime, isolation, worker and cleanup evidence.
Runs on private runner-local observations, before sanitized export.
"""
import hashlib,json,pathlib
from source_check import require
from shlink_build import DEPENDENCIES
ARCHIVE='dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8'
def score(base,system):
 base=pathlib.Path(base);out=base/'evidence'
 def load(path):
  require(path.is_file() and not path.is_symlink(),'regular_runtime_evidence',path=path.name)
  return json.loads(path.read_text())
 ordinary=load(out/'independent-score.json')
 require(ordinary['status']=='ordinary_controls_verified','ordinary_schedule_passed')
 require(ordinary['branches']=={'shlink':12,'zipline':24}[system],'all_branches')
 result=load(out/'result.json');require(result['status']=='controls_completed' and result['cleanup_complete'] is True,'application_and_cleanup_completed')
 if system=='zipline':
  before=load(out/'runtime-before.json');after=load(out/'runtime-after.json')
  require(before==after and before['status']=='verified_unchanged' and before['runtime_archive_sha256']==ARCHIVE and before['entries']>0,'immutable_zipline_runtime')
  infra=load(out/'infra-00-result.json');require(infra['status']=='completed' and infra['shutdown_verified'] is True,'postgres_shutdown')
  interfaces=load(out/'network-interfaces.json');routes=load(out/'network-routes.json')
  require(len(interfaces)==1 and interfaces[0]['ifname']=='lo' and routes==[],'isolated_loopback_namespace')
 else:
  require(system=='shlink','known_system');build=load(base/'build-evidence/result.json');deploy=load(base/'deployment.json')
  require(build['status']=='build_verified' and build['application_started'] is False,'separate_build_identity')
  require(deploy['containers']=={} and deploy['network_created'] is False and deploy['cleanup_errors']==[],'owned_resources_removed')
  require(not deploy.get('diagnostic_errors'),'complete_runtime_diagnostics')
  for role in ['backend-runtime','client-runtime','redis']:require(deploy['images'][role]==build['images'][role]['id'],'built_image_used',role=role)
  require(set(build['dependency_checked_paths'])==set(DEPENDENCIES) and all(build['dependency_checked_paths'].values()),'reviewed_installed_dependencies')
  key=hashlib.sha256(deploy['api_key'].encode()).hexdigest();require(key==result['api_key_sha256'],'deployed_actor_key')
  starts=[c for c in deploy['commands'] if c['label']=='backend-start']
  require(len(starts)==15 and all(c.get('exit_code')==0 for c in deploy['commands']),'complete_runtime_command_history')
  events=list(out.glob('event-probe-*.json'));workers=list(out.glob('worker-probe-*.json'))
  require(len(events)==len(workers)==len(starts),'probe_every_backend_start')
  for p in events:
   probe=load(p);require(probe['status']=='no_enabled_async_listeners' and probe['enabled_count']==0 and bool(probe['listeners']) and all(r['registered'] is False for r in probe['listeners']),'no_async_listeners')
  for p in workers:
   probe=load(p);require(probe['status']=='worker_spawn_configuration_verified' and len(probe['workers'])==1,'single_http_worker')
   require(probe['workers'][0]['initial_api_key_sha256']==key,'worker_actor_key')
  networks=[i for i,c in enumerate(deploy['commands']) if c['label']=='network-identity'];require(len(networks)==1,'network_observed')
  network=load(out/('docker-%04d.log'%networks[0]));require(len(network)==1 and network[0]['Internal'] is True and network[0]['Name']==deploy['network'],'internal_application_network')
 return dict(status='feasibility_system_verified',system=system,branches=ordinary['branches'],development_only=True,independent_evaluation_cases=0,scope='One system only; both systems and job time/cost ledger still required for study GO')
if __name__=='__main__':
 import sys
 result=score(sys.argv[1],sys.argv[2]);(pathlib.Path(sys.argv[1])/'evidence/runtime-score.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
