#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];D=Path('/private/tmp/development-starter-docs-v1')
OUT=ROOT/'manifests/development-starter-docs-v1.json'
def build():
    schedule=json.loads((ROOT/'manifests/development-starter-docs-schedule-v1.json').read_text())
    partition=(ROOT/'manifests/project-family-partition-v1.json').read_bytes();assert hashlib.sha256(partition).hexdigest()==schedule['partition_sha256']
    allowed={r['full_name'] for r in json.loads(partition)['rows'] if r['partition']=='development'}
    raw=(D/'collection.json').read_bytes();c=json.loads(raw);assert len(c['rows'])==len(schedule['files'])==2
    rows=[]
    assessments=[dict(category='frontend_setup_and_route_guard_description',source_lines=[2,4,17,18],
                     assessment='Named route guards describe access/navigation behavior; no explicit selected signup/login field-validation obligation established.'),
                 dict(category='server_setup_and_authentication_configuration_description',source_lines=[4,72,91],
                     assessment='Token-expiry default and password-hashing description are explicit but not selected signup/login field-validation labels.')]
    for index,(s,r) in enumerate(zip(schedule['files'],c['rows']),1):
        assert s['full_name'] in allowed and all(s[k]==r[k] for k in s)
        assert r['status']=='verified' and r['index']==index
        content=(D/(str(index)+'.txt')).read_bytes()
        assert len(content)==r['bytes'] and hashlib.sha256(content).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()==r['blob_sha']
        rows.append(dict(r,lines_reviewed=len(content.decode().splitlines()),manual_assessment=assessments[index-1]))
    return dict(kind='development_starter_documentation_followup',freeze='dcb2a35',rows=rows,
        collection_sha256=hashlib.sha256(raw).hexdigest(),elapsed_seconds=c['elapsed_seconds'],
        candidate_behavioral_statements=[
          dict(file_index=2,line=72,subject='token_expiry',documented_default_seconds=600,
               status='candidate_only_not_selected_validation_label',limits=['configuration_and_revision_compatibility_unverified','no_runtime_or_independent_authorship_verification']),
          dict(file_index=2,line=91,subject='password_hashing',documented_mechanism='bcrypt',
               status='descriptive_storage_statement_not_selected_validation_label',limits=['no_field_constraints_or_exhaustive_input_semantics'])],
        documentation_alignment=dict(frontend_cli_generation='8.3.21',frontend_cli_setup='8.3.21',
            prior_root_cli_setup='9.1.3',scope='README declarations differ; actual runtime was not installed or checked'),
        root_link_alias_equivalence_verified=False,linked_pages_read=False,
        semantic_review='single_assistant_full_document_review_not_independent_adjudication',
        resolved_selected_operation_labels=0,independent_evaluation_cases=0,reserved_source_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Two pinned documentation files and recorded scope assessments verified')
    else:OUT.write_text(text)
