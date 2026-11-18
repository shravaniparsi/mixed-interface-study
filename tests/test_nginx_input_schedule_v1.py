"""Input isolation and coverage, with no application or schema execution."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/build_nginx_input_schedule_v1.py'
spec = importlib.util.spec_from_file_location('nginx_inputs', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NginxInputScheduleTests(unittest.TestCase):
    def test_each_mutation_changes_only_one_leaf(self):
        for pointer in module.PROPERTIES:
            for operation in ('omit', 'null'):
                with self.subTest(pointer=pointer, operation=operation):
                    body = module.mutate(pointer, operation)
                    original = module.ORDINARY
                    parts = pointer[1:].split('/')
                    parent, original_parent = body, original
                    for part in parts[:-1]:
                        key = int(part) if isinstance(parent, list) else part
                        parent, original_parent = parent[key], original_parent[key]
                    if operation == 'omit':
                        self.assertNotIn(parts[-1], parent)
                    else:
                        self.assertIsNone(parent[parts[-1]])
                    parent[parts[-1]] = original_parent[parts[-1]]
                    self.assertEqual(body, original)
        self.assertEqual(module.ORDINARY['items'][0]['password'], 'Study-Only-Control-2026')

    def test_first_other_property_and_ordinary_coverage(self):
        plan = module.build()
        self.assertEqual(len(plan['cases']), 9)
        self.assertEqual(plan['supported_properties'], sorted(module.PROPERTIES))
        ordinary_edits = plan['cases'][0]['independent_continuations']
        for case in plan['cases'][1:]:
            target = case['mutation']['pointer']
            edit, = case['independent_continuations']
            self.assertEqual(edit['path'], next(p for p in sorted(module.PROPERTIES) if p != target))
            self.assertIn(edit, ordinary_edits)
        self.assertEqual(len(ordinary_edits), 2)

    def test_reject_unscheduled_variants(self):
        for pointer, operation in [('/clients/0/directive', 'omit'), ('/name', 'empty'), ('/items/1/password', 'null')]:
            with self.subTest(pointer=pointer, operation=operation):
                with self.assertRaises(AssertionError):
                    module.mutate(pointer, operation)


if __name__ == '__main__':
    unittest.main()
