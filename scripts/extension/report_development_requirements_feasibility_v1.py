#!/usr/bin/env python3
"""Verify collected files and retain explicit manual documentation assessments.

Hashes/coverage are machine-checked; semantic assessments are not independently
certified by this reporter. No keyword classifier substitutes for document review.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=Path('/private/tmp/development-requirements-feasibility-v1')
OUT=ROOT/'manifests/development-requirements-feasibility-v1.json'
ASSESSMENTS={
1:dict(category='build_setup_and_external_navigation',selected_operations=['registration','admin_user_create','admin_user_update'],
       navigation_lines=[6],finding='No scoped field-validation requirement for the selected operations in this README.',
       relevant_scope='The README identifies JHipster 7.9.3 generation and a linked Mini-Book; neither linked document was read.'),
2:dict(category='setup_general_authorization_and_navigation',selected_operations=['signup','login'],
       navigation_lines=[57,58,63,128,129],finding='General role/access examples do not specify selected signup/login field-validation obligations.',
       relevant_scope='Frontend/server links name an older repository URL and master paths; target equivalence and revision alignment remain unverified.'),
3:dict(category='course_navigation',selected_operations=['employee_create','employee_update'],
       navigation_lines=[43,48,56],finding='Tutorial titles and video links do not themselves specify employee field constraints or post-operation obligations.',
       relevant_scope='No video or transcript was retrieved; normative content and revision compatibility are unknown.'),
4:dict(category='generated_build_setup_and_navigation',selected_operations=['registration'],
       navigation_lines=[2],finding='No scoped registration field-validation requirement in this README.',
       relevant_scope='The README identifies JHipster 4.14.3 and links archived documentation; links were not followed.')}
def build():
    schedule=json.loads((ROOT/'manifests/development-requirements-feasibility-schedule-v1.json').read_text())
    partition=(ROOT/'manifests/project-family-partition-v1.json').read_bytes()
    assert hashlib.sha256(partition).hexdigest()==schedule['partition_sha256']
    allowed={r['full_name'] for r in json.loads(partition)['rows'] if r['partition']=='development'}
    raw=(D/'collection.json').read_bytes();c=json.loads(raw)
    assert len(c['rows'])==len(schedule['files'])==4
    rows=[]
    for index,(s,r) in enumerate(zip(schedule['files'],c['rows']),1):
        assert s['full_name'] in allowed and all(r[k]==s[k] for k in s)
        assert r['index']==index and r['status']=='verified'
        content=(D/(str(index)+'.txt')).read_bytes()
        assert len(content)==r['bytes'] and hashlib.sha256(content).hexdigest()==r['sha256']
        assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()==r['blob_sha']
        lines=content.decode().splitlines();a=ASSESSMENTS[index]
        assert all(1<=n<=len(lines) for n in a['navigation_lines'])
        rows.append(dict(r,lines_reviewed=len(lines),manual_assessment=a,
                         resolved_selected_operation_labels=0,linked_content_read=False))
    return dict(kind='development_readme_requirement_feasibility',freeze='90ba052',rows=rows,
        collection_sha256=hashlib.sha256(raw).hexdigest(),elapsed_seconds=c['elapsed_seconds'],
        semantic_review='single_assistant_full_document_review_not_independent_adjudication',
        resolved_selected_operation_labels=0,reserved_source_reads=0,independent_evaluation_cases=0,
        interpretation='No suitable selected-operation labels established from these four root documents; wider documentation availability remains unknown.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Four document hashes, coverage and recorded manual assessments verified')
    else:OUT.write_text(text)
