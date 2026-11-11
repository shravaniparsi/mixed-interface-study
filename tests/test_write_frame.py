import unittest
from mixed_interface.write_frame import evaluate


class WriteFrameTests(unittest.TestCase):
    def test_missing_is_not_null(self):
        self.assertEqual(evaluate({'x': None}, {}, {})['frame_violations'], ['x'])
        self.assertEqual(evaluate({}, {'x': None}, {})['frame_violations'], ['x'])

    def test_explicit_clear_and_falsy_values_are_assignments(self):
        for value in (None, '', False, 0, [], {}):
            result = evaluate({'x': 'original', 'y': 1}, {'x': value, 'y': 1}, {'x': value})
            self.assertEqual(result['frame_violations'], [])
            self.assertEqual(result['failed_assignments'], [])

    def test_bool_number_and_nested_changes(self):
        result = evaluate({'x': {'n': False}}, {'x': {'n': 0}}, {})
        self.assertEqual(result['frame_violations'], ['x'])

    def test_omitted_field_is_protected(self):
        result = evaluate({'note': 'a', 'order': 0}, {'note': 'b', 'order': None}, {'note': 'b'})
        self.assertEqual(result['frame_violations'], ['order'])

    def test_failed_request_is_distinct_from_frame(self):
        result = evaluate({'note': 'a'}, {'note': 'a'}, {'note': 'b'})
        self.assertEqual(result['failed_assignments'], ['note'])
        self.assertEqual(result['frame_violations'], [])

    def test_derived_exception_does_not_hide_other_changes(self):
        result = evaluate({'time': 1, 'group': 1}, {'time': 2, 'group': None}, {}, ['time'])
        self.assertEqual(result['frame_violations'], ['group'])
        with self.assertRaises(ValueError):
            evaluate({}, {}, {'time': 2}, ['time'])
