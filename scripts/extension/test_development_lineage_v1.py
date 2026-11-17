import copy
import json
import unittest
from compose_development_lineage_v1 import ROOT, compose


class LineageTest(unittest.TestCase):
    def setUp(self):
        self.forms, self.payloads, self.services = [json.loads((ROOT / ('manifests/' + n + '.json')).read_text())
            for n in ['development-reactive-form-inventory-v1', 'development-reactive-payload-inventory-v1',
                      'development-service-http-inventory-v1']]
        self.allowed = {r['full_name'] for r in self.payloads['rows']}

    def run_compose(self):
        return compose(self.forms, self.payloads, self.services, self.allowed)

    def test_confirmation_is_not_body_obligation(self):
        r = self.run_compose()
        call = r['rows'][0]['calls'][0]
        a = call['arguments'][0]
        self.assertEqual([f['payload_field'] for f in a['fields'] if f['direct_body_parameter_candidate']],
                         ['login', 'email', 'password'])
        self.assertEqual(a['controls_absent_from_literal'][0]['control']['field'], 'confirmPassword')
        self.assertEqual(a['fields'][-1]['status'], 'unresolved_control')
        self.assertEqual(call['component_call']['lexical_guards'][0]['branch'], 'else')
        self.assertEqual(r['complete_api_rules'], 0)

    def test_component_hash_revision_project_fail_closed(self):
        original = copy.deepcopy(self.forms)
        for key in ['source_sha256', 'commit', 'full_name']:
            self.forms = copy.deepcopy(original)
            self.forms['rows'][0][key] = 'wrong'
            with self.assertRaises(ValueError):
                self.run_compose()

    def test_service_wrong_project_revision_class_or_method_does_not_join(self):
        original = copy.deepcopy(self.services)
        for key in ['full_name', 'commit', 'class_name', 'method']:
            self.services = copy.deepcopy(original)
            if key == 'method':
                self.services['rows'][0]['methods'][0][key] = 'wrong'
            else:
                self.services['rows'][0][key] = 'wrong'
            self.assertEqual(self.run_compose()['rows'][0]['calls'][0]['service_candidate_count'], 0)

    def test_ambiguous_service_does_not_join(self):
        self.services['rows'].append(copy.deepcopy(self.services['rows'][0]))
        call = self.run_compose()['rows'][0]['calls'][0]
        self.assertEqual(call['service_candidate_count'], 2)
        self.assertFalse(any(f['direct_body_parameter_candidate'] for f in call['arguments'][0]['fields']))

    def test_unknown_field_does_not_join(self):
        self.payloads['rows'][0]['calls'][0]['arguments'][0]['fields'][0]['source']['field'] = 'absent'
        self.assertEqual(self.run_compose()['rows'][0]['calls'][0]['arguments'][0]['fields'][0]['status'],
                         'unresolved_control')

    def test_wrappers_preserve_uncertainty(self):
        for call in self.run_compose()['rows'][2]['calls']:
            self.assertEqual(call['service_method']['reason'], 'wrapper_not_httpclient')
            fields = call['arguments'][0]['fields']
            self.assertEqual(len(fields), 4)
            self.assertFalse(any(f['direct_body_parameter_candidate'] for f in fields))

    def test_reserved_input_rejected(self):
        self.allowed.remove(self.payloads['rows'][0]['full_name'])
        with self.assertRaises(ValueError):
            self.run_compose()


if __name__ == '__main__':
    unittest.main()
