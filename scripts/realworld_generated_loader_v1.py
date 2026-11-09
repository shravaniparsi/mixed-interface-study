"""File-backed offline contract loader. Certificates are not execution attestation."""
import hashlib,json
from pathlib import Path
from realworld_generated_bindings_v1 import ROOT,POOL,plan,case_for
from mixed_interface.repetition import require
from realworld_generated_terminal_v1 import compare
SOURCES=(POOL,'scripts/realworld_generated_bindings_v1.py','scripts/realworld_generated_terminal_v1.py',
         'scripts/realworld_generated_loader_v1.py','scripts/summarize_realworld_oracle_components.py',
         'scripts/realworld_generated_case.mjs','scripts/response_capture.mjs','scripts/realworld_integrity.mjs',
         'src/mixed_interface/evaluation.py','src/mixed_interface/repetition.py','src/mixed_interface/terminal_outcomes.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(directory):
    root=Path(directory).resolve()
    def path(name):
        require(isinstance(name,str) and not Path(name).is_absolute(),'Absolute evidence path')
        p=(root/name).resolve();require(p.is_relative_to(root) and p.is_file(),'Missing or escaping evidence path')
        return p
    def read(name):return json.loads(path(name).read_bytes())
    certificate=read('certificate.json')
    require(certificate.get('kind')=='offline_generated_evidence_contract_v1','Unsupported certificate')
    require(certificate.get('evidence_origin')=='synthetic_contract_fixture','Only synthetic contract bundles supported before supervisor qualification')
    require(certificate.get('runtime_dispatch_qualified') is False,'Runtime qualification cannot be self-declared')
    job=read('job.json');require(job in plan()['jobs'],'Altered job')
    expected={'job.json','fixture.bin'}|{'sources/'+s for s in SOURCES}
    expected|={c+'/'+n for c in ('api','ui') for n in ('case.json','raw.json','run.json','reset.bin')}
    hashes=certificate['files_sha256'];require(set(hashes)==expected,'Certificate file inventory differs')
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual==expected|{'certificate.json'},'Unexpected or missing bundle file')
    for name,h in hashes.items():require(sha(path(name))==h,'Evidence bytes changed: '+name)
    for source in SOURCES:require(sha(path('sources/'+source))==sha(ROOT/source),'Pinned source differs: '+source)
    fixture_sha=sha(path('fixture.bin'));branches={}
    for channel in ('api','ui'):
        spec=case_for(job,channel);require(read(channel+'/case.json')==spec,'Executed case differs')
        raw=read(channel+'/raw.json');run=read(channel+'/run.json')
        require(run.get('case_id')==spec['case_id'] and run.get('route')==[o['interface'] for o in spec['operations']],'Runner identity differs')
        require(run.get('reset_sha256')==sha(path(channel+'/reset.bin'))==fixture_sha,'Independent reset bytes differ')
        require(type(run.get('cleanup_confirmed')) is bool and type(run.get('exit_code')) is int,'Missing supervisor fields')
        branches[channel]=(raw,run)
    result=compare(job,branches,{**hashes,'certificate.json':sha(path('certificate.json'))})
    result.update(evidence_origin=certificate['evidence_origin'],new_application_executions=0,
                  source_qualified_bytes=True,execution_attested=False)
    return result
