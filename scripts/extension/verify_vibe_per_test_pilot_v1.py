#!/usr/bin/env python3
"""Reconstruct per-test transition comparisons from the registered replay evidence."""
import argparse
import ast
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
from vibe_paired_outcomes_v1 import compare, node_outcomes, parse_event_text
ROOT = Path(__file__).resolve().parents[2]
RUN = 43152134972
HEAD = '2efa3a99c4c33f582d82ab16a5227cc05b91148d'
PREFIX = 'vibe-testing-replication-package/'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    registration = json.loads((ROOT / 'manifests/vibe-per-test-pilot-registration-v1.json').read_text())
    for path, digest in registration['sha256'].items():
        assert sha(ROOT / path) == digest
    path = ROOT / 'results/evaluation-feasibility-screen-v1/vibe-testing-replication-package.zip'
    assert sha(path) == registration['archive_sha256']
    with zipfile.ZipFile(path) as archive:
        files = {p[len(PREFIX):]: archive.read(p) for p in archive.namelist() if not p.endswith('/')}
    operators = None
    for node in ast.parse(files['07_mutation_testing/scripts/_mutation_worker.py']).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MUTATIONS' for t in node.targets):
            operators = ast.literal_eval(node.value)
    return registration, files, operators


def validate_level(folder, registration, files, operators):
    data = json.loads((folder / 'observations.json').read_text()); level = data['level']
    assert data['kind'] == 'vibe_per_test_pilot_v1' and data['archive_sha256'] == registration['archive_sha256'] and data['paid_model_calls'] == 0
    assert (folder / 'study-head.txt').read_text().strip() == HEAD
    for line in (folder / 'instrument-sha256.txt').read_text().splitlines():
        digest, path = line.split(None, 1); assert registration['sha256'][path.strip()] == digest
    suites = sorted(r['path'] for r in registration['selected_suites'] if f'__{level}__' in r['path'])
    expected = [f'{Path(s).parent.name}--{name}' for s in suites for name in ['original-before'] + [o[0] for o in operators] + ['original-after']]
    assert data['expected_keys'] == expected
    seen = [r['key'] for r in data['trials']]; assert seen == expected[:len(seen)] and data['unattempted_keys'] == expected[len(seen):]
    if data['terminal'] == 'completed':
        assert seen == expected
    sources = {p: hashlib.sha256(b).hexdigest() for p, b in files.items() if p.startswith('02_target_api/app/') and p.endswith('.py')}
    assert data['source_hashes'] == sources
    original = files['02_target_api/app/crud.py']; variants = {'original-before': original, 'original-after': original}; static = {}
    for name, pattern, replacement in operators:
        value, count = re.subn(pattern, replacement, original.decode(), count=1); variants[name] = value.encode()
        if not count:
            static[name] = 'not_applied'
        else:
            try:
                ast.parse(value)
            except SyntaxError:
                static[name] = 'syntax_invalid'
    rows = {}; nodes = {}; event_summaries = {}; before_usable = {}
    for row in data['trials']:
        key = row['key']; name = row['operator']; suite = row['suite']; group = Path(suite).parent.name
        assert suite in suites and key == group + '--' + name
        assert row['suite_sha256'] == hashlib.sha256(files[suite]).hexdigest()
        assert row['source_sha256'] == hashlib.sha256(variants[name]).hexdigest()
        rows[key] = row
        if name in static:
            assert row['outcome'] == static[name] and not row['test_executed']
        elif name not in ['original-before', 'original-after'] and not before_usable[group]:
            assert row['outcome'] == 'unusable_original_control' and not row['test_executed']
        if row['test_executed']:
            assert row['imported']['pid'] == row['pid'] and row['imported']['source_sha256'] == row['source_sha256']
            imported = json.loads((folder / key / 'service.log').read_text().splitlines()[0]); assert imported == row['imported']
            assert row['health'][-1]['status'] == row['reset']['status'] == 200
            assert json.loads(row['reset']['body'])['status'] == 'ok'
            assert row['reset_counts'] and all(v == 0 for v in row['reset_counts'].values())
            path = folder / key / 'junit.xml'
            if path.exists():
                xml = ET.parse(path); totals = {k: sum(int(s.get(k, 0)) for s in xml.iter('testsuite')) for k in ['tests', 'failures', 'errors', 'skipped']}
                totals['passed'] = totals['tests'] - totals['failures'] - totals['errors'] - totals['skipped']; assert totals == row['junit']
            if row['outcome'] == 'reported':
                assert path.exists() and row['return_code'] in [0, 1] and not row['timeout']
            events_path = folder / key / 'events.jsonl'
            events, malformed = parse_event_text(events_path.read_text()) if events_path.exists() else ([], [])
            nodes[key] = node_outcomes(events) if row['outcome'] == 'reported' and not malformed else None
            event_summaries[key] = {'malformed_event_lines': malformed, 'http_events': sum(e['kind'] == 'http' for e in events), 'blocked_external_http': sum(e['kind'] == 'blocked_external_http' for e in events), 'http_5xx_events': sum(e['kind'] == 'http' and 500 <= e.get('status', 0) < 600 for e in events), 'per_test_nodes': len(nodes[key]) if nodes[key] is not None else None}
            if any(e['kind'] == 'blocked_external_http' for e in events):
                nodes[key] = None
        else:
            assert row['outcome'] not in ['reported', 'timeout']
        if name == 'original-before':
            before_usable[group] = row['outcome'] == 'reported' and row.get('junit', {}).get('passed', 0) > 0
    comparisons = []
    for suite in suites:
        group = Path(suite).parent.name; before = rows.get(group + '--original-before'); after = rows.get(group + '--original-after')
        for name, _, _ in operators:
            key = group + '--' + name; mutant = rows.get(key)
            item = {'suite': suite, 'key': key, 'operator': name}
            if not mutant:
                item.update(paired_evidence_qualified=False, reason='unattempted')
            elif name in static:
                item.update(paired_evidence_qualified=False, reason=static[name])
            elif not before or not after or any(r['outcome'] != 'reported' for r in [before, mutant, after]):
                item.update(paired_evidence_qualified=False, reason='unqualified_or_missing_execution')
            else:
                item.update(compare(nodes.get(before['key']), nodes.get(key), nodes.get(after['key']), before['junit'], mutant['junit']))
                item['new_failure_details'] = {n: nodes[key][n] for n in item.get('new_failure_nodes', [])}
            comparisons.append(item)
    qualified = [r for r in comparisons if r['paired_evidence_qualified']]
    return {'level': level, 'terminal': data['terminal'], 'recorded_trials': len(seen), 'executed_suite_trials': sum(r['test_executed'] for r in rows.values()), 'trial_outcomes': dict(Counter(r['outcome'] for r in rows.values())), 'unattempted_keys': data['unattempted_keys'], 'paired_qualified_mutant_comparisons': len(qualified), 'unqualified_comparison_reasons': dict(Counter(r['reason'] for r in comparisons if not r['paired_evidence_qualified'])), 'aggregate_kills_in_qualified_comparisons': sum(r['aggregate_kill'] for r in qualified), 'identified_new_failures_in_qualified_comparisons': sum(r['identified_new_failure'] for r in qualified), 'disagreements': sum(r['count_rule_disagrees_with_new_failure'] for r in qualified), 'comparisons': comparisons, 'event_summaries': event_summaries, 'observations_sha256': sha(folder / 'observations.json')}


