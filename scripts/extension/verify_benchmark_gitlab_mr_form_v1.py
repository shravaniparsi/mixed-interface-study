#!/usr/bin/env python3
"""Reconstruct read-only form findings, not write qualification."""
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();root=a.archive.resolve()
 run=json.loads((root/'run.json').read_text());assert run['databaseId']==44019120926 and run['status']=='completed' and run['conclusion']=='success' and run['headSha']=='068db7f5bfe5713fe7c630a98b0a73980f041571'
 folder=root/'gitlab-mr-form-v1-44019120926';row=json.loads((folder/'mr-form-inspection.json').read_text())
 assert (folder/'head.txt').read_text().strip()==run['headSha']
 assert (folder/'version.txt').read_text().strip()=='15.7.5'
 assert 'sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0' in (folder/'image-identity.txt').read_text()
 assert row['inspection_completed'] and row['browser_cleanup_confirmed'] and not row['business_writes_permitted'] and row['scientific_cases_executed']==0
 assert row['actor']=={'id':2330,'username':'byteblaze'}
 assert all(r['status']==200 for r in row['api_reads'])
 assert len(row['forms'])==1 and row['forms'][0]['label']=='bound_creation_form'
 fields={f['id']:f for f in row['forms'][0]['fields'] if f.get('id')}
 defaults={'title':fields['merge_request_title']['value'],'description':fields['merge_request_description']['value'],'remove_source_branch_checked':fields['merge_request_force_remove_source_branch']['checked'],'squash_checked':fields['merge_request_squash']['checked']}
 job=run['jobs'][0];parse=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
 result={'kind':'benchmark_gitlab_mr_form_results_v1','run_id':44019120926,'inspection_completed':True,'ordinary_write_triple_qualified':False,'scientific_cases_executed':0,'job_seconds':(parse(job['completedAt'])-parse(job['startedAt'])).total_seconds(),'paid_model_calls':0,'branch_identities':row['branch_identities'],'existing_matching_mrs':row['existing_matching_mrs'],'observed_form_defaults':defaults,'reviewer_dropdown_inspected':any(f['label']=='reviewer_dropdown' for f in row['forms']),'reviewer_label_present':any(f.get('text')=='Reviewer' for f in row['forms'][0]['fields']),'blocked_local_requests':[r for r in row['blocked_requests'] if not r['external']],'blocked_external_request_count':sum(r['external'] for r in row['blocked_requests']),'interpretation':'Existing open matching MR prevents assuming an absent-target precondition. No creation/rejection or reviewer update was tested. No defect or task impossibility is established.','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}}
 target=ROOT/'manifests/benchmark-gitlab-mr-form-results-v1.json'
 if a.verify:assert json.loads(target.read_text())==result
 else:target.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
