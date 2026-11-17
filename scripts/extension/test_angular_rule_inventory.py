import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.angular_rule_inventory import inventory

class InventoryTests(unittest.TestCase):
    def source(self,body):
        return "import {required, minLength, schema} from '@angular/forms/signals';\nexport const testSchema = schema<Model>(path => {\n"+body+"\n});\n"
    def test_explicit_calls_and_unknown_callback(self):
        x=inventory(self.source('  required(path.name);\n  minLength(path.name, 2);\n  custom(path.name);'),'fixture')
        self.assertEqual(len(x['candidates']),2);self.assertEqual(len(x['unsupported']),1)
        self.assertEqual(x['candidates'][0]['line'],3)
        self.assertEqual(x['candidates'][1]['bound'],2)
        self.assertTrue(all(r['api_mapping']=='unresolved' for r in x['candidates']))
    def test_guard_cannot_be_silently_discarded(self):
        x=inventory(self.source('  if (enabled) {\n    required(path.name);\n  }'),'fixture')
        self.assertEqual(x['status'],'unsupported_schema_structure');self.assertEqual(x['candidates'],[])
    def test_dynamic_bound_retained_unsupported(self):
        x=inventory(self.source('  minLength(path.name, limit);'),'fixture')
        self.assertEqual(len(x['unsupported']),1);self.assertEqual(x['candidates'],[])
    def test_alias_import_rejected(self):
        s=self.source('  required(path.name);').replace('required,','required as localRequired,')
        self.assertEqual(inventory(s,'fixture')['status'],'unsupported_schema_structure')
    def test_commented_schema_is_not_extracted(self):
        s=self.source('  required(path.name);')
        self.assertEqual(inventory('/*'+s+'*/','fixture')['candidates'],[])
    def test_multiple_schemas_rejected(self):
        s=self.source('  required(path.name);')
        self.assertEqual(inventory(s+s,'fixture')['candidates'],[])

if __name__=='__main__':unittest.main()
