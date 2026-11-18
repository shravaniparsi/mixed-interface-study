import json
import unittest
from checkpoint_field_diff_v1 import differences, compare_documents


class FieldDiffTests(unittest.TestCase):
    def test_missing_null_and_escaped_keys_are_distinct(self):
        rows = differences({'a/b': None, 'gone': 1}, {'a/b': '', 'new': None})
        self.assertEqual([(r['path'], r['change']) for r in rows], [('/a~1b', 'value_or_type'), ('/gone', 'removed'), ('/new', 'added')])

    def test_array_permutation_and_timestamp_precision(self):
        rows = differences({'roles': ['A', 'B'], 't': '2026-01-01T00:00:00.123456789Z'}, {'roles': ['B', 'A'], 't': '2026-01-01T00:00:00.123457Z'})
        self.assertTrue(rows[0]['same_element_multiset'])
        self.assertEqual(rows[-1]['utc_instant_comparison']['after_minus_before_nanoseconds'], 211)

    def test_all_documents_included_without_values(self):
        rows = compare_documents([{'index':'user','id':'1','source':{'password':'private-token'}}], [{'index':'user','id':'1','source':{'password':'changed-token'}}, {'index':'user','id':'2','source':{}}])
        self.assertEqual(len(rows['changed_documents']), 2)
        text = json.dumps(rows)
        self.assertNotIn('private-token', text)
        self.assertNotIn('changed-token', text)


if __name__ == '__main__':
    unittest.main()
