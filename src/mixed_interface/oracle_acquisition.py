"""Score a fixed, paired oracle-evaluation frame without dropping abstentions.

This is measurement infrastructure, not a method, dataset or scientific result.
Labels are supplied externally; provenance references do not certify their truth.
"""
from collections import Counter

VERDICTS = {'satisfied', 'violated', 'unknown', 'code_error', 'not_run'}
LABELS = {'satisfied', 'violated', 'unresolved'}


def normalize_rbctest_status(status):
    """Translate inspected helper labels only, not a full RBCTest adapter."""
    labels = {'satisfied': 'satisfied', 'mismatched': 'violated',
              'unknown': 'unknown', 'code error': 'code_error'}
    if status not in labels:
        raise ValueError('Unrecognized baseline status; preserve as an integration error')
    return labels[status]


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def score(frame, predictions):
    methods = frame['methods']
    cases = frame['cases']
    if not methods or len(set(methods)) != len(methods) or not cases:
        raise ValueError('Require unique methods and a nonempty fixed case frame')
    ids = [c['case_id'] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate case identifiers would inflate the denominator')
    for c in cases:
        if c['label'] not in LABELS or not c['project_id'] or not c['workflow_id'] or not c['constraint_id']:
            raise ValueError('Invalid label or missing clustering identity')
        if c['label'] != 'unresolved' and not c.get('label_evidence'):
            raise ValueError('Resolved labels need an external evidence reference')
    expected = {(m, i) for m in methods for i in ids}
    observed = [(p['method'], p['case_id']) for p in predictions]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError('Every method must retain exactly one explicit verdict for every case')
    for p in predictions:
        if p['verdict'] not in VERDICTS:
            raise ValueError('Unknown verdict; do not coerce unknown/errors to satisfied')
    lookup = {(p['method'], p['case_id']): p['verdict'] for p in predictions}

    def summarize(method, selected):
        statuses = Counter(lookup[method, c['case_id']] for c in selected)
        resolved = [c for c in selected if c['label'] != 'unresolved']
        judged = [c for c in resolved if lookup[method, c['case_id']] in {'satisfied', 'violated'}]
        positive = [c for c in resolved if c['label'] == 'violated']
        negative = [c for c in resolved if c['label'] == 'satisfied']
        tp = sum(lookup[method, c['case_id']] == 'violated' for c in positive)
        fp = sum(lookup[method, c['case_id']] == 'violated' for c in negative)
        fn = sum(lookup[method, c['case_id']] == 'satisfied' for c in positive)
        tn = sum(lookup[method, c['case_id']] == 'satisfied' for c in negative)
        unknown_labels = [c for c in selected if c['label'] == 'unresolved']
        return dict(retained_cases=len(selected), resolved_cases=len(resolved), unresolved_labels=len(unknown_labels),
            verdict_counts={k: statuses[k] for k in sorted(VERDICTS)},
            true_alerts=tp, false_alerts=fp, missed_violations_with_satisfied_verdict=fn, true_satisfied=tn,
            violations_without_decisive_verdict=len(positive)-tp-fn,
            satisfied_without_decisive_verdict=len(negative)-tn-fp,
            alerts_on_unresolved_labels=sum(lookup[method,c['case_id']]=='violated' for c in unknown_labels),
            decisive_coverage=ratio(len(judged),len(resolved)),
            precision_on_resolved_alerts=ratio(tp,tp+fp),
            violation_detection_fraction=ratio(tp,len(positive)),
            false_alert_fraction=ratio(fp,len(negative)),
            accuracy_on_decisive_resolved=ratio(tp+tn,len(judged)))

    projects = sorted({c['project_id'] for c in cases})
    result = dict(scope='fixed-frame oracle scoring; no independence or label-validity certification',
        retained_cases=len(cases),projects=len(projects),
        workflow_clusters=len({(c['project_id'],c['workflow_id']) for c in cases}),
        constraint_clusters=len({(c['project_id'],c['workflow_id'],c['constraint_id']) for c in cases}),methods={})
    for method in methods:
        result['methods'][method] = dict(overall=summarize(method,cases),
            by_project={project:summarize(method,[c for c in cases if c['project_id']==project]) for project in projects})
    # Retain every paired disagreement, including missing execution and unresolved truth.
    result['paired_verdicts'] = [dict(case_id=c['case_id'],project_id=c['project_id'],label=c['label'],
        verdicts={m:lookup[m,c['case_id']] for m in methods}) for c in cases]
    return result
