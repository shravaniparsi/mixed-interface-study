"""Reconcile historical sampling dispositions; never infer blindness from absence."""
import collections, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
INPUTS = ['manifests/editability-repairability-repository-schedule-v1.json', 'manifests/redesign-evaluation-status-v21.json', 'manifests/editability-repairability-exposure-classes-v1.json', 'results/fresh-session-source-preflight-v1/feasibility-v3-summary.json']
def audit():
    schedule, terminal, exposure, feasibility = [json.loads((ROOT/p).read_text()) for p in INPUTS]
    old = {r['sequence']: r for r in terminal['rows']}
    assert len(old) == len(terminal['rows'])
    rows = []
    for r in schedule['rows']:
        seq, repo = r['sequence'], r['repository']
        if r['group'] == 'development':
            disposition = 'historical_development_allocation'
        else:
            assert seq in old and old[seq]['repository'] == repo
            disposition = old[seq]['status']
        rows.append(dict(sequence=seq, repository=repo, prior_disposition=disposition,
                         eligible_for_provenance_review=disposition == 'source_unattempted',
                         independence_established=False, evaluation_admitted=False))
    assert feasibility['status'] == 'development_feasibility_passed'
    return dict(input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
                rows=rows, counts=dict(collections.Counter(r['prior_disposition'] for r in rows)),
                provenance_review_candidates=sum(r['eligible_for_provenance_review'] for r in rows),
                historical_exposure_index_gaps=exposure['global_history_gaps'],
                interpretation='Unattempted in this study is not proof of no exposure elsewhere. Metadata reference alone is not a behavioral outcome. Closed slots remain closed.',
                independent_evaluation_cases=0)
if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
