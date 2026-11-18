"""Real authenticated tiny synthetic archive recovery, no application data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import seal_nginx_evidence_v1 as seal
import verify_nginx_sealed_evidence_v1 as m

class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory();cls.root=Path(cls.temporary.name)
        cls.key=cls.root/'key.pem';cls.cert=cls.root/'cert.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:3072','-noenc','-keyout',str(cls.key),'-out',str(cls.cert),'-subj','/CN=Synthetic Recovery','-days','1'],check=True,capture_output=True,timeout=30)
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def fixture(self,root):
        source=root/'private';source.mkdir();(source/'data.json').write_text('{"synthetic":true}')
        seal.seal(source,self.cert,root/'public')
        return (root/'public/private-evidence.cms',root/'public/sealed-evidence.json',self.cert,self.key,root/'recovered')
    def test_recovers_and_verifies_every_member_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);args=self.fixture(root);report=m.recover(*args)
            self.assertEqual(report['members_verified'],2);self.assertEqual(report['members_extracted'],0)
            self.assertEqual(set(p.name for p in args[-1].iterdir()),{'authenticated-evidence.tar.gz','recovery-verification.json'})
    def test_failed_authentication_discards_even_partial_plaintext(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);args=self.fixture(root)
            def fail(command,**kwargs):
                kwargs['stdout'].write(b'unauthenticated partial')
                raise subprocess.CalledProcessError(1,command)
            with patch.object(m.subprocess,'run',side_effect=fail):
                with self.assertRaises(subprocess.CalledProcessError):m.recover(*args)
            self.assertEqual(list(args[-1].iterdir()),[])
    def test_wrong_public_digest_fails_before_decryption(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);args=self.fixture(root);report=json.loads(args[1].read_text());report['ciphertext_sha256']='0'*64;args[1].write_text(json.dumps(report))
            with patch.object(m.subprocess,'run') as called:
                with self.assertRaisesRegex(ValueError,'identity'):m.recover(*args)
                called.assert_not_called()
    def test_archive_inventory_mismatch_is_not_published_as_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);args=self.fixture(root)
            with patch.object(m,'audit_archive',side_effect=ValueError('altered inventory')):
                with self.assertRaises(ValueError):m.recover(*args)
            self.assertEqual(list(args[-1].iterdir()),[])

if __name__=='__main__':unittest.main()
