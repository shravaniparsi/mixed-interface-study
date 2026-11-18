"""Real OpenSSL roundtrip on tiny synthetic files; no application evidence."""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import seal_nginx_evidence_v1 as m

class SealingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.key=cls.root/'test-key.pem';cls.cert=cls.root/'test-cert.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:3072','-noenc','-keyout',str(cls.key),'-out',str(cls.cert),'-subj','/CN=Synthetic Test','-days','1'],check=True,capture_output=True,timeout=30)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_authenticated_roundtrip_preserves_private_files_and_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'private';source.mkdir();raw=b'only-synthetic-secret\x00payload'
            (source/'state.bin').write_bytes(raw);os.symlink('state.bin',source/'link')
            report=m.seal(source,self.cert,root/'public')
            self.assertEqual(set(p.name for p in (root/'public').iterdir()),{'private-evidence.cms','sealed-evidence.json'})
            cipher=root/'public/private-evidence.cms'
            self.assertNotIn(raw,cipher.read_bytes())
            decrypted=subprocess.run(['openssl','cms','-decrypt','-binary','-inform','DER','-in',str(cipher),'-recip',str(self.cert),'-inkey',str(self.key)],check=True,capture_output=True,timeout=15).stdout
            self.assertEqual(hashlib.sha256(decrypted).hexdigest(),report['archive_sha256'])
            with tarfile.open(fileobj=io.BytesIO(decrypted),mode='r:gz') as archive:
                self.assertEqual(archive.extractfile('evidence/state.bin').read(),raw)
                self.assertTrue(archive.getmember('evidence/link').issym())
                inventory=json.load(archive.extractfile('_archive-inventory.json'))
                self.assertEqual(inventory['total_file_bytes'],len(raw))
            corrupted=bytearray(cipher.read_bytes());corrupted[-1]^=1;(root/'bad.cms').write_bytes(corrupted)
            result=subprocess.run(['openssl','cms','-decrypt','-binary','-inform','DER','-in',str(root/'bad.cms'),'-recip',str(self.cert),'-inkey',str(self.key)],capture_output=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
    def test_nested_output_and_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'private';source.mkdir()
            for out in (source/'public',source):
                with self.assertRaises(ValueError):m.seal(source,self.cert,out)
            out=Path(directory)/'existing';out.mkdir()
            with self.assertRaises(ValueError):m.seal(source,self.cert,out)
    def test_external_symlink_is_retained_without_following(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'private';source.mkdir();(root/'outside').write_bytes(b'not archived')
            os.symlink('../outside',source/'link');rows,total=m.inventory(source)
            self.assertEqual(total,0);self.assertEqual(rows[-1]['target'],'../outside')
    def test_special_files_and_reserved_name_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);os.mkfifo(root/'fifo')
            with self.assertRaises(ValueError):m.inventory(root)
            (root/'fifo').unlink();(root/'_archive-inventory.json').write_text('conflict')
            with self.assertRaises(ValueError):m.inventory(root)

if __name__=='__main__':unittest.main()
