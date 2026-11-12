import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('adapter_score', Path(__file__).resolve().parents[1] / 'scripts/extension/score_adapter_comparison_v1.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class RequestComparisonTests(unittest.TestCase):
    def request(self, body, media='application/json'):
        return {'method': 'PATCH', 'path': '/records/seed', 'content_type': media, 'raw_body': body}

    def test_permits_declared_media_and_object_order_equivalence(self):
        self.assertTrue(module.same_request(self.request('{"x":1,"y":2}'), self.request('{ "y": 2, "x": 1 }', 'application/merge-patch+json')))

    def test_preserves_null_absence_boolean_number_and_array_order(self):
        for first, second in [('{}', '{"x":null}'), ('{"x":false}', '{"x":0}'), ('{"x":[1,2]}', '{"x":[2,1]}')]:
            with self.subTest(first=first):
                self.assertFalse(module.same_request(self.request(first), self.request(second)))

    def test_rejects_wrong_path_or_media(self):
        other = self.request('{}'); other['path'] = '/records/sibling'
        self.assertFalse(module.same_request(self.request('{}'), other))
        self.assertFalse(module.same_request(self.request('{}'), self.request('{}', 'text/plain')))