def build(archive):
    registration, files, operators = inputs(); run = json.loads((archive / 'run.json').read_text()); jobs = json.loads((archive / 'jobs.json').read_text())['jobs']
    assert run['id'] == RUN and run['head_sha'] == HEAD and run['status'] == 'completed' and run['run_attempt'] == 1
    assert len(jobs) == 2 and all(j['status'] == 'completed' for j in jobs)
    levels = {}
    for path in archive.rglob('observations.json'):
        value = validate_level(path.parent, registration, files, operators); assert value['level'] not in levels; levels[value['level']] = value
    for level in ['L0', 'L4']:
        if level not in levels:
            levels[level] = {'terminal': 'missing_observations', 'execution_count_known': False}
    minutes = sum((datetime.fromisoformat(j['completed_at'].replace('Z', '+00:00')) - datetime.fromisoformat(j['started_at'].replace('Z', '+00:00'))).total_seconds() / 60 for j in jobs)
    return {'kind': 'vibe_per_test_pilot_results_v1', 'run_id': RUN, 'study_head': HEAD, 'levels': levels, 'application_job_minutes': minutes, 'job_minutes_ceiling': 40, 'paid_model_calls': 0, 'outcome_exposed_exploratory_pilot': True, 'semantic_fault_adjudication_complete': False, 'evidence_sha256': {str(p.relative_to(archive)): sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--archive', type=Path, required=True); parser.add_argument('--output', type=Path, required=True); parser.add_argument('--verify', action='store_true'); args = parser.parse_args(); value = build(args.archive)
    if args.verify:
        assert json.loads(args.output.read_text()) == value
    else:
        assert not args.output.exists(); args.output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ['levels', 'evidence_sha256']}, indent=2))
    for level in value['levels'].values():
        print(json.dumps({k: v for k, v in level.items() if k not in ['comparisons', 'event_summaries']}, indent=2))


if __name__ == '__main__':
    main()
