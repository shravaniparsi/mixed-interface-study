#!/usr/bin/env python3
"""Reconstruct packaged-source identity without claiming live API behavior."""
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44024863535
HEAD='cb07b42f771b83aadf5b20488a64ccb430a305a8'
SELECTED=['app/models/merge_request.rb','app/services/merge_requests/base_service.rb','app/views/shared/issuable/form/_metadata.html.haml','app/views/shared/issuable/form/_metadata_issuable_reviewer.html.haml']
def reconstruct(root):
 run=json.loads((root/'run.json').read_text());assert run['databaseId']==RUN and run['status']=='completed' and run['headSha']==HEAD
 jobs=[j for j in run['jobs'] if j['name']=='inspect'];assert len(jobs)==1;job=jobs[0];assert job['status']=='completed'
 parse=lambda t:datetime.fromisoformat(t.replace('Z','+00:00'))
 folder=root/f'gitlab-mr-source-inspection-{RUN}';extracted=folder/'extracted'
 upstream=json.loads((ROOT/'evidence/gitlab-mr-form-source-v1.json').read_text());expected={f['path']:f['sha256'] for f in upstream['sources']}
 registration=json.loads((ROOT/'manifests/benchmark-gitlab-mr-source-registration-v1.json').read_text());assert hashlib.sha256((ROOT/'evidence/gitlab-mr-form-source-v1.json').read_bytes()).hexdigest()==registration['source_sha256']['evidence/gitlab-mr-form-source-v1.json']
 comparisons=[]
 for name in SELECTED:
  p=extracted/name;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
  comparisons.append({'path':name,'present':p.exists(),'expected_sha256':expected[name],'actual_sha256':actual,'matches_upstream':actual==expected[name]})
 statepath=folder/'container-state.json';state=json.loads(statepath.read_text()) if statepath.exists() else None
 never_started=bool(state and state.get('Status')=='created' and state.get('Running') is False and state.get('StartedAt','').startswith('0001-01-01'))
 read=lambda name:(folder/name).read_text().strip() if (folder/name).exists() else None
 package=read('extracted/package-version-manifest.txt');edition_line=package.splitlines()[0] if package else None
 identity=read('image-identity.txt') or '';ee=extracted/'ee/app/models/ee/merge_request.rb'
 identity_checks={'frozen_head':read('head.txt')==HEAD,'image_digest':'sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0' in identity,'version':read('extracted/VERSION')=='15.7.5','revision':bool(read('extracted/REVISION') and upstream['commit'].startswith(read('extracted/REVISION'))),'ce_package':edition_line=='gitlab-ce 15.7.5','never_started':never_started}
 return {'kind':'benchmark_gitlab_mr_packaged_source_results_v1','run_id':RUN,'job_conclusion':job['conclusion'],'job_seconds':(parse(job['completedAt'])-parse(job['startedAt'])).total_seconds(),'scientific_cases_executed':0,'paid_model_calls':0,'identity_checks':identity_checks,'packaged_source_identity_established':all(identity_checks.values()) and all(c['matches_upstream'] for c in comparisons),'source_comparisons':comparisons,'package_edition_line':edition_line,'ee_model_copied':ee.exists(),'ee_copy_status_lines':[l for l in (read('extraction-status.tsv') or '').splitlines() if l.startswith('ee/')],'extraction_errors':read('extraction-errors.log'),'live_behavior_tested':False,'interpretation':'Matching bytes establish packaged upstream reviewer logic. Copy failure alone is not proof every runtime override is absent; no live request was executed. A shared backend capability limit is not incremental interface evidence.','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();v=reconstruct(a.archive.resolve());dest=ROOT/'manifests/benchmark-gitlab-mr-source-results-v1.json'
 if a.verify:assert json.loads(dest.read_text())==v
 else:dest.write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({k:v for k,v in v.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
