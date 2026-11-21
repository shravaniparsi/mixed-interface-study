import copy,hashlib,json,pathlib,tempfile,unittest
from runtime_score import score,ARCHIVE,DEPENDENCIES
class RuntimeGate(unittest.TestCase):
 def fixture(self,system):
  docs={'evidence/independent-score.json':dict(status='ordinary_controls_verified',branches=12 if system=='shlink' else 24),'evidence/result.json':dict(status='controls_completed',cleanup_complete=True)}
  if system=='zipline':
   for side in ['before','after']:docs['evidence/runtime-'+side+'.json']=dict(status='verified_unchanged',runtime_archive_sha256=ARCHIVE,entries=64235)
   docs['evidence/infra-00-result.json']=dict(status='completed',shutdown_verified=True);docs['evidence/network-interfaces.json']=[{'ifname':'lo'}];docs['evidence/network-routes.json']=[]
  else:
   key='synthetic-runtime-gate-credential';fingerprint=hashlib.sha256(key.encode()).hexdigest();docs['evidence/result.json']['api_key_sha256']=fingerprint
   images={role:'sha256:fixture-'+role for role in ['backend-runtime','client-runtime','redis']}
   docs['build-evidence/result.json']=dict(status='build_verified',application_started=False,images={k:{'id':v} for k,v in images.items()},dependency_checked_paths={k:['reviewed/path.php'] for k in DEPENDENCIES})
   docs['deployment.json']=dict(containers={},network_created=False,cleanup_errors=[],images=images,api_key=key,network='fixture-network',commands=[dict(label='network-identity',exit_code=0)]+[dict(label='backend-start',exit_code=0) for _ in range(15)])
   docs['evidence/docker-0000.log']=[dict(Name='fixture-network',Internal=True)]
   for i in range(15):
    docs['evidence/event-probe-'+str(i)+'.json']=dict(status='no_enabled_async_listeners',enabled_count=0,listeners=[dict(registered=False)])
    docs['evidence/worker-probe-'+str(i)+'.json']=dict(status='worker_spawn_configuration_verified',workers=[dict(initial_api_key_sha256=fingerprint)])
  return docs
 def execute(self,system,docs):
  with tempfile.TemporaryDirectory() as tmp:
   for name,value in docs.items():
    p=pathlib.Path(tmp)/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(value))
   return score(tmp,system)
 def test_complete_fixture_for_both_systems(self):
  for system in ['zipline','shlink']:self.assertEqual(self.execute(system,self.fixture(system))['status'],'feasibility_system_verified')
 def test_ordinary_success_does_not_override_runtime_failures(self):
  for fault in ['missing_runtime','runtime_changed','postgres_live','external_route','external_interface','wrong_image','missing_probe','enabled_listener','wrong_worker_key','external_network','cleanup_failed','incomplete_schedule']:
   system='zipline' if fault in ['missing_runtime','runtime_changed','postgres_live','external_route','external_interface'] else 'shlink';docs=self.fixture(system)
   if fault=='missing_runtime':del docs['evidence/runtime-after.json']
   elif fault=='runtime_changed':docs['evidence/runtime-after.json']['entries']=1
   elif fault=='postgres_live':docs['evidence/infra-00-result.json']['shutdown_verified']=False
   elif fault=='external_route':docs['evidence/network-routes.json']=[{'dst':'default'}]
   elif fault=='external_interface':docs['evidence/network-interfaces.json'].append({'ifname':'eth0'})
   elif fault=='wrong_image':docs['deployment.json']['images']=dict(docs['deployment.json']['images'],redis='unexpected-image')
   elif fault=='missing_probe':del docs['evidence/event-probe-0.json']
   elif fault=='enabled_listener':docs['evidence/event-probe-0.json']['listeners'][0]['registered']=True
   elif fault=='wrong_worker_key':docs['evidence/worker-probe-0.json']['workers'][0]['initial_api_key_sha256']='wrong'
   elif fault=='external_network':docs['evidence/docker-0000.log'][0]['Internal']=False
   elif fault=='cleanup_failed':docs['deployment.json']['containers']={'backend':'still-running'}
   elif fault=='incomplete_schedule':docs['evidence/independent-score.json']['branches']=11
   with self.subTest(fault=fault),self.assertRaises(ValueError):self.execute(system,docs)
if __name__=='__main__':unittest.main()
