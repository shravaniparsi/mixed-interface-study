"""Synthetic sequencing/transport tests; no actual Docker/browser invocation."""
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import run_nginx_ordinary_scenario_v1 as m

class ScenarioTests(unittest.TestCase):
    def test_canonical_request_preserves_full_payload_and_actor(self):
        a={'request':{'method':'PUT','url':'http://172.28.0.2:81/api/nginx/access-lists/3','headers':{'Authorization':'Bearer original','Content-Type':'application/json'},'body':'{"name":"x","items":[]}'}}
        b={'request':dict(a['request'],path='/api/nginx/access-lists/3',body='{"items": [], "name": "x"}')}
        self.assertEqual(m.canonical_request(a),m.canonical_request(b))
        b['request']['body']='{"name":"x"}'
        self.assertNotEqual(m.canonical_request(a),m.canonical_request(b))
    def test_observation_timeout_never_resends_command(self):
        with tempfile.TemporaryDirectory() as root:
            bridge=Mock();bridge.send.side_effect=TimeoutError();bridge.pending={'id':'one'};bridge.failed=False
            bridge.observe_pending.side_effect=[TimeoutError(),{'done':True}]
            scenario=m.OrdinaryScenario(Mock(),bridge,Path(root)/'private',time.monotonic()+60)
            self.assertEqual(scenario.browser('quiescence'),{'done':True})
            self.assertEqual(bridge.send.call_count,1);self.assertEqual(bridge.observe_pending.call_count,2)
    def test_terminal_worker_failure_does_not_retry(self):
        with tempfile.TemporaryDirectory() as root:
            bridge=Mock();bridge.send.side_effect=RuntimeError('failure')
            scenario=m.OrdinaryScenario(Mock(),bridge,Path(root)/'private',time.monotonic()+60)
            with self.assertRaises(RuntimeError):scenario.browser('native_update',id=3,edit={})
            bridge.observe_pending.assert_not_called();self.assertEqual(bridge.send.call_count,1)
    def test_elapsed_parent_deadline_stops_before_send(self):
        with tempfile.TemporaryDirectory() as root:
            bridge=Mock();scenario=m.OrdinaryScenario(Mock(),bridge,Path(root)/'private',time.monotonic()-1)
            with self.assertRaises(TimeoutError):scenario.browser('quiescence')
            bridge.send.assert_not_called()
    def test_actual_persisted_fixture_values_required_for_all_three_producers(self):
        from copy import deepcopy
        import json
        import test_nginx_ordinary_database_comparison_v1 as fixture
        db=fixture.OrdinaryDatabaseComparisonTests().fixture()[0]
        for name,key in [('access_list','id'),('access_list_auth','access_list_id'),('access_list_client','access_list_id')]:
            table=next(t for t in db['tables'] if t['name']==name)
            original=json.loads(table['rows'][0]); names=[c[1][1] for c in table['columns']]
            table['rows']=[]
            for target in (1,2,3):
                row=deepcopy(original);row[names.index(key)]=['integer',str(target)];table['rows'].append(json.dumps(row))
        producer={'name':'Study Control','items':[{'username':'studycontrol','password':'Study-Only-Control-2026'}],'clients':[{'address':'192.0.2.10'}]}
        m.verify_ordinary_fixture(db,[1,2,3],1,producer)
        fixture.change(db,'access_list_auth','password','wrong',index=1)
        with self.assertRaisesRegex(ValueError,'persisted producer'):
            m.verify_ordinary_fixture(db,[1,2,3],1,producer)

    def test_frozen_branch_order_and_first_failure_stop(self):
        import test_nginx_ordinary_database_comparison_v1 as fixture
        db=fixture.OrdinaryDatabaseComparisonTests().fixture()[0]
        user=next(t for t in db['tables'] if t['name']=='user')
        user.update(fixture.table('user',[dict(id=1,email='study@example.invalid')]))
        snapshot={'database':db,'runtime':{'inventories':{}},'access':b'private'}
        for fail in (False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory() as root:
                checkpoint=Mock();scenario=m.OrdinaryScenario(checkpoint,Mock(),Path(root)/'private',time.monotonic()+60)
                scenario.settle_startup=Mock(return_value={'window':{}});scenario.snapshot=Mock(return_value=snapshot)
                scenario.schema=Mock();scenario.docker=Mock();scenario.save=Mock()
                updates=[];creates=[]
                request={'method':'PUT','path':'/api/nginx/access-lists/3','body':'{}','headers':{'authorization':'Bearer same','content-type':'application/json'}}
                def browser(operation,**kwargs):
                    if operation=='api_create':
                        creates.append(1);return {'json':{'id':1 if len(creates)==1 else 3},'request':request}
                    if operation=='native_create':return {'response':{'id':2}}
                    if operation=='read':return {'status':200,'json':{'id':kwargs['id']}}
                    if operation in ('native_update','api_update'):
                        updates.append(operation)
                        if fail:raise RuntimeError('native failed')
                        envelope={'request':request}
                        return {'result':envelope} if operation=='api_update' else envelope
                    return {}
                scenario.browser=Mock(side_effect=browser)
                with patch.object(m,'verify_ordinary_fixture'),patch.object(m,'compare_restart_state'),patch.object(m,'verify_ordinary_filesystem_delta'),patch.object(m,'compare_ordinary_databases'):
                    if fail:
                        with self.assertRaises(RuntimeError):scenario.run('study@example.invalid','private',{}, {})
                        self.assertEqual(updates,['native_update']);checkpoint.stop_and_restore.assert_not_called()
                    else:
                        result=scenario.run('study@example.invalid','private',{}, {})
                        self.assertEqual(updates,['native_update','native_update','api_update'])
                        self.assertEqual(checkpoint.capture.call_count,1);self.assertEqual(checkpoint.stop_and_restore.call_count,2)
                        self.assertEqual(result['scientific_inputs'],0)

if __name__=='__main__':unittest.main()
