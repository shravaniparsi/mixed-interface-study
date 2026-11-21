import unittest
from mysql_state import canonical_ddl
class SchemaText(unittest.TestCase):
 def test_explicit_redundant_charset(self):
  a='`value` text COLLATE utf8mb4_unicode_ci'
  self.assertEqual(canonical_ddl(a),canonical_ddl('`value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
 def test_actual_collation_change_preserved(self):
  self.assertNotEqual(canonical_ddl('text COLLATE utf8mb4_unicode_ci'),canonical_ddl('text CHARACTER SET utf8mb4 COLLATE utf8mb4_bin'))
 def test_charset_without_collation_preserved(self):
  self.assertNotEqual(canonical_ddl('text CHARACTER SET utf8mb4'),canonical_ddl('text CHARACTER SET latin1'))
