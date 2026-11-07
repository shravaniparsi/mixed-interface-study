"""Summarize recorded PetClinic paired branches without assigning defect labels."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
if args.output.exists():
    parser.error('--output exists; use a new report path')
summary = json.loads((args.results / 'summary.json').read_text())
registry_path = args.results / 'registered-candidates.json'
assert hashlib.sha256(registry_path.read_bytes()).hexdigest() == summary['registry_sha256']
registry = json.loads(registry_path.read_text())
candidates = {c['id']: c for c in registry['candidates']}
rows = []
for pair in summary['pairs']:
    case_id = pair['candidate_id']
    api = json.loads((args.results / (case_id + '-api_semantic.json')).read_text())
    ui = json.loads((args.results / (case_id + '-fresh_ui.json')).read_text())
    api_puts = [e['request'] for e in api['trace'] if e['method'] == 'PUT']
    ui_puts = [e['request'] for e in ui['trace'] if e['method'] == 'PUT']
    if api['status'] == ui['status'] == 'prefix_rejected':
        observation = 'prefix_rejected_before_either_continuation'
    elif api['status'] == ui['status'] == 'continuation_passed' and pair['final_state_equal']:
        observation = 'both_continuations_passed_same_final_state'
    elif api['status'] == 'continuation_passed' and ui['status'] == 'ui_blocked':
        observation = 'api_edit_passed_fresh_ui_edit_blocked_requires_adjudication'
    else:
        observation = 'other_requires_investigation'
    elapsed = lambda d: (datetime.datetime.fromisoformat(d['finished_at'].replace('Z', '+00:00')) - datetime.datetime.fromisoformat(d['started_at'].replace('Z', '+00:00'))).total_seconds()
    rows.append({**pair, 'input_kind': candidates[case_id]['kind'], 'prefix_http_status': api.get('prefix_status'), 'observation': observation,
                 'fresh_ui_read_observed': ui.get('fresh_ui_read_observed'),
                 'continuation_payloads_equal': api_puts == ui_puts if api_puts and ui_puts else None,
                 'api_seconds_including_reset': elapsed(api), 'ui_seconds_including_reset': elapsed(ui),
                 'api_start_seconds': api.get('backend_start_seconds'), 'ui_start_seconds': ui.get('backend_start_seconds'),
                 'external_requests_blocked': len(api.get('blocked_external_requests', [])) + len(ui.get('blocked_external_requests', [])),
                 'page_errors': len(api.get('page_errors', [])) + len(ui.get('page_errors', []))})
report = {'subject': 'petclinic', 'kind': 'development_slice_observations', 'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'source_directory': str(args.results), 'registry_sha256': summary['registry_sha256'], 'runner_sha256': summary['runner_sha256'],
          'registered_candidates': len(candidates), 'completed_candidate_pairs': len(rows), 'executed_branches': len(summary['branches']),
          'template_count': len(set(r['template'] for r in rows)), 'repetitions_in_this_run': 1,
          'observations': dict(Counter(r['observation'] for r in rows)),
          'prefix_status_by_candidate': dict(Counter(str(r['prefix_http_status']) for r in rows)),
          'all_initial_states_match': all(r['initial_state_equal'] for r in rows),
          'all_post_prefix_states_match': all(r['post_prefix_state_equal'] for r in rows),
          'application_source_modified': False,
          'interpretation': 'Observed development cases, not a defect-prevalence estimate, selector comparison, or agent experiment. UI/API discrepancies require requirement-based adjudication; common prefix rejection is not UI continuation value.',
          'rows': rows}
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('x') as stream:
    stream.write(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['completed_candidate_pairs', 'executed_branches', 'observations', 'all_initial_states_match', 'all_post_prefix_states_match']}))
