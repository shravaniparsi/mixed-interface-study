"""A docstring-only classification must not hide executable string changes."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extension'))
from audit_vibe_mutation_source_v1 import normalized


class VibeSourceAuditTests(unittest.TestCase):
    def test_docstring_change_ignores_only_documentation(self):
        self.assertEqual(normalized('def f():\n    "left and right"\n    return 1\n'), normalized('def f():\n    "left or right"\n    return 1\n'))

    def test_returned_or_exception_strings_remain_observable_changes(self):
        self.assertNotEqual(normalized('def f():\n    return "a and b"\n'), normalized('def f():\n    return "a or b"\n'))
        self.assertNotEqual(normalized('raise ValueError("a and b")'), normalized('raise ValueError("a or b")'))

    def test_executable_change_with_same_docstring_is_not_removed(self):
        self.assertNotEqual(normalized('def f():\n    "doc"\n    return 1\n'), normalized('def f():\n    "doc"\n    return 2\n'))


if __name__ == '__main__':
    unittest.main()
