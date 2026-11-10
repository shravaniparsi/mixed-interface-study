"""Full-corpus runtime mapping, including Unicode and separately bound controls."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from primary_catalog_v1 import templates,read

class PrimaryCatalogTests(unittest.TestCase):
    def test_every_retained_entry_has_exact_template_and_reference(self):
        v=templates();self.assertEqual(v,read(ROOT/'manifests/primary-runtime-catalog-v1.json'))
        self.assertEqual(v['counts'],{'entries':75,'pairs':73,'singletons':2,'branches':148})
        self.assertFalse(v['execution_authorized']);self.assertFalse(v['primary_freeze_complete'])
        for b in v['bindings']:
            if b['entry_kind']=='singleton':self.assertIsNone(b['reference_runtime']);self.assertEqual(b['runtime']['branch_order'],['ui'])
            else:self.assertEqual(set(b['reference_runtime']['source_case_sha256']),{'api','ui'})
    def test_reference_uses_candidate_instrumentation_even_when_catalog_control_differs(self):
        entries={b['entry']['pair_id']:b for b in templates()['bindings']}
        identity=entries['realworld_development::profile-username-length60']
        control=entries[identity['reference_pair_id']]
        self.assertEqual(identity['runtime']['profile'],identity['reference_runtime']['profile'])
        self.assertNotEqual(identity['reference_runtime']['profile'],control['runtime']['profile'])
        self.assertEqual(identity['reference_runtime']['source_case_sha256'],control['runtime']['source_case_sha256'])
    def test_unicode_cases_preserve_original_catalog_hashes(self):
        rows=read(ROOT/'manifests/retained-corpus-review-v5.json')['review']['rows']
        expected={r['inventory_entry']['pair_id']:{b['continuation_interface']:b['source_case_sha256'] for b in r['branches']} for r in rows}
        for b in templates()['bindings']:self.assertEqual(b['runtime']['source_case_sha256'],expected[b['entry']['pair_id']])
