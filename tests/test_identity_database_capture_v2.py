import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_realworld_identity_extract_v1 import synthetic
from test_realworld_identity_measurements_v2 import failed_reads
from test_realworld_identity_database import fixture as database_fixture
from capture_identity_database_v2 import capture
from validate_identity_database_capture_v2 import validate
from realworld_identity_extract_v1 import extract as legacy_extract


class DatabaseCaptureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.root = Path(cls.temp.name); cls.cases = {}
        pinned = Path.home() / '.nvm/versions/node/v20.19.6/bin/node'
        node = str(pinned) if pinned.is_file() else shutil.which('node')
        for status in (200, 422, 500):
            directory = cls.root / str(status); directory.mkdir()
            raw, spec, fixture = failed_reads() if status == 500 else synthetic(username=None if status == 422 else 'u'*60, status=status, unknown=status != 422)
            db = directory / 'active.sqlite3'; database_fixture(db)
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE accounts_user SET bio='old'")
                conn.execute('DELETE FROM articles_article')
                for i, article in enumerate(fixture.values()):
                    conn.execute('INSERT INTO articles_article VALUES(?,?,?,?,?,?)',
                                 (10+i, article['slug'], article['title'], article['description'], article['body'], 7))
            traffic = []; request = None
            for event in raw['trace']:
                if event['type'] == 'request': request = event
                elif event['type'] == 'response': traffic.append({'request': request, 'response': event})
            for name, value in [('case.json', spec), ('fixture.json', fixture), ('traffic.json', traffic)]:
                (directory / name).write_text(json.dumps(value))
            (directory / 'mutate.py').write_text('''import json,sqlite3,sys
with sqlite3.connect(sys.argv[1]) as db:
 for key,value in json.loads(sys.stdin.read()).items():
  if key not in ('username','email','bio','image'):raise ValueError('Unexpected field')
  db.execute('UPDATE accounts_user SET '+key+'=?',(value,))
''')
            (directory / 'mock.mjs').write_text('''import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const rows=JSON.parse(readFileSync(new URL('./traffic.json',import.meta.url)));let index=0;
globalThis.fetch=async(url,options)=>{
 const row=rows[index++];assert.ok(row,'Unexpected request');
 assert.equal(new URL(url).pathname+new URL(url).search,row.request.path);assert.equal(options.method,row.request.method);
 const payload=options.body?JSON.parse(options.body):null;
 if(payload?.user?.password)payload.user.password='[REDACTED]';
 assert.deepEqual(payload,row.request.payload??null);
 if(row.request.method==='PUT' && [200,500].includes(row.response.status)){
  execFileSync(process.env.TEST_PYTHON,[fileURLToPath(new URL('./mutate.py',import.meta.url)),fileURLToPath(new URL('./active.sqlite3',import.meta.url))],{input:JSON.stringify(payload.user)});
 }
 const data=structuredClone(row.response.data);if(data.user)data.user.token='test-token';
 return new Response(JSON.stringify(data),{status:row.response.status,headers:{'content-type':'application/json'}});
};
process.on('exit',()=>{if(index!==rows.length)process.exitCode=1;});
''')
            import os
            cmd = [node, '--import', str(directory / 'mock.mjs'), str(ROOT / 'scripts/realworld_identity_case_v2.mjs'),
                   '--case', str(directory / 'case.json'), '--fixture', str(directory / 'fixture.json'),
                   '--continuation', 'api', '--output', str(directory / 'result.json'),
                   '--database', str(db), '--database-python', sys.executable, '--database-output', str(directory / 'backups')]
            result = subprocess.run(cmd, cwd=ROOT, env={**os.environ, 'TEST_PYTHON': sys.executable},
                                    capture_output=True, text=True, timeout=30)
            if result.returncode: raise AssertionError(result.stdout + result.stderr)
            emitted = json.loads((directory / 'result.json').read_text())
            cls.cases[status] = (emitted, directory / 'backups', fixture, spec)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def check(self, status):
        raw, directory, fixture, _ = self.cases[status]
        return validate(raw, directory, fixture)

    def test_actual_adapter_captures_same_branch_state_before_reads(self):
        for status in (200, 422, 500):
            with self.subTest(status=status):
                result = self.check(status)
                self.assertTrue(result['verified'])
                self.assertEqual(result['snapshots']['before_prefix']['user']['username'], 'pilotresearch')
                expected = 'pilotresearch' if status == 422 else 'u'*(60 if status == 200 else 61)
                self.assertEqual(result['snapshots']['after_prefix']['user']['username'], expected)
                self.assertFalse(result['restart_observed'])
        self.assertEqual(self.check(200)['snapshots']['after_continuation']['user']['bio'], 'Bio after meaningful continuation.')
        self.assertEqual(len(self.check(500)['snapshots']), 2)

    def test_old_semantic_classifier_is_not_repaired_by_database_capture(self):
        raw, _, fixture, spec = self.cases[500]
        self.assertEqual(legacy_extract(raw, spec, fixture)['kind'], 'missing_evidence')

    def test_accepted_trace_still_qualifies_with_additional_database_events(self):
        raw, _, fixture, spec = self.cases[200]
        self.assertEqual(legacy_extract(raw, spec, fixture)['kind'], 'unresolved_policy')

    def test_snapshot_overwrite_is_rejected(self):
        _, directory, _, _ = self.cases[500]
        before = (directory / 'after_prefix.sqlite3').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            capture(directory.parent / 'active.sqlite3', directory, 'after_prefix')
        self.assertEqual((directory / 'after_prefix.sqlite3').read_bytes(), before)

    def test_unregistered_checkpoint_rejected(self):
        _, directory, _, _ = self.cases[500]
        with self.assertRaises(ValueError): capture(directory.parent / 'active.sqlite3', directory, '../overwrite')

    def test_changed_snapshot_bytes_rejected(self):
        raw, directory, fixture, _ = self.cases[500]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'copy'; shutil.copytree(directory, target)
            with sqlite3.connect(target / 'after_prefix.sqlite3') as conn:
                conn.execute("UPDATE accounts_user SET username='other'")
            with self.assertRaisesRegex(ValueError, 'bytes differ'): validate(raw, target, fixture)

    def test_forged_projection_rejected(self):
        original, directory, fixture, _ = self.cases[500]; raw = deepcopy(original)
        raw['database_capture']['snapshots']['after_prefix']['projection']['user']['username'] = 'fake'
        with self.assertRaisesRegex(ValueError, 'projection differs'): validate(raw, directory, fixture)

    def test_readback_before_snapshot_rejected(self):
        original, directory, fixture, _ = self.cases[500]; raw = deepcopy(original)
        events = raw['trace']; checkpoint = [e for e in events if e['type'].startswith('database_snapshot_') and e['stage'] == 'after_prefix']
        raw['trace'] = [e for e in events if e not in checkpoint] + checkpoint
        for i, event in enumerate(raw['trace']): event['sequence'] = i+1
        with self.assertRaisesRegex(ValueError, 'immediately after'): validate(raw, directory, fixture)

    def test_missing_checkpoint_file_rejected(self):
        raw, directory, fixture, _ = self.cases[200]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'copy'; shutil.copytree(directory, target)
            (target / 'after_continuation.sqlite3').unlink()
            with self.assertRaisesRegex(ValueError, 'inventory differs'): validate(raw, target, fixture)

    def test_changed_source_hash_rejected(self):
        original, directory, fixture, _ = self.cases[500]; raw = deepcopy(original)
        raw['database_capture']['sources']['capture_identity_database_v2.py'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source differs'): validate(raw, directory, fixture)

    def ui_ordering_fixture(self):
        # Source-shaped ordering fixture only; this does not execute a browser.
        original, directory, fixture, _ = self.cases[200]; raw = deepcopy(original)
        raw['continuation_interface'] = 'ui'
        raw['observations']['api_continuation_started'] = False
        raw['observations']['ui_continuation_started'] = True
        for event in raw['trace']:
            if event.get('source') == 'api' and event.get('phase') == 'continuation': event['source'] = 'ui'
        at = next(i for i, e in enumerate(raw['trace']) if e['type'] == 'database_snapshot_started' and e['stage'] == 'after_continuation')
        raw['trace'].insert(at, {'type': 'capture_drain', 'phase': 'continuation', 'complete': True,
                                 'reason': 'before_database_snapshot'})
        for i, event in enumerate(raw['trace']): event['sequence'] = i+1
        return raw, directory, fixture

    def test_ui_ordering_fixture_requires_drain_before_backup(self):
        raw, directory, fixture = self.ui_ordering_fixture()
        self.assertTrue(validate(raw, directory, fixture)['verified'])
        next(e for e in raw['trace'] if e.get('reason') == 'before_database_snapshot')['complete'] = False
        with self.assertRaisesRegex(ValueError, 'not drained'): validate(raw, directory, fixture)

    def test_network_event_inside_checkpoint_rejected(self):
        original, directory, fixture, _ = self.cases[500]; raw = deepcopy(original)
        at = next(i for i, e in enumerate(raw['trace']) if e['type'] == 'database_snapshot_finished' and e['stage'] == 'after_prefix')
        raw['trace'].insert(at, {'type': 'request', 'source': 'state_probe', 'phase': 'failed_prefix_followup', 'path': '/api/user', 'method': 'GET'})
        for i, event in enumerate(raw['trace']): event['sequence'] = i+1
        with self.assertRaisesRegex(ValueError, 'during checkpoint'): validate(raw, directory, fixture)

    def test_unrelated_fixture_rejected(self):
        raw, directory, original, _ = self.cases[500]; fixture = deepcopy(original)
        fixture['base']['body'] = 'different fixture'
        with self.assertRaisesRegex(ValueError, 'fixture content differs'): validate(raw, directory, fixture)


if __name__ == '__main__': unittest.main()
