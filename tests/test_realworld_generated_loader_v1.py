"""Synthetic contract bundles and adversarial terminal decisions; no live evidence."""
from copy import deepcopy
from pathlib import Path
import json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_generated_bindings_v1 import plan,case_for
from realworld_generated_loader_v1 import load,sha,SOURCES
from realworld_generated_terminal_v1 import combine,classify
from test_realworld_oracle_components import positive


def put(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))


def bundle(root):
    raw,run,spec,_=positive(generated=True)
    job=next(j for j in plan()['jobs'] if spec['case_id'] in j['pair']['case_ids'].values())
    put(root/'job.json',job);(root/'fixture.bin').write_bytes(b'synthetic reset bytes; not an application database')
    for source in SOURCES:
        p=root/'sources'/source;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/source).read_bytes())
    for channel in ('api','ui'):
        raw,run,spec,_=positive(consumer=channel,generated=True)
        run.update(cleanup_confirmed=True,reset_sha256=sha(root/'fixture.bin'))
        for name,value in [('case.json',spec),('raw.json',raw),('run.json',run)]:put(root/channel/name,value)
        (root/channel/'reset.bin').write_bytes((root/'fixture.bin').read_bytes())
    seal(root)
    return job


def seal(root):
    put(root/'certificate.json',{'kind':'offline_generated_evidence_contract_v1','evidence_origin':'synthetic_contract_fixture',
        'runtime_dispatch_qualified':False,'files_sha256':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and p.name!='certificate.json'}})


class LoaderTests(unittest.TestCase):
    def test_synthetic_bundle_stays_incomplete_without_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle(root);value=load(root)
            self.assertEqual(value['terminal']['kind'],'missing_evidence')
            self.assertFalse(value['execution_attested']);self.assertFalse(value['runtime_dispatch_qualified'])

    def test_changed_raw_and_resealed_foreign_case_source_reset_rejected(self):
        for mode in ('raw','case','source','reset','extra','escape','promotion'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d);bundle(root)
                if mode=='raw':(root/'api/raw.json').write_text('{}')
                elif mode=='case':put(root/'api/case.json',{})
                elif mode=='source':(root/'sources'/SOURCES[0]).write_text('{}')
                elif mode=='reset':(root/'api/reset.bin').write_bytes(b'foreign reset')
                elif mode=='extra':(root/'extra.json').write_text('{}')
                elif mode=='escape':
                    (root/'api/raw.json').unlink();(root/'api/raw.json').symlink_to(ROOT/'manifests/realworld-generated-bindings-v1.json')
                else:
                    v=json.loads((root/'certificate.json').read_text());v['runtime_dispatch_qualified']=True;put(root/'certificate.json',v)
                if mode in ('case','source','reset'):seal(root)
                with self.assertRaises(ValueError):load(root)

    def test_cleanup_timeout_and_interruption_precedence(self):
        job=plan()['jobs'][0]
        self.assertEqual(classify(job,'api',{}, {'cleanup_confirmed':False,'timed_out':True})['kind'],'cleanup_unconfirmed')
        self.assertEqual(classify(job,'api',{}, {'cleanup_confirmed':True,'timed_out':True})['kind'],'case_timeout')
        self.assertEqual(classify(job,'api',{}, {'cleanup_confirmed':True,'interrupted':True})['kind'],'interrupted')

    def test_terminal_matrix_on_explicit_synthetic_reduced_components(self):
        def branch(kind,accepted=True,mismatch=False):
            return {'kind':kind,'components':{'accepted_prefix':accepted,'components':{
                'assigned_api_continuation':{'mismatch_observed':mismatch},
                'assigned_native_continuation':{'mismatch_observed':mismatch}}}}
        job=plan()['jobs'][0];evidence={'synthetic':'0'*64}
        cases=[('clean_observation','clean_observation',True,True,'clean_observation'),
               ('matched_rejection','matched_rejection',False,True,'matched_rejection'),
               ('unresolved_policy','unresolved_policy',True,True,'unresolved_policy'),
               ('completed_mismatch','clean_observation',True,True,'completed_mismatch'),
               ('clean_observation','clean_observation',True,False,'incomparable_observation'),
               ('missing_evidence','clean_observation',True,True,'missing_evidence')]
        for a,b,accepted,gate,expected in cases:
            with self.subTest(expected=expected):
                value=combine(job,{'api':branch(a,accepted,a=='completed_mismatch'),'ui':branch(b,accepted)}, {'same_reset':gate},evidence)
                self.assertEqual(value['kind'],expected)
        shared=branch('completed_mismatch')
        shared['components']['components']['shared_final_native_read']={'mismatch_observed':True,'checks':[{'id':'shared_render','passed':False,'scope':'synthetic'}]}
        shared_value=combine(job,{'api':shared,'ui':branch('clean_observation')},{'same_reset':True},evidence)
        self.assertFalse(shared_value['outcome']['channel_discrepancy'])
        self.assertTrue(shared_value['outcome']['check_failure'])
        self.assertEqual(shared_value['outcome']['observation_signature']['checks']['api']['shared_final_native_read'],[['shared_render',False,'synthetic']])
        value=combine(job,{'api':branch('clean_observation'),'ui':branch('matched_rejection',False)}, {'same_reset':True},evidence)
        self.assertEqual(value['kind'],'incomparable_observation')
