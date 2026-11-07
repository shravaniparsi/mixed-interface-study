"""Synthetic counterexamples: never experimental observations or defect labels."""
import copy,unittest
from mixed_interface.attribution import normalize_case,compare_pair,counts,GATES


def branch(channel,*,failed=None,rejected=False,empty=False):
    assigned='assigned_api_continuation' if channel=='api' else 'assigned_native_continuation'
    components={};rules={}
    for name in [assigned,'shared_post_continuation_api_readback','shared_final_native_read','environment_reset_cleanup']:
        role='comparability_guard' if name=='environment_reset_cleanup' else 'observation'
        checks=[] if rejected or empty and name==assigned else [{'id':'probe','passed':name!=failed}]
        components[name]={'checks':checks,'status':'no_check_mismatch_observed','comparison_eligible':True}
        rules[name+'::probe']={'component':name,'role':role}
    raw={'case_id':'fixture-'+channel,'route':'api-'+channel,'accepted_prefix':not rejected,'execution_evidence_complete':True,'components':components}
    return raw,rules

def norm(channel,**kwargs):
    r,m=branch(channel,**kwargs);return normalize_case(r,'synthetic',m,record_id=channel)

def pair(a=None,u=None,gates=None):
    return compare_pair(a or norm('api'),u or norm('ui'),gates or {k:True for k in GATES},pair_id='synthetic',catalog='synthetic',workflow='synthetic')


class AttributionTests(unittest.TestCase):
    def test_shared_native_read_failure_does_not_create_ui_only_credit(self):
        r=pair(u=norm('ui',failed='shared_final_native_read'))
        self.assertEqual(r['assigned_signal_overlap'],'neither');self.assertEqual(len(r['shared_mismatches']),1)
    def test_common_api_readback_failure_is_shared_even_after_native_action(self):
        r=pair(norm('api',failed='shared_post_continuation_api_readback'),norm('ui',failed='shared_post_continuation_api_readback'))
        self.assertEqual(r['assigned_signal_overlap'],'neither');self.assertEqual(len(r['shared_mismatches']),2)
    def test_assigned_channel_mismatches_have_four_distinct_states(self):
        for a,u,wanted in [(False,False,'neither'),(True,False,'api_only'),(False,True,'ui_only'),(True,True,'both')]:
            r=pair(norm('api',failed='assigned_api_continuation' if a else None),norm('ui',failed='assigned_native_continuation' if u else None))
            self.assertEqual(r['assigned_signal_overlap'],wanted)
    def test_missing_assigned_checks_are_not_a_clean_pass(self):
        r=pair(u=norm('ui',empty=True));self.assertEqual(r['status'],'unresolved_pair');self.assertIsNone(r['assigned_signal_overlap'])
    def test_comparability_guard_failure_is_not_an_application_signal(self):
        r=pair(u=norm('ui',failed='environment_reset_cleanup'));self.assertEqual(r['status'],'unresolved_pair');self.assertIsNone(r['assigned_signal_overlap'])
    def test_rejected_prefixes_never_enter_continuation_overlap(self):
        r=pair(norm('api',rejected=True),norm('ui',rejected=True));self.assertEqual(r['status'],'rejected_prefix_no_continuation_contrast');self.assertIsNone(r['assigned_signal_overlap'])
    def test_unknown_check_and_component_fail_closed(self):
        for mode in ('check','component'):
            r,m=branch('ui')
            if mode=='check':r['components']['assigned_native_continuation']['checks'][0]['id']='unmapped'
            else:r['components']['unknown']=r['components'].pop('assigned_native_continuation')
            with self.assertRaises(ValueError):normalize_case(r,'synthetic',m,record_id='u')
    def test_failed_or_unobserved_pair_gate_prevents_clean_comparison(self):
        for value in (False,None):
            gates={k:True for k in GATES};gates['same_pre_candidate_state']=value
            self.assertEqual(pair(gates=gates)['status'],'unresolved_pair')
    def test_mixed_acceptance_is_unresolved(self):
        self.assertEqual(pair(u=norm('ui',rejected=True))['status'],'unresolved_pair')
    def test_unpaired_and_rejected_records_have_separate_denominators(self):
        ps=[pair(),pair(norm('api',rejected=True),norm('ui',rejected=True))]
        c=counts(ps,[1,2,3,4,5],['singleton'])
        self.assertEqual((c['branch_records'],c['accepted_control_pairs'],c['rejected_prefix_pairs'],c['unpaired_control_records']),(5,1,1,1))
        self.assertEqual(c['assigned_check_mismatch_overlap']['neither'],1);self.assertIsNone(c['independent_sample_size'])
    def test_non_boolean_verdict_is_not_a_pass(self):
        r,m=branch('ui');r['components']['assigned_native_continuation']['checks'][0]['passed']=1
        with self.assertRaises(ValueError):normalize_case(r,'synthetic',m,record_id='u')
    def test_ineligible_component_is_unresolved(self):
        r,m=branch('ui');r['components']['assigned_native_continuation']['comparison_eligible']=False
        u=normalize_case(r,'synthetic',m,record_id='ui');self.assertEqual(pair(u=u)['status'],'unresolved_pair')
    def test_unresolved_policy_check_never_becomes_exclusive_channel_credit(self):
        r,m=branch('ui');r['policy_unresolved']=True;r['components']['unresolved_policy']={'checks':[{'id':'policy','passed':False}],'status':'policy_observations_only','comparison_eligible':False}
        m['unresolved_policy::policy']={'component':'unresolved_policy','role':'unresolved_policy'}
        result=pair(u=normalize_case(r,'synthetic',m,record_id='ui'));self.assertEqual(result['assigned_signal_overlap'],'neither');self.assertTrue(result['unresolved_policy_present'])
    def test_missing_gate_vocabulary_is_rejected(self):
        with self.assertRaises(ValueError):pair(gates={'some_gate':True})

    def test_unknown_component_status_is_rejected(self):
        r,m=branch('ui');r['components']['assigned_native_continuation']['status']='invented_pass'
        with self.assertRaises(ValueError):normalize_case(r,'synthetic',m,record_id='ui')
    def test_evidence_issues_override_a_claim_of_completeness(self):
        r,m=branch('ui');r['evidence_issues']=['lost_response']
        self.assertEqual(pair(u=normalize_case(r,'synthetic',m,record_id='ui'))['status'],'unresolved_pair')
    def test_different_producer_routes_cannot_be_paired_by_assertion(self):
        u=norm('ui');u['route']='ui-ui'
        self.assertEqual(pair(u=u)['status'],'unresolved_pair')
