"""Verify coverage, source anchors and qualification provenance, not coding truth."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    matrix_path = ROOT / 'manifests/agentcompany-capability-matrix-v1.json'
    matrix = json.loads(matrix_path.read_text())
    review = json.loads((ROOT / 'manifests/agentcompany-downstream-predicates-v1.json').read_text())
    assert hashlib.sha256(matrix_path.read_bytes()).hexdigest() == review['source_matrix_sha256']
    original = {r['task']: r for r in matrix['tasks']}
    rows = review['tasks']
    assert len(rows) == len({r['task'] for r in rows}) == 15
    assert {r['task'] for r in rows} == set(original)
    assert review['task_count'] == len(rows)
    assert review['family_count'] == len({r['family'] for r in rows}) == 10
    assert review['relation_counts'] == dict(sorted(Counter(r['relation'] for r in rows).items()))
    for row in rows:
        name = row['task']
        raw = (ROOT / 'results/agentcompany-feasibility-v1/source/workspaces/tasks' / name / 'task.md').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['instruction_sha256'] == original[name]['instruction_sha256']
        assert row['family'] == original[name]['family']
        assert row['producer_anchor'] in raw.decode() and row['consumer_anchor'] in raw.decode()
        for field in ('producer_contract', 'consumer_contract', 'competent_api_checks', 'interpretation_limit', 'exposure', 'coding'):
            assert isinstance(row[field], str) and row[field]
    qualified = [r['task'] for r in rows if r['ordinary_three_path_qualified']]
    assert qualified == ['hr-new-grad-job-description'] and review['ordinary_qualified_tasks'] == 1
    outcome = json.loads((ROOT / 'manifests/agentcompany-owncloud-ordinary-outcome-v3.json').read_text())
    assert outcome['run_id'] == 44055187164 and outcome['qualification']['qualified']
    assert outcome['qualification']['scientific_cases'] == review['scientific_executions'] == 0
    print(json.dumps(dict(tasks=len(rows), families=review['family_count'], relation_counts=review['relation_counts'], ordinary_qualified=qualified,
                         scope='Verifies retained coverage and literal source anchors; interpretive predicate labels are not independently adjudicated.'), indent=2))


if __name__ == '__main__': main()
