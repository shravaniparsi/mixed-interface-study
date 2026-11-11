"""Adversarial data-bundle checks; no model or benchmark runs."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/extension/build_restestbench_generator_inputs_v1.py'
spec=importlib.util.spec_from_file_location('input_builder',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class InputBoundaryTests(unittest.TestCase):
    def test_extra_source_or_label_file_rejected(self):
        clean={'service/requirements.json':b'[{"id":1,"description":"Create an item"}]'}
        module.validate_bundle(module.packed(clean),clean)
        for name in ['mutants.json','golden/test.py','results.json','../secret.txt']:
            with self.assertRaises(AssertionError):module.validate_bundle(module.packed({**clean,name:b'{}'}),clean)
    def test_mutation_field_rejected_even_if_file_name_is_allowed(self):
        files={'service/requirements.json':b'[{"id":1,"description":"Create an item","mutants":[]}]'}
        with self.assertRaises(AssertionError):module.validate_bundle(module.packed(files),files)
    def test_duplicate_requirement_id_rejected(self):
        files={'service/requirements.json':b'[{"id":1,"description":"First"},{"id":1,"description":"Second"}]'}
        with self.assertRaises(AssertionError):module.validate_bundle(module.packed(files),files)

if __name__=='__main__':unittest.main()
