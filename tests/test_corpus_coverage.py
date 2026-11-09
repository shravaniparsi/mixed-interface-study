from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_corpus_coverage import inputs
from mixed_interface.coverage import build, reconstruct, require_primary_dispatch, validate


class CorpusCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=inputs()
    def setUp(self):self.inventory,self.registries,self.contracts,self.selections=deepcopy(self.base)
    def build(self):return build(self.inventory,self.registries,self.contracts,self.selections)

    def test_complete_scope_and_branch_accounting(self):
        data=self.build();counts=data['counts']
        self.assertEqual((counts['pair_entries'],counts['singletons'],counts['logical_branches'],counts['workflow_templates']),(73,2,148,8))
        branches=[b['logical_branch_id'] for r in data['rows'] for b in r['branches']]
        self.assertEqual(len(set(branches)),148)
        self.assertEqual(counts['primary_dispatch_ready'],0)

    def test_every_inventory_row_preserved_exactly(self):
        data=self.build()
        self.assertEqual([r['inventory_entry'] for r in data['rows']],self.inventory['pairs']+self.inventory['unpaired_controls'])

    def test_no_extra_native_counterfactuals(self):
        rows=[r for r in self.build()['rows'] if r['entry_kind']=='singleton']
        self.assertEqual(len(rows),2)
        for r in rows:
            self.assertIsNone(r['reference_control_pair_id'])
            self.assertEqual([b['continuation_interface'] for b in r['branches']],['ui'])
            self.assertEqual(r['branches'][0]['producer_interface'],'ui')

    def test_same_catalog_workflow_and_producer_reference(self):
        data=self.build();by_id={r['inventory_entry']['pair_id']:r for r in data['rows']}
        for r in data['rows']:
            if r['reference_control_pair_id'] is None:continue
            a=r['inventory_entry'];b=by_id[r['reference_control_pair_id']]['inventory_entry']
            self.assertEqual(tuple(a[k] for k in ('catalog','workflow_id','producer_interface')),tuple(b[k] for k in ('catalog','workflow_id','producer_interface')))

    def test_quartz_unexecuted_boundary_exposure_preserved(self):
        rows=[r for r in self.build()['rows'] if r['inventory_entry']['prior_exposure']=='source_inspected_boundary_not_executed']
        self.assertEqual(sum(len(r['branches']) for r in rows),40)
        self.assertTrue(all(not r['recorded_engineering_evidence'] and r['open_binding_gaps'] for r in rows))

    def test_outside_inventory_engineering_control_not_added(self):
        self.assertEqual(self.build()['engineering_controls_outside_retained_inventory'],['article-tag-order-duplicates-control'])

    def test_changed_control_payload_does_not_inherit_prospective_qualification(self):
        self.selections['realworld_paired']['cases'][0]['prefix_payload']['body']='different input'
        row=next(r for r in self.build()['rows'] if r['inventory_entry'].get('candidate_id')=='article-valid')
        self.assertEqual(row['path_family'],'realworld_legacy')
        self.assertNotIn('manifests/realworld-paired-runner-qualification.json',row['recorded_engineering_evidence'])

    def test_profile_identity_helper_limit_is_explicit(self):
        rows=[r for r in self.build()['rows'] if r['inventory_entry'].get('candidate_id','').startswith('profile-username-')]
        self.assertEqual(len(rows),4)
        self.assertTrue(all('profile_identity_fields_outside_normalization_helper' in r['open_binding_gaps'] for r in rows))

    def test_changed_exposure_or_missing_row_rejected(self):
        self.inventory['pairs'][0]['prior_exposure']='unseen'
        with self.assertRaisesRegex(ValueError,'semantics or exposure'):self.build()
        self.inventory=deepcopy(self.base[0]);self.inventory['pairs'].pop()
        with self.assertRaises(ValueError):self.build()

    def test_source_payload_change_rejected(self):
        self.registries['realworld_development']['cases'][0]['prefix_payload']['body']='changed'
        with self.assertRaisesRegex(ValueError,'semantics or exposure'):self.build()

    def test_missing_workflow_contract_rejected(self):
        del self.contracts['workflows']['realworld.article_create_body_edit']
        with self.assertRaises((KeyError,ValueError)):self.build()

    def test_reference_cannot_cross_workflow(self):
        self.contracts['workflows']['realworld.article_create_body_edit']['reference_control_candidate']='profile-bio-valid'
        with self.assertRaisesRegex(ValueError,'crosses'):self.build()

    def test_rejected_reference_cannot_be_substituted(self):
        self.contracts['workflows']['realworld.article_create_body_edit']['reference_control_candidate']='article-body-omitted'
        with self.assertRaisesRegex(ValueError,'positive control'):self.build()

    def test_petclinic_channel_names_explicit(self):
        rows=[r for r in self.build()['rows'] if r['inventory_entry']['catalog']=='petclinic_development']
        self.assertEqual(len(rows),18)
        self.assertTrue(all({b['continuation_interface']:b['runner_channel'] for b in r['branches']}=={'api':'api_semantic','ui':'fresh_ui'} for r in rows))

    def test_readiness_promotion_and_deleted_gap_rejected(self):
        saved=self.build();saved['rows'][0]['primary_dispatch_ready']=True
        with self.assertRaisesRegex(ValueError,'dispatch flags'):validate(saved,self.inventory,self.registries,self.contracts,self.selections)
        saved=self.build();next(r for r in saved['rows'] if r['open_binding_gaps'])['open_binding_gaps']=[]
        with self.assertRaises(ValueError):validate(saved,self.inventory,self.registries,self.contracts,self.selections)

    def test_dispatch_guard_cannot_be_bypassed_by_truthy_flags(self):
        saved=self.build();saved['execution_authorized']=True;saved['rows'][0]['primary_dispatch_ready']=True
        with self.assertRaisesRegex(ValueError,'not a frozen'):require_primary_dispatch(saved,[saved['rows'][0]['inventory_entry']['pair_id']])

    def test_duplicate_or_foreign_selection_rejected(self):
        saved=self.build();identifier=saved['rows'][0]['inventory_entry']['pair_id']
        for ids in ([],[identifier,identifier],['foreign']):
            with self.assertRaises(ValueError):require_primary_dispatch(saved,ids)

    def test_mutated_generated_reference_rejected_even_with_rebuilt_inventory(self):
        for case in self.registries['quartz_generated_v2']['cases']:
            if case['intervention']=='route_only':case['mutation']={'kind':'synthetic-unregistered-change'}
        pairs,singletons=reconstruct(self.registries,self.contracts)
        self.inventory['pairs']=pairs;self.inventory['unpaired_controls']=singletons
        with self.assertRaisesRegex(ValueError,'accepted route control'):self.build()

    def test_qualified_realworld_path_is_limited_to_exact_selected_entries(self):
        rows=[r for r in self.build()['rows'] if r['path_family']=='realworld_paired_controls']
        self.assertEqual(len(rows),6)
        for row in rows:
            self.assertEqual(row['terminal_v2_bridge'],'scripts/realworld_expanded_campaign.py')
            self.assertIn('manifests/realworld-expanded-integration-qualification.json',row['recorded_engineering_evidence'])
            self.assertFalse(row['open_binding_gaps'])
            self.assertFalse(row['primary_dispatch_ready'])

    def test_changed_selection_does_not_inherit_expanded_qualification(self):
        self.selections['realworld_paired']['cases'][5]['prefix_payload']={'bio':'changed'}
        row=next(r for r in self.build()['rows'] if r['inventory_entry'].get('candidate_id')=='profile-bio-null')
        self.assertEqual(row['path_family'],'realworld_legacy')
        self.assertNotIn('manifests/realworld-expanded-integration-qualification.json',row['recorded_engineering_evidence'])
        self.assertIn('realworld_v2_job_dispatch',row['open_binding_gaps'])

    def test_rejection_path_qualification_does_not_cover_unexpected_acceptance(self):
        rows=[r for r in self.build()['rows'] if r['path_family']=='realworld_rejection_controls']
        self.assertEqual({r['inventory_entry']['candidate_id'] for r in rows},{'article-body-omitted','comment-body-omitted','profile-username-empty'})
        for row in rows:
            self.assertIn('manifests/realworld-rejection-integration-qualification.json',row['recorded_engineering_evidence'])
            self.assertIn('unexpected_acceptance_normalization_and_continuation',row['open_binding_gaps'])
            self.assertNotIn('realworld_v2_job_dispatch',row['open_binding_gaps'])
            self.assertFalse(row['primary_dispatch_ready'])

    def test_changed_rejection_payload_does_not_inherit_qualification(self):
        self.selections['realworld_rejection']['cases'][-1]['prefix_payload']={'username':'different'}
        row=next(r for r in self.build()['rows'] if r['inventory_entry'].get('candidate_id')=='profile-username-empty')
        self.assertEqual(row['path_family'],'realworld_legacy')
        self.assertNotIn('manifests/realworld-rejection-integration-qualification.json',row['recorded_engineering_evidence'])

    def test_petclinic_selected_paths_only(self):
        rows=[r for r in self.build()['rows'] if r['path_family']=='petclinic_terminal_controls']
        self.assertEqual(len(rows),6)
        for row in rows:
            self.assertEqual(row['open_binding_gaps'],['petclinic_unexpected_prefix_outcome_extraction'])
            self.assertFalse(row['primary_dispatch_ready'])

    def test_changed_petclinic_registry_does_not_inherit_qualification(self):
        self.selections['petclinic_terminal']['registry_semantic_sha256']='changed'
        self.assertFalse(any(r['path_family']=='petclinic_terminal_controls' for r in self.build()['rows']))
