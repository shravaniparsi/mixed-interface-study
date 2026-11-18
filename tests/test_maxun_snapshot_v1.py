import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('maxun_snapshot', Path(__file__).resolve().parents[1] / 'scripts/extension/maxun_snapshot_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SnapshotInventory(unittest.TestCase):
    def archive(self, root, filename, members):
        path = Path(root) / filename
        with tarfile.open(path, 'w') as archive:
            for name, content, overrides in members:
                info = tarfile.TarInfo(name)
                info.size, info.uid, info.gid, info.mode, info.mtime = len(content), 999, 999, 0o600, 123456
                for key, value in overrides.items():
                    setattr(info, key, value)
                archive.addfile(info, io.BytesIO(content))
        return path

    def test_file_contents_and_metadata_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            base = self.archive(root, 'a.tar', [('base/1', b'original', {})])
            actual = module.archive_inventory(base)['base/1']
            self.assertEqual((actual['uid'], actual['gid'], actual['mode'], actual['mtime']), (999,999,0o600,123456))
            changed = self.archive(root, 'b.tar', [('base/1', b'changed!', {})])
            self.assertNotEqual(module.archive_inventory(base), module.archive_inventory(changed))
            altered = self.archive(root, 'c.tar', [('base/1', b'original', {'mtime':123457})])
            self.assertNotEqual(module.archive_inventory(base), module.archive_inventory(altered))

    def test_tar_member_order_does_not_hide_extra_file(self):
        with tempfile.TemporaryDirectory() as root:
            members = [('a', b'1', {}), ('b', b'2', {})]
            a = self.archive(root,'a.tar',members)
            b = self.archive(root,'b.tar',list(reversed(members)))
            self.assertEqual(module.archive_inventory(a),module.archive_inventory(b))
            c = self.archive(root,'c.tar',members+[('leftover',b'x',{})])
            self.assertNotEqual(module.archive_inventory(a),module.archive_inventory(c))

    def test_traversal_and_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            for n,name in enumerate(['../outside', '/absolute']):
                with self.assertRaisesRegex(ValueError,'Unsafe'):
                    module.archive_inventory(self.archive(root,str(n)+'.tar',[(name,b'x',{})]))

    def test_links_and_duplicate_members_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'Unsupported'):
                module.archive_inventory(self.archive(root,'link.tar',[('a',b'',{'type':tarfile.SYMTYPE,'linkname':'elsewhere'})]))
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                module.archive_inventory(self.archive(root,'duplicate.tar',[('a',b'1',{}),('a',b'2',{})]))

    def test_empty_archive_is_not_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'Empty'):
                module.archive_inventory(self.archive(root,'empty.tar',[]))


if __name__ == '__main__':
    unittest.main()
