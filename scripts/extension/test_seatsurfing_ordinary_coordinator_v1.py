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


if __name__=='__main__':unittest.main()
