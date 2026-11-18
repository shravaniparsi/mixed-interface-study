"""Synthetic full-row comparison and current build-report contract tests."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import capture_seatsurfing_comparison_state_v1 as capture
from compare_seatsurfing_ordinary_state_v1 import compare_ordinary_state,epoch_microseconds
import seatsurfing_postgres_checkpoint_v2 as checkpoint


def snapshot(tables):
    state={'tables':[],'sequences':[]}
    for key in ['schema','roles','memberships','role_database_settings','database_configuration','tablespaces','settings']:
        state[key+'_sha256']='a'*64
    data=[]
    for name,values in sorted(tables.items()):
        rows=[json.dumps(v,separators=(',',':')) for v in values]
        raw=('\n'.join(sorted(rows))+ ('\n' if rows else '')).encode()
        state['tables'].append({'schema_name':'public','relation_name':name,'relkind':'r','rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest()})
        data.append({'schema_name':'public','relation_name':name,'rows':rows})
    return {'status':'paused_comparison_state_captured','state':state,'row_data':data,'field_exclusions':[]}


class OrdinaryComparison(unittest.TestCase):
    def setUp(self):
        self.tables={'sessions':[{'id':'session','user_id':'user','expires_at':'2026-12-01T00:00:00','last_activity':'2026-11-18T12:00:00'}],
                     'locations':[{'id':'location','name':'Study area','description':'Study description','announcement':'Study notice','map_data':None},{'id':'sample','name':'Original sample'}],
                     'users':[{'id':'user','disabled':False,'last_activity_at_utc':'2026-11-18T11:59:00'}]}
        self.after=copy.deepcopy(self.tables)
        self.after['sessions'][0]['last_activity']='2026-11-18T12:00:02.123456'
        self.kwargs={'session_id':'session','location_id':'location','window_start_us':epoch_microseconds('2026-11-18T12:00:01Z'),'window_end_us':epoch_microseconds('2026-11-18T12:00:03Z')}
    def compare(self,edit=None):return compare_ordinary_state(snapshot(self.tables),snapshot(self.after),**self.kwargs,edit=edit)
    def test_restart_load_preserves_everything_except_bounded_session_activity(self):
        result=self.compare();self.assertEqual(result['status'],'ordinary_operation_state_matches');self.assertFalse(result['runtime_qualified']);self.assertEqual(result['session_activity']['before'],self.tables['sessions'][0]['last_activity'])
    def test_exact_ordinary_edit_with_retained_audit_delta(self):
        self.after['locations'][0]['description']='Edit description'
        result=self.compare({'path':'/description','value':'Edit description'});self.assertEqual(result['target_change']['before'],'Study description')
    def test_unrelated_target_field_change_rejected(self):
        self.after['locations'][0]['name']='changed'
        with self.assertRaisesRegex(ValueError,'outside'):self.compare()
    def test_sample_record_change_rejected(self):
        self.after['locations'][1]['name']='changed'
        with self.assertRaisesRegex(ValueError,'Another location'):self.compare()
    def test_user_activity_not_covered_by_session_rule(self):
        self.after['users'][0]['last_activity_at_utc']='2026-11-18T12:00:02'
        with self.assertRaisesRegex(ValueError,'Unrelated table'):self.compare()
    def test_session_lifetime_change_rejected(self):
        self.after['sessions'][0]['expires_at']='2027-01-01T00:00:00'
        with self.assertRaisesRegex(ValueError,'lifetime'):self.compare()
    def test_nonmonotonic_or_out_of_window_activity_rejected(self):
        for value in ['2026-11-18T11:59:59','2026-11-18T12:00:04']:
            self.after['sessions'][0]['last_activity']=value
            with self.assertRaisesRegex(ValueError,'monotonic'):self.compare()
    def test_metadata_and_raw_row_integrity_are_required(self):
        left,right=snapshot(self.tables),snapshot(self.after)
        right['state']['sequences']=[{'unexpected':True}]
        with self.assertRaisesRegex(ValueError,'configuration'):compare_ordinary_state(left,right,**self.kwargs)
        right=snapshot(self.after);right['row_data'][0]['rows'][0]+=' '
        with self.assertRaisesRegex(ValueError,'fingerprint'):compare_ordinary_state(left,right,**self.kwargs)
        right=snapshot(self.after);del right['state']['roles_sha256']
        with self.assertRaisesRegex(ValueError,'Incomplete'):compare_ordinary_state(left,right,**self.kwargs)
    def test_unrelated_duplicate_row_cannot_disappear(self):
        self.tables['users'].append(copy.deepcopy(self.tables['users'][0]))
        with self.assertRaisesRegex(ValueError,'row count'):self.compare()


class BuildReportContract(unittest.TestCase):
    def test_actual_builder_revision_field_is_accepted(self):
        path=Path(__file__).resolve().parents[2]/'results/catalog-seatsurfing-source-build-preparation-v4/manifest.json'
        build={'status':'source_build_verified_and_inventory_complete','application_revision':'9953f452324bab6fb8f7106dd8965cc401aa456c','source_preparation_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'application_image_id':'sha256:'+'b'*64}
        self.assertEqual(checkpoint.bind_build(build),build['application_image_id'])
        build['application_revision']='wrong'
        with self.assertRaisesRegex(RuntimeError,'revision'):checkpoint.bind_build(build)


class CaptureBinding(unittest.TestCase):
    def run_capture(self, *, changed=False, corrupt=False, zone='UTC'):
        fixture=snapshot({'locations':[{'id':'fixture'}]})
        first=fixture['state'];second=copy.deepcopy(first)
        if changed: second['roles_sha256']='b'*64
        line=fixture['row_data'][0]['rows'][0]+(' ' if corrupt else '')+'\n'
        def sql(query):
            if query=='SHOW TimeZone':return zone
            self.assertEqual(query,'SELECT row_to_json(t)::text FROM ONLY "public"."locations" t')
            return line
        with patch.object(capture.checkpoint,'bind_build'),patch.object(capture.checkpoint,'guard'),patch.object(capture.checkpoint,'sql',side_effect=sql),patch.object(capture.checkpoint,'fingerprint',side_effect=[first,second]):
            return capture.capture_state({})
    def test_rows_bound_to_unchanged_before_after_fingerprints(self):
        result=self.run_capture();self.assertEqual(result['status'],'paused_comparison_state_captured');self.assertEqual(result['field_exclusions'],[])
    def test_concurrent_metadata_change_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'changed during'):self.run_capture(changed=True)
    def test_row_fingerprint_mismatch_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'differ from fingerprint'):self.run_capture(corrupt=True)
    def test_non_utc_database_cannot_supply_timestamp_comparison(self):
        with self.assertRaisesRegex(RuntimeError,'UTC'):self.run_capture(zone='America/Los_Angeles')


if __name__=='__main__':unittest.main()
