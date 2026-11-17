#!/usr/bin/env python3
"""Qualification requires all three fresh paths; failures are not scientific defects."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANCHES = ['native_native', 'api_native', 'api_api']


def qualify(runtime, results, registration):
    problems = []
    if runtime.get('status') != 'completed':problems.append('runtime_incomplete')
    rows = runtime.get('branches', [])
    if [r.get('branch') for r in rows] != BRANCHES:problems.append('schedule_incomplete')
    if set(results) != set(BRANCHES):problems.append('branch_results_missing')
    cids = [cid for r in rows for cid in r.get('containers', {}).values()]
    if len(cids) != 6 or len(set(cids)) != 6:problems.append('fresh_container_evidence_missing')
    projections = []
    for row in rows:
        branch = row['branch'];r = results.get(branch, {})
        if not row.get('ready') or row.get('node_returncode') != 0 or row.get('cleanup') != {'owncloud': 0, 'collabora': 0, 'network': 0}:problems.append(branch + ':runtime_not_qualified')
        if r.get('branch') != branch or not r.get('passed') or r.get('stage') != 'completed' or r.get('error'):problems.append(branch + ':assertions_incomplete')
        state = r.get('producer', {})
        if state.get('sha256') != registration['payload_sha256'] or state.get('length') != registration['payload_bytes'] or state.get('path') != registration['destination']:problems.append(branch + ':wrong_producer')
        if r.get('final_file') != state or r.get('public_download_sha256') != registration['payload_sha256']:problems.append(branch + ':preservation_or_public_access_failed')
        share = r.get('share', {})
        if share.get('path') != registration['destination'] or share.get('share_type') != 3 or share.get('permissions') != 1 or share.get('uid_owner') != 'theagentcompany' or share.get('share_with') not in (None, '') or share.get('expiration') not in (None, ''):problems.append(branch + ':wrong_share')
        writes = [q for q in r.get('api_requests', []) if q['method'] in ('POST', 'PUT', 'PATCH', 'DELETE')]
        expected = [] if branch == 'native_native' else ['PUT', 'POST'] if branch == 'api_api' else ['PUT']
        if [q['method'] for q in writes] != expected:problems.append(branch + ':api_fallback_or_wrong_route')
        native = r.get('native_requests', [])
        if branch != 'api_api' and not any(q['method'] == 'POST' and q['path'].endswith('/shares') and 200 <= q['status'] < 300 for q in native):problems.append(branch + ':native_share_trace_missing')
        if branch == 'native_native' and not any((q['method'] == 'PUT' and 'job_description.md' in q['path']) or (q['method'] == 'POST' and q['path'].endswith('/upload.php')) for q in native):problems.append(branch + ':native_upload_trace_missing')
        projections.append(state)
    if projections and any(p != projections[0] for p in projections[1:]):problems.append('producer_projection_mismatch')
    return {'qualified': not problems, 'problems': problems, 'scientific_cases': 0, 'confirmed_defects': 0,
            'interpretation': 'Ordinary harness qualification only; no efficacy, generalization or new-defect claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--archive', type=Path, required=True);args = parser.parse_args()
    runtime = json.loads((args.archive / 'runtime.json').read_text())
    results = {branch: json.loads((args.archive / branch / 'result.json').read_text()) for branch in BRANCHES if (args.archive / branch / 'result.json').exists()}
    registration = json.loads((ROOT / 'manifests/agentcompany-owncloud-ordinary-v1.json').read_text())
    print(json.dumps(qualify(runtime, results, registration), indent=2))
