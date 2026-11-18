"""Synthetic coordinator binding tests: decoding never establishes identity."""
import base64
import hashlib
import json
import unittest
from verify_seatsurfing_actor_state_v1 import bind_actor_inputs


class ActorBinding(unittest.TestCase):
    def setUp(self):
        self.uuid='00000000-0000-4000-8000-000000000001'
        claims=base64.urlsafe_b64encode(json.dumps({'userID':self.uuid,'sid':self.uuid}).encode()).decode().rstrip('=')
        self.storage={'origins':[{'origin':'http://127.0.0.1:8080','localStorage':[{'name':'accessToken','value':'header.'+claims+'.signature'},{'name':'refreshToken','value':self.uuid}]}]}
        self.key=b'public-key-fixture';self.build=b'build-fixture'
        self.provision={'public_key_sha256':hashlib.sha256(self.key).hexdigest(),'build_report_sha256':hashlib.sha256(self.build).hexdigest()}
    def bind(self):
        raw=json.dumps(self.storage).encode()
        return bind_actor_inputs(raw,hashlib.sha256(raw).hexdigest(),self.key,self.provision,self.build)
    def test_bound_decoded_claims_only_select_original_read_only_query(self):
        values,claims,query=self.bind()
        self.assertEqual(claims['userID'],self.uuid);self.assertEqual(values['refreshToken'],self.uuid)
        self.assertIn('READ ONLY',query)
        self.assertNotIn('identityConsistent',claims)
    def test_changed_provisioned_key_or_build_rejected(self):
        self.key=b'other'
        with self.assertRaisesRegex(ValueError,'Public key'):self.bind()
        self.key=b'public-key-fixture';self.build=b'other'
        with self.assertRaisesRegex(ValueError,'another build'):self.bind()
    def test_duplicate_storage_key_rejected(self):
        self.storage['origins'][0]['localStorage'].append({'name':'refreshToken','value':'other'})
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.bind()
    def test_original_storage_hash_required(self):
        with self.assertRaisesRegex(ValueError,'hash'):bind_actor_inputs(b'{}','wrong',self.key,self.provision,self.build)
    def test_unverified_selector_cannot_inject_sql(self):
        self.storage['origins'][0]['localStorage'][1]['value']="'; DELETE FROM users; --"
        with self.assertRaisesRegex(ValueError,'UUID'):self.bind()




# The coordinator tests below use mocked database/Node boundaries. The real
# cryptographic file-entry-point test lives in seatsurfing-actor.test.mjs.

class CoordinatorBinding(unittest.TestCase):
    setUp = ActorBinding.setUp
    def test_database_and_verifier_bindings(self):
        import os
        from pathlib import Path
        import subprocess
        import tempfile
        from unittest.mock import patch
        import verify_seatsurfing_actor_state_v1 as module
        for altered in [None, 'database_id', 'raw_data', 'verifier_hash']:
            with self.subTest(altered=altered), tempfile.TemporaryDirectory(prefix='seatsurfing-actor-binding-') as temp:
                root=Path(temp); build=root/'build.json';build.write_text('{"study_commit":"commit"}')
                key=root/'public.pem';key.write_bytes(self.key)
                storage=root/'storage.json';storage.write_text(json.dumps(self.storage))
                provision=root/'provision.json';provision.write_text(json.dumps({
                    'status':'isolated_fixture_ready_browser_and_actor_unqualified',
                    'public_key_sha256':hashlib.sha256(self.key).hexdigest(),
                    'build_report_sha256':hashlib.sha256(build.read_bytes()).hexdigest(),
                    'application_container_id':'app','database_container_id':'pg'}))
                query=module.actor_query(self.uuid,self.uuid,self.uuid)
                acquired={'query_sha256':hashlib.sha256(query.encode()).hexdigest(),
                          'build_report_sha256':hashlib.sha256(build.read_bytes()).hexdigest(),
                          'raw_result':'{}','raw_result_sha256':hashlib.sha256(b'{}').hexdigest(),
                          'data':{},'application_container_id':'app','database_container_id':'pg'}
                if altered=='database_id':acquired['database_container_id']='other'
                if altered=='raw_data':acquired['data']={'changed':True}
                def execute(argv, **kwargs):
                    raw=Path(argv[-2]).read_bytes()
                    Path(argv[-1]).write_text(json.dumps({'status':'actor_identity_verified',
                        'inputSha256':'wrong' if altered=='verifier_hash' else hashlib.sha256(raw).hexdigest(),
                        'result':{'identityConsistent':True,'continuity':{'fixture':True}}}))
                    return subprocess.CompletedProcess(argv,0,b'',b'')
                with patch.dict(os.environ,GITHUB_ACTIONS='true',GITHUB_REPOSITORY='shravaniparsi/mixed-interface-study',GITHUB_SHA='commit'), patch.object(module,'bind_build'), patch.object(module,'capture_actor_database',return_value=acquired), patch.object(module.subprocess,'run',side_effect=execute) as run:
                    report=module.verify_actor_state(build_report=build,provision_report=provision,
                        storage=storage,storage_sha256=hashlib.sha256(storage.read_bytes()).hexdigest(),
                        events=[],public_key=key,organization_id=self.uuid,private_directory=root/'evidence')
                self.assertEqual(report['status'],'actor_acquisition_and_identity_verified' if altered is None else 'actor_verification_unavailable')
                self.assertEqual(run.call_count,0 if altered in ['database_id','raw_data'] else 1)


if __name__=='__main__':unittest.main()
