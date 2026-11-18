import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('state',Path(__file__).resolve().parents[1]/'scripts/extension/maxun_postgres_state_v1.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class LogicalExport(unittest.TestCase):
    def test_values_are_preserved(self):
        raw=b'{"schema":"public","table":"robot","rows":[{"id":"same","timestamp":"fixed","name":null,"workflow":[2,1]}]}\n'
        value=module.parse_state(raw)
        self.assertEqual(value['tables'][0]['rows'][0],{'id':'same','timestamp':'fixed','name':None,'workflow':[2,1]})
        self.assertFalse(value['comparison_coverage_qualified'])
    def test_empty_table_retained(self):
        self.assertEqual(module.parse_state(b'{"schema":"public","table":"session","rows":[]}')['tables'][0]['rows'],[])
    def test_missing_tables_and_incomplete_rows_rejected(self):
        for raw in [b'',b'{"schema":"public","table":"robot"}',b'{"schema":"public","table":"robot","rows":[null]}']:
            with self.assertRaises(ValueError):module.parse_state(raw)
    def test_fractional_values_remain_distinguishable(self):
        template='{"schema":"public","table":"robot","rows":[{"number":%s}]}'
        a=module.parse_state((template % '0.123456789012345671').encode())
        b=module.parse_state((template % '0.123456789012345672').encode())
        self.assertEqual(a['tables'][0]['rows'], b['tables'][0]['rows'])
        self.assertNotEqual(a['tables'][0]['exact_rows'], b['tables'][0]['exact_rows'])
        self.assertEqual(a['comparison_field'], 'exact_rows')
    def test_types_cannot_collide(self):
        from decimal import Decimal
        self.assertNotEqual(module.exact_value(Decimal('1')), module.exact_value('1'))
        self.assertNotEqual(module.exact_value(True), module.exact_value(Decimal('1')))
        self.assertNotEqual(module.exact_value({'number':'1'}), module.exact_value(Decimal('1')))
        self.assertEqual(module.exact_value({'a':None,'b':True}),module.exact_value({'b':True,'a':None}))
    def test_non_json_constants_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_state(b'{"schema":"public","table":"robot","rows":[{"value":NaN}]}')
    def test_duplicate_relation_rejected(self):
        row=b'{"schema":"public","table":"robot","rows":[]}\n'
        with self.assertRaisesRegex(ValueError,'Duplicate'):module.parse_state(row+row)

if __name__=='__main__':unittest.main()
