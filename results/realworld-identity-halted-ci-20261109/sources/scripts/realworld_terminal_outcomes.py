"""RealWorld branch classification for terminal v2; no dispatch authorization.

The pure classifier consumes already source-qualified records. Archive replay
validates the existing control cohort before classification. Pair comparability
and owned process-group cleanup belong to the future per-job loader.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import summarize_realworld_paired_components as reducer
from validate_realworld_paired_controls import validate as validate_archive


def classify_branch(raw, run, registered, *, fixture, cleanup_confirmed):
    """Keep transport, evidence completeness, and business observations separate.

    cleanup_confirmed must come from the owning supervisor, not adapter exit.
    No arbitrary adapter exception is promoted to an application HTTP failure.
    """
    def result(kind, issues, **extra):
        return {'kind': kind, 'issues': sorted(set(issues)), **extra}

    if cleanup_confirmed is not True or run.get('backend_exit_confirmed') is not True:
        return result('cleanup_unconfirmed', ['owned_cleanup_not_confirmed'])
    if run.get('interrupted') is True:
        return result('interrupted', ['interruption'])
    if run.get('timed_out') is True:
        return result('case_timeout', ['case_deadline'])
    if not isinstance(raw, dict) or not raw:
        return result('missing_evidence', ['missing_result'])
    if raw.get('execution_status') != 'completed' or raw.get('error'):
        return result('environment_failure', ['unclassified_adapter_or_execution_error'])
    if type(run.get('exit_code')) is not int or run['exit_code'] != 0:
        return result('environment_failure', ['unexpected_worker_exit'])
    if run.get('status') not in ('passed', 'completed'):
        return result('environment_failure', ['unrecognized_runner_status'])
    # The historical reducer names successful process completion "passed".
    # This translation is permitted only after the transport checks above;
    # check failures in raw evidence are never rewritten.
    normalized = deepcopy(run)
    normalized['status'] = 'passed'
    try:
        issues = (reducer.capture_integrity_issues(raw, required=True)
                  + reducer.execution_integrity_issues(raw, required=True))
        reduced = reducer.reduce_case(raw, normalized, registered, fixture=fixture,
                                      provenance_issues=issues)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return result('missing_evidence', ['malformed_evidence'])
    if not reduced['execution_evidence_complete']:
        return result('missing_evidence', reduced['evidence_issues'], components=reduced)
    failed = any(p['mismatch_observed'] for name, p in reduced['components'].items()
                 if name not in ('environment_reset_cleanup', 'unresolved_policy'))
    kind = ('completed_mismatch' if failed else 'unresolved_policy' if reduced['policy_unresolved']
            else 'clean_observation' if reduced['accepted_prefix'] else 'matched_rejection')
    return result(kind, [], components=reduced)


def replay_archive(directory):
    """Replay the pinned 14-branch archive, not a fresh campaign qualification."""
    directory = Path(directory)
    certificate = validate_archive(directory)
    read = lambda name: json.loads((directory / name).read_bytes())
    summary = read('summary.json')
    specs = {c['candidate_id']: c for c in read('registered-candidates.json')['cases']}
    fixture = read('fixture-references.json')
    classified = []
    for branch in summary['branches']:
        value = classify_branch(read(branch['evidence']), branch, specs[branch['candidate_id']],
                                fixture=fixture, cleanup_confirmed=summary['frontend_exit_confirmed'])
        classified.append({'case_id': branch['case_id'], **value})
    if len(classified) != 14 or any(b['kind'] != 'clean_observation' for b in classified):
        raise ValueError('Archived engineering controls failed terminal replay')
    return {'kind': 'historical_control_terminal_replay', 'source_validation': certificate,
            'branches': classified, 'new_application_executions': 0,
            'per_job_dispatch_qualified': False, 'primary_freeze_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    print(json.dumps(replay_archive(args.archive), indent=2))
