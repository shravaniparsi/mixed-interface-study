#!/usr/bin/env python3
"""Analyze declared features only; no outcome labels or application execution."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.selection import Candidate, CandidateSelector, DependencyEdge, RouteObligation, Strategy, ExecutionFeedback


def build():
    rows, hashes = [], {}
    for name in ('realworld-article-generated-pool-v1', 'quartz-job-generated-pool-v2'):
        path = ROOT / 'manifests' / (name + '.json')
        raw = path.read_bytes()
        pool = json.loads(raw)
        candidates = []
        for row in pool['cases']:
            targets = row['selection_targets']
            deps = frozenset(DependencyEdge(**e) for e in targets['dependencies'])
            obligations = frozenset(RouteObligation(
                DependencyEdge(**{k: e[k] for k in ('producer', 'consumer', 'field_or_state', 'kind')}),
                e['producer_interface'], e['consumer_interface']) for e in targets['obligations'])
            candidates.append(Candidate(row['case_id'], deps, obligations, row['estimated_cost_s']))
        dep_count = len({c.dependencies for c in candidates})
        cost_count = len({c.estimated_cost_s for c in candidates})
        signatures = Counter((c.dependencies, c.obligations, c.estimated_cost_s) for c in candidates)
        assert dep_count == 1 and cost_count == 1
        # Implementation cross-checks for two extreme feedback scenarios only.
        # The invariant argument covers other feedback: every remaining score
        # is the same |D minus covered| / cost because D and cost are shared.
        checks = []
        for feedback_mode in ('none_exercised', 'all_declared_exercised'):
            for seed in (0, 1, 7):
                a = CandidateSelector(candidates, Strategy.RANDOM, seed)
                b = CandidateSelector(candidates, Strategy.DEPENDENCY_GREEDY, seed)
                compared = 0
                while not a.exhausted:
                    left, right = a.select_next(), b.select_next()
                    assert left.case_id == right.case_id
                    deps = left.dependencies if feedback_mode == 'all_declared_exercised' else frozenset()
                    reached = frozenset(op for d in deps for op in (d.producer, d.consumer))
                    value = ExecutionFeedback(left.case_id, reached, deps)
                    a.record_feedback(value)
                    b.record_feedback(value)
                    compared += 1
                assert b.exhausted
                checks.append({'feedback_scenario': feedback_mode, 'seed': seed, 'matching_choices': compared})
        rows.append({'pool': str(path.relative_to(ROOT)), 'candidate_count': len(candidates),
                     'dependency_signatures': dep_count, 'estimated_cost_values': sorted({c.estimated_cost_s for c in candidates}),
                     'route_obligation_signatures': len({c.obligations for c in candidates}),
                     'indistinguishable_feature_class_sizes': sorted(signatures.values()),
                     'dependency_random_equivalent_under_shared_feedback_and_seed': True,
                     'synthetic_implementation_cross_checks': checks})
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    source = ROOT / 'src/mixed_interface/selection.py'
    hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    return {'kind': 'selector_pool_structure_audit_v1', 'pools': rows,
            'new_application_executions': 0, 'outcome_labels_used': False,
            'interpretation': 'Dependency-greedy and random are equivalent on these declared pools with identical seeds and common feedback. Route-greedy can distinguish routes but not payload variants sharing features. This is not measured defect detection, latency or proof of universal selector equivalence.',
            'source_sha256': hashes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    path = ROOT / 'manifests/selector-pool-structure-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value, indent=2))
