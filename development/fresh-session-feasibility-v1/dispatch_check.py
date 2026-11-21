"""Reject unreviewed, unregistered or excess manual workflow runs before setup/build."""
import datetime,hashlib,json,os,pathlib,subprocess
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
def validate(study,dispatch,system,history,current_id,now):
 require(study['ready_for_application_dispatch'] is True,'both_harnesses_ready')
 require(study['gates']['G1_build_chain_audit']=='passed' and study['gates']['G2_both_adapters_observers_scorers']=='passed','review_gates')
 require(dispatch['status']=='reviewed' and system in dispatch['authorized_systems'],'authorized_system')
 require(dispatch.get('publication_status')=='authorized_sanitized_public_logs','publication_authorized')
 require(now<=datetime.datetime.fromisoformat(study['preparation_deadline_utc'].replace('Z','+00:00')),'preparation_deadline')
 require(dispatch['max_workflow_attempts']<=3 and dispatch['max_runner_minutes']==120,'bounded_job_plan')
 require(sum(r['run_attempt'] for r in history)<=dispatch['max_workflow_attempts'],'workflow_attempt_cap')
 current=[r for r in history if str(r['id'])==str(current_id)];require(len(current)==1 and current[0]['run_attempt']==1,'no_implicit_rerun')
 require(current[0]['display_title']=='Fresh-session feasibility / '+system,'current_system_identity')
 previous={str(r['id']):r for r in history if str(r['id'])!=str(current_id)}
 require(set(previous)==set(dispatch['previous_runs']),'all_prior_runs_registered')
 for identity,expected in dispatch['previous_runs'].items():
  actual=previous[identity]
  require(actual['status']=='completed' and actual['conclusion']==expected['conclusion'] and actual['run_attempt']==expected['run_attempt'],'prior_run_terminal_identity')
  require(actual['display_title']=='Fresh-session feasibility / '+expected['system'],'prior_system_identity')
 require(bool(dispatch['sha256']),'frozen_inputs_present')
 return True

def main():
 freeze=os.environ['FREEZE'];system=os.environ['STUDY_SYSTEM'];require(len(freeze)==40 and all(c in '0123456789abcdef' for c in freeze),'full_freeze_sha')
 require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==freeze,'exact_checkout')
 study=json.loads((ROOT/'manifests/fresh-session-feasibility-v1.json').read_text());dispatch=json.loads((ROOT/'manifests/fresh-session-dispatch-v1.json').read_text())
 # Refuse pending review without making network calls or installing anything.
 require(study['ready_for_application_dispatch'] is True and dispatch['status']=='reviewed','review_not_complete')
 repo='shravaniparsi/mixed-interface-study';metadata=json.loads(subprocess.check_output(['gh','api','repos/'+repo],text=True,timeout=20));require(metadata['private'] is False,'public_standard_runner_only')
 history=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/actions/workflows/fresh_session_feasibility_v1.yml/runs?per_page=100'],text=True,timeout=20))
 require(history['total_count']<=100,'complete_run_history')
 validate(study,dispatch,system,history['workflow_runs'],os.environ['GITHUB_RUN_ID'],datetime.datetime.now(datetime.timezone.utc))
 required={'.github/workflows/fresh_session_feasibility_v1.yml','protocol/fresh-session-feasibility-v1.md','manifests/fresh-session-ordinary-matrix-v1.json'}
 required|={str(p.relative_to(ROOT)) for p in (ROOT/'development/fresh-session-feasibility-v1').iterdir() if p.suffix in {'.py','.mjs','.php','.json'}}
 require(required<=set(dispatch['sha256']),'all_harness_inputs_frozen')
 for name,expected in dispatch['sha256'].items():
  p=ROOT/name;require(p.is_file() and not p.is_symlink(),'regular_frozen_input',path=name);require(hashlib.sha256(p.read_bytes()).hexdigest()==expected,'frozen_input_hash',path=name)
 print('Reviewed frozen harness, public repository and registered attempt budget verified.')
if __name__=='__main__':main()
