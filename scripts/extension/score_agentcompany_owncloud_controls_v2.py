"""Extend the unchanged v1 outcome rules with browser-readiness witnesses."""
import argparse
import json
import math
from pathlib import Path
from score_agentcompany_owncloud_controls_v1 import qualify as qualify_v1, BRANCHES, ROOT


def qualify(runtime, results, registration):
    outcome = qualify_v1(runtime, results, registration)
    problems = outcome['problems']
    for branch in BRANCHES[:2]:
        result = results.get(branch, {})
        ready = result.get('readiness', [])
        if len(ready) != (2 if branch == 'native_native' else 1):
            problems.append(branch + ':readiness_incomplete')
        for record in ready:
            value = record.get('free_space', '')
            try:
                valid = str(value).strip() != '' and math.isfinite(float(value))
            except (TypeError, ValueError):
                valid = False
            if not valid or record.get('dir') != '/Documents' or record.get('status') != 200:
                problems.append(branch + ':invalid_readiness')
            matches = []
            for response in result.get('passive_responses', []):
                if '/getstoragestats.php?' not in response.get('path', '') or response.get('status') != 200:
                    continue
                try:
                    data = json.loads(response.get('body', ''))['data']
                    if str(data['freeSpace']) == str(value) and response['observedAt'] <= record['at']:
                        matches.append(response)
                except (ValueError, KeyError, TypeError):
                    pass
            if not matches:
                problems.append(branch + ':readiness_response_missing')
        actions = result.get('ui_events', [])
        if not any(e.get('action') == 'dismiss_welcome' for e in actions):
            problems.append(branch + ':welcome_action_missing')
        if not any(e.get('action') == 'list_page' and 'job_description.md' in e.get('names', []) for e in actions):
            problems.append(branch + ':row_navigation_missing')
        if branch == 'native_native':
            uploads = [e for e in actions if e.get('action') == 'select_upload']
            if len(uploads) != 1 or not ready or uploads[0].get('at', -1) < ready[0].get('at', 0) or uploads[0].get('free_space') != ready[0].get('free_space'):
                problems.append(branch + ':upload_before_readiness_or_value_changed')
    outcome['qualified'] = not problems
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--archive', type=Path, required=True); args = parser.parse_args()
    runtime = json.loads((args.archive / 'runtime.json').read_text())
    results = {b: json.loads((args.archive / b / 'result.json').read_text()) for b in BRANCHES if (args.archive / b / 'result.json').exists()}
    registration = json.loads((ROOT / 'manifests/agentcompany-owncloud-ordinary-v1.json').read_text())
    print(json.dumps(qualify(runtime, results, registration), indent=2))
