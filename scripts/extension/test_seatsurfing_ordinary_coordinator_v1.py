"""Coordinator sequencing with real state comparators and mocked runtime edges."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import seatsurfing_ordinary_coordinator_v1 as module
from test_seatsurfing_ordinary_state_v1 import snapshot
from compare_seatsurfing_ordinary_state_v1 import epoch_microseconds


class CommandObservation(unittest.TestCase):
    def test_short_observation_timeout_does_not_resend(self):
        class Bridge:
            pending=True;failed=False;sent=0;observed=0
            def send(self,*args,**kwargs):self.sent+=1;raise TimeoutError()
            def observe_pending(self,**kwargs):self.observed+=1;self.pending=None;return {'retained':True}
        bridge=Bridge();self.assertEqual(module.observe_command(bridge,{}),{'retained':True})
        self.assertEqual((bridge.sent,bridge.observed),(1,1))
    def test_original_deadline_failure_stops_observing(self):
        class Bridge:
            pending=True;failed=False;sent=0
            def send(self,*args,**kwargs):self.sent+=1;raise TimeoutError()
            def observe_pending(self,**kwargs):self.failed=True;raise TimeoutError()
        bridge=Bridge()
        with self.assertRaisesRegex(TimeoutError,'deadline'):module.observe_command(bridge,{})
        self.assertEqual(bridge.sent,1)


class ProducerStage(unittest.TestCase):
    def run_stage(self, changed=False):
        temporary=tempfile.TemporaryDirectory(prefix='seatsurfing-coordinator-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);build=root/'build.json';build.write_text('{}')
        config=root/'login.json';config.write_text(json.dumps({'mode':'native_login','origin':'http://127.0.0.1:8080','login':{'organizationId':'org'}}))
        provision=root/'provision.json';provision.write_text(json.dumps({'status':'isolated_fixture_ready_browser_and_actor_unqualified','build_report_sha256':hashlib.sha256(build.read_bytes()).hexdigest(),'native_login_config':str(config),'node_tools':str(root/'tools')}))
        stage=module.OrdinaryCoordinator(build_report=build,provision_report=provision,public_key=root/'key',directory=root/'stage',edit={'path':'/description','value':'Edit description'})
        calls=[]
        class Bridge:
            ready=False;failed=False;artifact_directory=root/'worker'
            def await_ready(self,**kwargs):self.ready=True
            def send(self,command,**kwargs):
                calls.append(command)
                if command['operation']=='create':return {'createdId':'native'}
                if command['operation'] in ('session_storage','capture'):return {'storageSha256':'hash','network':{'events':[]}}
                return {}
        class Lifecycle:
            events=[]
            def __init__(self,*args):pass
            def pause(self):self.events.append({'action':'pause'})
            def resume(self):self.events.append({'action':'resume'})
        row={'organization_id':'org','name':'Study area','description':'Study description','announcement':'Study notice','max_concurrent_bookings':0,'tz':'','enabled':True,'map_scale':1,'map_type':'','bookable_days':'','blocked_from':None,'blocked_until':None,'map_data':None}
        before={'locations':[{'id':'sample','name':'Original'}],'sessions':[{'id':'session','user_id':'user','last_activity':'2026-11-18T00:00:00'}],'users':[{'id':'user'}]}
        states=[copy.deepcopy(before)]
        for identity,second in [('native',2),('api',5),(None,8)]:
            current=copy.deepcopy(states[-1])
            if identity:current['locations'].append({'id':identity,**row})
            current['sessions'][0]['last_activity']=f'2026-11-18T00:00:0{second}'
            states.append(current)
        if changed:states[2]['users'][0]['extra']='unintended'
        actor={'status':'actor_acquisition_and_identity_verified','continuity':{'sessionId':'session'}}
        api={'status':'api_worker_result_retained','result':{'result':{'outcome':'ordinary_create_http_observed','createdId':'api'}}}
        base=epoch_microseconds('2026-11-18T00:00:00Z')
        times=[(base+x*1000000)*1000 for x in [1,3,4,6,7,9]]
        with patch.object(module,'launch_native_browser',return_value=Bridge()),patch.object(module,'FixtureLifecycle',Lifecycle),patch.object(module,'capture_state',side_effect=[snapshot(s) for s in states]),patch.object(module,'verify_actor_state',return_value=actor) as verify,patch.object(module,'run_api_operation',return_value=api) as run_api,patch.object(module.time,'time_ns',side_effect=times):
            if changed:
                with self.assertRaisesRegex(ValueError,'unrelated table'):stage.producer_stage()
            else:
                result=stage.producer_stage();self.assertEqual(result['api_id'],'api')
            self.assertEqual(run_api.call_count,1)
            if not changed:self.assertEqual(verify.call_args.kwargs['expected_continuity'],actor['continuity'])
        return stage,calls
    def test_complete_stage_retains_original_worker_at_paused_warm_editor(self):
        stage,calls=self.run_stage()
        self.assertEqual(stage.phase,'warm_editor_paused')
        self.assertEqual([c['operation'] for c in calls],['login','session_storage','create','open','capture'])
        self.assertEqual(calls[3]['id'],'api');self.assertEqual(calls[3]['apiProducer']['createdId'],'api')
        self.assertFalse(stage.report['runtime_qualified'])
        self.assertTrue((stage.directory/'producer-pair.json').is_file())
        self.assertTrue((stage.directory/'producer-stage.json').is_file())
        with self.assertRaisesRegex(RuntimeError,'only once'):stage.producer_stage()
    def test_unrelated_mutation_stops_before_open_and_prevents_replay(self):
        stage,calls=self.run_stage(changed=True)
        self.assertEqual(stage.phase,'failed');self.assertEqual([c['operation'] for c in calls],['login','session_storage','create'])
        self.assertEqual(json.loads((stage.directory/'producer-stage.json').read_text())['status'],'producer_stage_unavailable')
        with self.assertRaises(RuntimeError):stage.producer_stage()




class CheckpointEvidence(unittest.TestCase):
    def fixture(self):
        now=module.time.time_ns()//1000000
        storage=b'{"cookies":[],"origins":[]}'
        network=b'[]'
        state={'status':'paused_comparison_state_captured','state':{'fixture':True}}
        actor={'status':'actor_acquisition_and_identity_verified','database_acquisition_provenance_verified':True,
               'continuity':{'accessTokenSha256':hashlib.sha256(b'access').hexdigest(),'refreshTokenSha256':hashlib.sha256(b'refresh').hexdigest()}}
        capture={'nativeStorageCapture':True,'browserRequestsSettled':True,'storageSha256':hashlib.sha256(storage).hexdigest(),'storageBytes':storage.decode(),
                 'network':{'events':[],'traceSha256':hashlib.sha256(network).hexdigest(),'pendingRequests':0,'pendingCaptures':0,'observedAt':now},
                 'diagnostics':{'sessionStorage':{},'cacheNames':[],'accessToken':'access','refreshToken':'refresh','expiry':now+600000}}
        return {'capture':capture,'actor':actor,'state':state},storage,network,state,{'state':'paused'}
    def test_evidence_bound_proof_preserves_background_task_uncertainty(self):
        result=module.build_checkpoint_observation(*self.fixture())
        self.assertTrue(result['application_operations_settled'])
        self.assertFalse(result['pending_application_tasks_proven_absent'])
        self.assertFalse(result['warm_restore_equivalence_established'])
    def test_missing_actor_or_changed_storage_rejected(self):
        data=list(self.fixture());data[0]['actor']['database_acquisition_provenance_verified']=False
        with self.assertRaisesRegex(ValueError,'actor'):module.build_checkpoint_observation(*data)
        data=list(self.fixture());data[1]=b'changed'
        with self.assertRaisesRegex(ValueError,'storage'):module.build_checkpoint_observation(*data)
    def test_pending_capture_and_stale_observation_rejected(self):
        data=list(self.fixture());data[0]['capture']['network']['pendingCaptures']=1
        with self.assertRaisesRegex(ValueError,'Unsettled'):module.build_checkpoint_observation(*data)
        data=list(self.fixture());data[0]['capture']['network']['observedAt']-=61000
        with self.assertRaisesRegex(ValueError,'sixty'):module.build_checkpoint_observation(*data)
    def test_changed_token_and_unmapped_storage_rejected(self):
        data=list(self.fixture());data[0]['capture']['diagnostics']['accessToken']='other'
        with self.assertRaisesRegex(ValueError,'credential'):module.build_checkpoint_observation(*data)
        data=list(self.fixture());data[0]['capture']['diagnostics']['cacheNames']=['unmapped']
        with self.assertRaisesRegex(ValueError,'Unmapped'):module.build_checkpoint_observation(*data)
    def test_changed_full_state_or_running_process_rejected(self):
        data=list(self.fixture());data[3]={'different':True}
        with self.assertRaisesRegex(ValueError,'paused complete'):module.build_checkpoint_observation(*data)
        data=list(self.fixture());data[4]={'state':'running'}
        with self.assertRaisesRegex(ValueError,'paused complete'):module.build_checkpoint_observation(*data)


class WarmEdit(unittest.TestCase):
    def test_warm_edit_requires_joint_checkpoint_and_keeps_same_worker(self):
        # Reuse the connected producer fixture; runtime boundaries remain mocked.
        helper=ProducerStage();self.addCleanup(helper.doCleanups)
        stage,_=helper.run_stage()
        with self.assertRaisesRegex(RuntimeError,'checkpoint'):stage.warm_edit()
        stage.phase='checkpoint_captured'
        after=copy.deepcopy(stage.warm['state'])
        tables={}
        for table in after['row_data']:
            rows=[json.loads(raw) for raw in table['rows']]
            if table['relation_name']=='locations':
                next(row for row in rows if row['id']=='api')['description']='Edit description'
            if table['relation_name']=='sessions':rows[0]['last_activity']='2026-11-18T00:00:11'
            tables[table['relation_name']]=rows
        after=snapshot(tables)
        base=epoch_microseconds('2026-11-18T00:00:00Z')
        original=stage.bridge
        with patch.object(module,'observe_command',return_value={'network':{'events':[]}}) as command,patch.object(module,'capture_state',return_value=after),patch.object(stage,'actor',return_value=stage.warm['actor']),patch.object(module.time,'time_ns',side_effect=[(base+10000000)*1000,(base+12000000)*1000]):
            result=stage.warm_edit()
        self.assertIs(stage.bridge,original);self.assertEqual(command.call_count,1)
        self.assertEqual(command.call_args.args[1],{'requestId':'edit','operation':'edit','edit':stage.edit})
        self.assertEqual(stage.phase,'warm_edit_paused');self.assertEqual(result['state_comparison']['status'],'ordinary_operation_state_matches')
        with self.assertRaises(RuntimeError):stage.warm_edit()




class RestoredNativeEdit(unittest.TestCase):
    def test_restored_edit_compares_against_original_warm_baseline(self):
        helper=ProducerStage();self.addCleanup(helper.doCleanups)
        stage,_=helper.run_stage();stage.restored_native=stage.warm;stage.phase='restored_native_editor_paused'
        tables={table['relation_name']:[json.loads(raw) for raw in table['rows']] for table in stage.warm['state']['row_data']}
        next(row for row in tables['locations'] if row['id']=='api')['description']='Edit description'
        tables['sessions'][0]['last_activity']='2026-11-18T00:00:11'
        after=snapshot(tables);base=epoch_microseconds('2026-11-18T00:00:00Z')
        with patch.object(module,'observe_command',return_value={'network':{'events':[]}}) as command,patch.object(module,'capture_state',return_value=after),patch.object(stage,'actor',return_value=stage.warm['actor']),patch.object(module.time,'time_ns',side_effect=[(base+10000000)*1000,(base+12000000)*1000]):
            result=stage.restored_native_edit()
        self.assertEqual(command.call_count,1);self.assertEqual(stage.phase,'restored_native_edit_paused')
        self.assertEqual(result['state_comparison']['target_change']['before'],'Study description')
        with self.assertRaises(RuntimeError):stage.restored_native_edit()


class JointCheckpointIntegration(unittest.TestCase):
    def test_dump_baseline_must_equal_full_warm_state(self):
        import subprocess
        for mismatch in [False,True]:
            with self.subTest(mismatch=mismatch):
                helper=ProducerStage();self.addCleanup(helper.doCleanups)
                stage,_=helper.run_stage()
                private_key=stage.directory/'private.pem';private_key.write_bytes(b'private-fixture')
                stage.provision['private_key_sha256']=hashlib.sha256(private_key.read_bytes()).hexdigest()
                stage.warm['storage'].parent.mkdir(parents=True,exist_ok=True)
                stage.warm['storage'].write_bytes(b'{}')
                (stage.bridge.artifact_directory/'browser-network.json').write_bytes(b'[]')
                def execute(argv,**kwargs):
                    checkpoint=Path(argv[argv.index('--checkpoint')+1]);(checkpoint/'database').mkdir(parents=True)
                    raw=b'{"synthetic_manifest":true}';(checkpoint/'manifest.json').write_bytes(raw)
                    baseline={'state':{'different':True} if mismatch else stage.warm['state']['state']}
                    (checkpoint/'database/baseline.json').write_text(json.dumps(baseline))
                    Path(argv[argv.index('--output')+1]).write_text(json.dumps({'status':'joint_checkpoint_captured_runtime_unqualified','manifest_sha256':hashlib.sha256(raw).hexdigest()}))
                    return subprocess.CompletedProcess(argv,0,b'',b'')
                with patch.object(stage.lifecycle,'_inspect',return_value={'state':'paused'},create=True),patch.object(module,'capture_state',return_value=stage.warm['state']),patch.object(module,'build_checkpoint_observation',return_value={}),patch.object(module.subprocess,'run',side_effect=execute) as run:
                    if mismatch:
                        with self.assertRaisesRegex(RuntimeError,'baseline differs'):stage.capture_checkpoint(private_key=private_key)
                    else:stage.capture_checkpoint(private_key=private_key)
                self.assertEqual(run.call_count,1)
                self.assertEqual(stage.phase,'failed' if mismatch else 'checkpoint_captured')
                with self.assertRaises(RuntimeError):stage.capture_checkpoint(private_key=private_key)




class RestoredNativeSequence(unittest.TestCase):
    def test_verified_restore_precedes_replacement_and_failed_restore_prevents_start(self):
        import subprocess
        from unittest.mock import Mock
        for branch,failure in [('native',False),('native',True),('api',False),('api',True)]:
            with self.subTest(branch=branch,failure=failure):
                helper=ProducerStage();self.addCleanup(helper.doCleanups)
                stage,_=helper.run_stage()
                stage.phase='warm_edit_paused' if branch=='native' else 'restored_native_edit_paused'
                restore_method=stage.restore_native_editor if branch=='native' else stage.restore_api_inputs
                stage.checkpoint=stage.directory/'checkpoint';stage.checkpoint.mkdir()
                storage=stage.checkpoint/'storage.json';storage.write_text(json.dumps({'origins':[{'localStorage':[{'name':'accessToken','value':'token'},{'name':'refreshToken','value':'refresh'}]}]}))
                digest=hashlib.sha256(storage.read_bytes()).hexdigest();stage.warm['capture']['storageSha256']=digest
                stage.checkpoint_result={'manifest_sha256':'manifest'}
                write=module.write_private
                write(stage.directory/'checkpoint-observation.json',{'storage_sha256':digest})
                stage.bridge.artifact_directory.mkdir(parents=True,exist_ok=True)
                write(stage.bridge.artifact_directory/'final-network.json',{'failure':None,'pendingIds':[],'pendingCaptures':0,'events':[]})
                stage.bridge.close=Mock(return_value=None)
                identity={'container_ids':['app','pg','old'],'state':'stopped'}
                stage.lifecycle.stop=Mock(side_effect=lambda close:(close() or {'after':identity}))
                stage.lifecycle._inspect=Mock(return_value=identity)
                stage.lifecycle.processes=(('old-app',),('same-pg',),('old-browser',))
                stage.warm['opened']={'readback':{'id':'api'},'loader':{'materialization':{'fixture':True}}}
                calls=[];operations=[]
                def command(argv):
                    calls.append(argv)
                    if argv[1]=='inspect':return json.dumps([{'Id':'app','State':{'Running':True,'Restarting':False,'Health':{'Status':'healthy'}}}]).encode()
                    return b''
                def restore(argv,**kwargs):
                    calls.append(['joint','restore'])
                    if not failure:Path(argv[argv.index('--output')+1]).write_text(json.dumps({'status':'database_restored_browser_context_not_started','storage_path':str(storage),'storage_sha256':digest}))
                    return subprocess.CompletedProcess(argv,1 if failure else 0,b'',b'')
                class Browser:
                    ready=False;failed=False;artifact_directory=stage.directory/'new-worker'
                    def await_ready(self,**kwargs):self.ready=True
                    def send(self,command,**kwargs):
                        operations.append(command['operation'])
                        if command['operation']=='open':return stage.warm['opened']
                        return {'storageSha256':digest,'network':{'events':[]}}
                class Lifecycle:
                    ids=('app','pg','new');processes=(('new-app',),('same-pg',),('new-browser',));events=[]
                    def __init__(self,*args):pass
                    def pause(self):pass
                tables={table['relation_name']:[json.loads(raw) for raw in table['rows']] for table in stage.warm['state']['row_data']}
                tables['sessions'][0]['last_activity']='2026-11-18T00:00:10'
                state=snapshot(tables);base=epoch_microseconds('2026-11-18T00:00:00Z')
                with patch.object(module,'run_api_operation',return_value={'status':'api_worker_result_retained','result':{'result':{'outcome':'source_inputs_loaded','materialization':{'fixture':True}}}}),patch.object(module,'verify_api_actor_response',return_value={'status':'synthetic_match'}),patch.object(module.subprocess,'run',side_effect=restore),patch.object(module,'lifecycle_command',side_effect=command),patch.object(module,'launch_native_browser',return_value=Browser()) as launch,patch.object(module,'FixtureLifecycle',Lifecycle),patch.object(stage,'snapshot',return_value=state),patch.object(stage,'actor',return_value=stage.warm['actor']),patch.object(module.time,'time_ns',side_effect=[(base+9000000)*1000,(base+11000000)*1000]):
                    if failure:
                        with self.assertRaisesRegex(RuntimeError,'restore unavailable'):restore_method(private_key=stage.directory/'key')
                    else:restore_method(private_key=stage.directory/'key')
                self.assertEqual(calls[0],['joint','restore'])
                if failure:
                    self.assertEqual(calls,[['joint','restore']]);self.assertEqual(launch.call_count,0);self.assertEqual(stage.phase,'failed')
                else:
                    self.assertEqual(calls[1:3],[['docker','rm',module.BROWSER],['docker','start',module.APP]])
                    self.assertEqual(operations,['open','capture'] if branch=='native' else []);self.assertEqual(stage.phase,'restored_native_editor_paused' if branch=='native' else 'restored_api_inputs_paused')
                with self.assertRaises(RuntimeError):restore_method(private_key=stage.directory/'key')




class IndependentApiActor(unittest.TestCase):
    def fixture(self):
        continuity={'userId':'user','email':'example','organizationId':'org','accountType':0,
            'permissions':{'locations':30},'requirePassword':True,'passwordPending':False,
            'roleIds':['role'],'accessTokenSha256':hashlib.sha256(b'token').hexdigest()}
        value={key:val for key,val in continuity.items() if key not in ['userId','accessTokenSha256']}
        value.update(id='user',organization={'id':'org'})
        raw=json.dumps(value)
        row={'url':'http://127.0.0.1:8080/user/me','method':'GET','outcome':'json_observed','status':200,
            'dispatchedAt':1,'completedAt':2,'headers':{'authorization':'Bearer token'},
            'responseBody':raw,'bodySha256':hashlib.sha256(raw.encode()).hexdigest()}
        return {'outcome':'source_inputs_loaded','acquisition':'independent_api_gets','envelopes':[row],'originalResponses':{'self':value}},continuity
    def test_independent_self_keeps_api_provenance(self):
        result=module.verify_api_actor_response(*self.fixture())
        self.assertFalse(result['native_trace_fabricated']);self.assertFalse(result['runtime_qualified'])
    def test_changed_token_missing_response_and_hash_fail(self):
        for change in ['token','missing','hash']:
            loaded,continuity=self.fixture()
            if change=='token':loaded['envelopes'][0]['headers']['authorization']='Bearer other'
            if change=='missing':loaded['envelopes']=[]
            if change=='hash':loaded['envelopes'][0]['bodySha256']='wrong'
            with self.assertRaises(ValueError):module.verify_api_actor_response(loaded,continuity)
    def test_current_permission_changes_fail_even_with_valid_body_hash(self):
        loaded,continuity=self.fixture();value=loaded['originalResponses']['self'];value['permissions']={'locations':10}
        raw=json.dumps(value);loaded['envelopes'][0].update(responseBody=raw,bodySha256=hashlib.sha256(raw.encode()).hexdigest())
        with self.assertRaisesRegex(ValueError,'permissions'):module.verify_api_actor_response(loaded,continuity)


class RestoredApiEdit(unittest.TestCase):
    def test_api_continuation_uses_fresh_loading_and_original_warm_state(self):
        helper=ProducerStage();self.addCleanup(helper.doCleanups)
        stage,_=helper.run_stage();stage.phase='restored_api_inputs_paused'
        stage.warm['opened']={'loader':{'materialization':{'fixture':True}}}
        stage.restored_api={'storage':stage.warm['storage'],'storage_sha256':'hash'}
        loaded={'materialization':{'fixture':True}}
        observed={'status':'api_worker_result_retained','result':{'result':{'outcome':'continuation_observed','loaded':loaded,'execution':{'outcome':'all_http_accepted'}}}}
        tables={table['relation_name']:[json.loads(raw) for raw in table['rows']] for table in stage.warm['state']['row_data']}
        next(row for row in tables['locations'] if row['id']=='api')['description']='Edit description'
        tables['sessions'][0]['last_activity']='2026-11-18T00:00:11'
        base=epoch_microseconds('2026-11-18T00:00:00Z')
        with patch.object(module,'run_api_operation',return_value=observed) as run,patch.object(module,'capture_state',return_value=snapshot(tables)),patch.object(module,'verify_api_actor_response',return_value={'status':'synthetic_match'}),patch.object(stage,'actor',return_value=stage.warm['actor']),patch.object(module.time,'time_ns',side_effect=[(base+10000000)*1000,(base+12000000)*1000]):
            result=stage.restored_api_edit()
        self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.kwargs['operation'],'ordinary_continue')
        self.assertEqual(result['native_trace_source'],'original_warm_capture')
        self.assertEqual(stage.phase,'restored_api_edit_paused')
        self.assertEqual(result['state_comparison']['target_change']['before'],'Study description')
        with self.assertRaises(RuntimeError):stage.restored_api_edit()




class RetainedRequestIntegration(unittest.TestCase):
    def test_hash_binding_and_artifact_mutation_rejection(self):
        import subprocess
        for changed in [None,'artifact','result_hash']:
            with self.subTest(changed=changed):
                helper=ProducerStage();self.addCleanup(helper.doCleanups)
                stage,_=helper.run_stage();stage.phase='restored_api_edit_paused'
                stage.warm_result={'native':{'fixture':'warm'}};stage.native_result={'native':{'fixture':'restored'}};stage.api_result={'api':{'fixture':'api'}}
                paths={'warm':stage.directory/'native/worker/results/edit-result.json','native':stage.directory/'restored-native/worker/results/edit-result.json','api':stage.directory/'api-continuation/worker/result.json','storage':stage.warm['storage']}
                objects={'warm':stage.warm_result['native'],'native':stage.native_result['native'],'api':{'result':stage.api_result['api']},'storage':{'fixture':'storage'}}
                for name,path in paths.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(objects[name]))
                stage.warm['capture']['storageSha256']=hashlib.sha256(paths['storage'].read_bytes()).hexdigest()
                if changed=='artifact':paths['warm'].write_text('{}')
                def execute(argv,**kwargs):
                    hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}
                    if changed=='result_hash':hashes['warm']='wrong'
                    Path(argv[-1]).write_text(json.dumps({'status':'both_native_write_plans_match_independent_api','inputHashes':hashes,'apiTransportBound':True,'apiTransportCaptureComplete':False}))
                    return subprocess.CompletedProcess(argv,0,b'',b'')
                with patch.object(module.subprocess,'run',side_effect=execute) as run:
                    if changed:
                        with self.assertRaises(ValueError):stage.compare_retained_requests()
                    else:stage.compare_retained_requests()
                self.assertEqual(run.call_count,0 if changed=='artifact' else 1)
                self.assertEqual(stage.phase,'failed' if changed else 'ordinary_comparisons_complete_transport_unqualified')
                with self.assertRaises(RuntimeError):stage.compare_retained_requests()




class FinalRateBudget(unittest.TestCase):
    def test_complete_process_traffic_counts_and_over_budget_refusal(self):
        from unittest.mock import Mock
        from test_seatsurfing_request_budget_v1 import RequestBudget
        for over in [False,True]:
            with self.subTest(over=over):
                helper=ProducerStage();self.addCleanup(helper.doCleanups)
                stage,_=helper.run_stage();stage.phase='ordinary_comparisons_complete_transport_unqualified'
                stage.bridge.close=Mock(return_value=None)
                stopped={'container_ids':['app','pg','browser'],'state':'stopped'}
                stage.lifecycle.stop=Mock(return_value={'after':stopped});stage.lifecycle._inspect=Mock(return_value=stopped)
                stage.warm['actor']['continuity']['accessTokenSha256']=hashlib.sha256(b'token').hexdigest()
                trace={'failure':None,'pendingIds':[],'pendingCaptures':0,'events':[]}
                for folder in ['native','restored-native','restored-api']:
                    path=stage.directory/folder/'worker/results/final-network.json';path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(RequestBudget().fixture(200)['native_trace'] if over and folder=='native' else trace))
                get={'method':'GET','url':'http://127.0.0.1:8080/user/me','headers':{'authorization':'Bearer token'},'status':200,'dispatchedAt':1,'completedAt':2}
                producer={'envelope':{'request':{'url':'http://127.0.0.1:8080/location/','headers':{'authorization':'Bearer token'}},'response':{'status':201},'dispatchedAt':1,'completedAt':2}}
                loaded={'envelopes':[get]};continued={'loaded':loaded,'execution':{'envelopes':[get]}}
                stage.restored_api={'loaded':loaded};stage.api_result={'api':continued}
                for folder,operation,result in [('api-create','ordinary_create',producer),('api-startup-load','independent_load',loaded),('api-continuation','ordinary_continue',continued)]:
                    path=stage.directory/folder/'worker/result.json';path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps({'status':'api_operation_observed','operation':operation,'result':result}))
                app={'Id':'app','Config':{'Env':['RATE_LIMIT=250','RATE_LIMIT_PERIOD=1-M']}}
                with patch.object(module,'lifecycle_command',return_value=json.dumps([app]).encode()):
                    if over:
                        with self.assertRaisesRegex(ValueError,'ceiling'):stage.stop_and_check_request_budgets()
                    else:
                        result=stage.stop_and_check_request_budgets()
                        self.assertEqual(result['budgets']['warm']['whole_process_authenticated_requests'],1)
                        self.assertEqual(result['budgets']['api']['whole_process_authenticated_requests'],3)
                self.assertEqual(stage.phase,'failed' if over else 'ordinary_fixture_stopped_rate_budget_verified')
                with self.assertRaises(RuntimeError):stage.stop_and_check_request_budgets()




class TransportGateIntegration(unittest.TestCase):
    def test_calibration_and_verifier_input_hashes_are_required(self):
        import subprocess
        from unittest.mock import Mock
        for changed in [None,'calibration','result']:
            with self.subTest(changed=changed):
                helper=ProducerStage();self.addCleanup(helper.doCleanups)
                stage,_=helper.run_stage();stage.phase='ordinary_fixture_stopped_rate_budget_verified'
                stage.lifecycle._inspect=Mock(return_value={'container_ids':['app','pg','browser']})
                calibration=stage.directory/'calibration.json';calibration.write_text('{"synthetic":true}')
                stage.provision.update(transport_calibration_path=str(calibration),transport_calibration_sha256=hashlib.sha256(calibration.read_bytes()).hexdigest())
                if changed=='calibration':calibration.write_text('{}')
                stage.request_budgets={};stage.request_comparisons={}
                for relative in ['native/worker/results/native-create.json','api-create/worker/result.json','api-continuation/worker/result.json']:
                    path=stage.directory/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
                app={'Id':'app','Config':{'Env':['CORS_ORIGINS=','PUBLIC_SCHEME=http','RATE_LIMIT=250','RATE_LIMIT_PERIOD=1-M']}}
                def execute(argv,**kwargs):
                    digest=hashlib.sha256(Path(argv[-2]).read_bytes()).hexdigest()
                    Path(argv[-1]).write_text(json.dumps({'status':'write_transport_evidence_verified','inputSha256':'wrong' if changed=='result' else digest,'result':{'status':'observed_write_transport_checks_pass'}}))
                    return subprocess.CompletedProcess(argv,0,b'',b'')
                with patch.object(module,'lifecycle_command',return_value=json.dumps([app]).encode()),patch.object(module.subprocess,'run',side_effect=execute) as run:
                    if changed:
                        with self.assertRaises(ValueError):stage.verify_write_transport()
                    else:stage.verify_write_transport()
                self.assertEqual(run.call_count,0 if changed=='calibration' else 1)
                self.assertEqual(stage.phase,'failed' if changed else 'ordinary_write_transport_verified_parent_gates_pending')
                with self.assertRaises(RuntimeError):stage.verify_write_transport()


if __name__=='__main__':unittest.main()
