"""Synthetic inventory tests; no application or live filesystem evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extension'))
import nginx_ordinary_filesystem_delta_v1 as m

class FilesystemDeltaTests(unittest.TestCase):
    def fixture(self):
        def row(path, kind='directory'):
            r = dict(path=path, kind=kind, mode=493 if kind=='directory' else 420, uid=1001, gid=1001, mtimeNs='1000000000')
            if kind=='file': r.update(bytes=12, sha256='a'*64)
            return r
        old = dict(extendedAttributesAbsent=True, inventories={root:[row('.')] for root in m.ROOTS})
        old['inventories']['/data'] += [row('access'), row('database.sqlite','file'), row('access/3','file'), row('keys.json','file')]
        new = deepcopy(old)
        for r in new['inventories']['/data']:
            if r['path'] in ('access/3','database.sqlite'): r.update(sha256='b'*64,mtimeNs='2000000000')
        return old,new,dict(timezone='UTC',start_epoch_seconds=1.5,end_epoch_seconds=2.5)
    def test_only_registered_ordinary_writes(self):
        a,b,w=self.fixture(); self.assertEqual(len(m.verify_delta(a,b,w,3)),2)
    def test_unrelated_secret_change_rejected(self):
        a,b,w=self.fixture(); b['inventories']['/data'][-1]['sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'Unrelated'): m.verify_delta(a,b,w,3)
    def test_no_whole_log_or_cache_exclusion(self):
        for root in ('/var/log/nginx','/var/lib/nginx/cache','/var/lib/logrotate'):
            a,b,w=self.fixture(); b['inventories'][root][0]['mtimeNs']='2000000000'
            with self.assertRaisesRegex(ValueError,'Unrelated'): m.verify_delta(a,b,w,3)
    def test_new_unknown_file_rejected(self):
        a,b,w=self.fixture(); b['inventories']['/data'].append(dict(b['inventories']['/data'][-1],path='unexpected'))
        with self.assertRaisesRegex(ValueError,'addition'): m.verify_delta(a,b,w,3)
    def test_timestamp_and_permissions_rejected(self):
        for field,value in (('mtimeNs','3000000000'),('mode',511)):
            a,b,w=self.fixture(); b['inventories']['/data'][2][field]=value
            with self.assertRaises(ValueError): m.verify_delta(a,b,w,3)
    def test_sidecar_requires_original_db_identity(self):
        a,b,w=self.fixture(); r=dict(b['inventories']['/data'][2],path='database.sqlite-wal'); b['inventories']['/data'].append(r)
        m.verify_delta(a,b,w,3); r['uid']=0
        with self.assertRaisesRegex(ValueError,'sidecar'): m.verify_delta(a,b,w,3)
    def test_missing_root_duplicate_and_traversal_rejected(self):
        for defect in ('root','duplicate','traversal'):
            a,b,w=self.fixture()
            if defect=='root': del b['inventories']['/run/nginx']
            elif defect=='duplicate': b['inventories']['/data'].append(deepcopy(b['inventories']['/data'][-1]))
            else: b['inventories']['/data'][-1]['path']='../keys.json'
            with self.assertRaises(ValueError): m.verify_delta(a,b,w,3)

    def test_full_database_and_credential_integration(self):
        import hashlib
        import test_nginx_ordinary_database_comparison_v1 as db_fixture
        import test_nginx_access_file_comparison_v1 as access_fixture
        helper = access_fixture.AccessFileComparisonTests()
        for edit_path in ('/clients/0/address', '/items/0/password'):
            db_before, db_after, edit, window = db_fixture.OrdinaryDatabaseComparisonTests().fixture(edit_path)
            a,b,_ = self.fixture()
            raw_before = helper.file()
            password = 'Study-Only-Edited-2026' if edit_path=='/items/0/password' else 'Study-Only-Control-2026'
            raw_after = helper.file('abcdefgh',password)
            for snapshot,raw in ((a,raw_before),(b,raw_after)):
                row = next(r for r in snapshot['inventories']['/data'] if r['path']=='access/3')
                row.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            for row in b['inventories']['/data']:
                if row['path'] in ('access/3','database.sqlite'):
                    row['mtimeNs']=str(int((window['start_epoch_seconds']+.2)*1e9))
            result=m.verify_ordinary_filesystem_delta(a,b,db_before,db_after,3,1,edit,window,raw_before,raw_after,helper.derive)
            self.assertEqual(len(result['access_files']),2)
            with self.assertRaisesRegex(ValueError,'inventory'):
                m.verify_ordinary_filesystem_delta(a,b,db_before,db_after,3,1,edit,window,raw_before,helper.file('87654321',password),helper.derive)
            damaged=deepcopy(db_after)
            db_fixture.change(damaged,'user','roles','changed')
            with self.assertRaisesRegex(ValueError,'Unrelated table'):
                m.verify_ordinary_filesystem_delta(a,b,db_before,damaged,3,1,edit,window,raw_before,raw_after,helper.derive)

if __name__=='__main__': unittest.main()
