"""Synthetic Docker diff/state predicates, plus optional local inventory check."""
from copy import deepcopy
from pathlib import Path
import os
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import nginx_root_layer_comparison_v1 as m
import nginx_root_layer_inventory_v1 as inventory

class RootLayerTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(path='/etc/passwd',kind='file',sha256='same',bytes=4,uid=0,gid=0,mode=420,links=1,mtime_ns=1000000000),dict(path='/app/index.js',kind='file',sha256='code',bytes=8,uid=0,gid=0,mode=420,links=1,mtime_ns=1000000000)]
        a={'rows':rows,'extended_attributes_absent':True};b=deepcopy(a)
        return a,b,b'C /etc/passwd\nC /app/index.js\n',dict(timezone='UTC',start_epoch_seconds=1.5,end_epoch_seconds=2.5)
    def test_exact_operation_and_bounded_account_rewrite(self):
        a,b,d,w=self.fixture();m.compare_root_layers(a,b,d,d,'operation',w)
        b['rows'][0]['mtime_ns']=2000000000;m.compare_root_layers(a,b,d,d,'restart',w)
        with self.assertRaises(ValueError):m.compare_root_layers(a,b,d,d,'operation',w)
    def test_account_contents_and_code_changes_never_ignored(self):
        for index in (0,1):
            a,b,d,w=self.fixture();b['rows'][index]['sha256']='different'
            with self.assertRaisesRegex(ValueError,'Unexplained'):m.compare_root_layers(a,b,d,d,'restart',w)
    def test_missing_coverage_added_path_and_kind_change_rejected(self):
        a,b,d,w=self.fixture()
        with self.assertRaisesRegex(ValueError,'membership'):m.compare_root_layers(a,b,d,d+b'A /unexpected\n','restart',w)
        with self.assertRaisesRegex(ValueError,'kind'):m.compare_root_layers(a,b,d,d.replace(b'C /app',b'A /app'),'restart',w)
        b['rows'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'):m.compare_root_layers(a,b,d,d,'operation',w)
    def test_stale_rewrite_timestamp_rejected(self):
        a,b,d,w=self.fixture();b['rows'][0]['mtime_ns']=3000000000
        with self.assertRaisesRegex(ValueError,'timestamp'):m.compare_root_layers(a,b,d,d,'restart',w)
    def test_malformed_duplicate_and_traversal_paths_rejected(self):
        for raw in (b'X /etc/a\n',b'C relative\n',b'C /etc/../secret\n',b'C /etc/a\nC /etc/a\n'):
            with self.assertRaises(ValueError):m.parse_diff(raw)
    def test_supervision_state_has_no_blanket_exception(self):
        a,b,d,w=self.fixture();a['rows'][1]['path']=b['rows'][1]['path']='/run/s6/state';b['rows'][1]['sha256']='different';d=d.replace(b'/app/index.js',b'/run/s6/state')
        with self.assertRaisesRegex(ValueError,'Unexplained'):m.compare_root_layers(a,b,d,d,'restart',w)
    @unittest.skipUnless(hasattr(os,'listxattr'),'Native xattr inspection unavailable locally')
    def test_inventory_hashes_files_without_following_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'file').write_bytes(b'synthetic');os.symlink('file',root/'link')
            rows=inventory.inspect_paths([str(root/'file'),str(root/'link'),str(root/'absent')])['rows']
            indexed={r['path']:r for r in rows}
            self.assertEqual(indexed[str(root/'link')]['kind'],'symlink')
            self.assertEqual(indexed[str(root/'absent')]['kind'],'absent')
            self.assertEqual(indexed[str(root/'file')]['bytes'],9)

if __name__=='__main__':unittest.main()
