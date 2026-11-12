#!/usr/bin/env python3
"""Classify observed failing assertion sites; not a counterfactual baseline replay."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/restestbench-mutant-runtime-v1-ci-43144135284'
SOURCES = ROOT / 'results/restestbench-assertion-analysis-v1/golden-sources.json'


def locate_failure(text, sources):
    frames = re.findall(r'(data/tests/[a-z-]+/test_\d+\.py):(\d+): in ', text)
    if not frames:
        return {'kind': 'unresolved_failure_site'}
    path, line = frames[-1]
    line = int(line)
    assert path in sources
    source = sources[path]
    nodes = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert) and n.lineno <= line <= n.end_lineno]
    if not nodes:
        return {'kind': 'non_assertion_site', 'path': path, 'line': line}
    assert len(nodes) == 1
    node = nodes[0]
    status = any(isinstance(n, ast.Attribute) and n.attr == 'status_code' for n in ast.walk(node.test))
    return {'kind': 'http_status_assertion' if status else 'other_assertion', 'path': path, 'line': line, 'predicate': ast.get_source_segment(source, node.test)}


def build():
    sources = json.loads(SOURCES.read_text())
    expected = json.loads((ROOT / 'manifests/restestbench-valid-input-hashes-v1.json').read_text())['services']
    assert len(sources) == 106
    for path, source in sources.items():
        assert hashlib.sha256(source.encode()).hexdigest() == expected[path.split('/')[2]][path]
    qualified_path = ROOT / 'manifests/restestbench-mutant-runtime-results-v1.json'
    qualified = json.loads(qualified_path.read_text())
    rows = []
    for service, summary in sorted(qualified['services'].items()):
        folder = ARCHIVE / service
        if not (folder / 'observations.json').exists():
            continue
        observations = json.loads((folder / 'observations.json').read_text())
        assert hashlib.sha256((folder / 'observations.json').read_bytes()).hexdigest() == summary['observations_sha256']
        for trial in observations['trials']:
            if not trial['candidate_detection']:
                continue
            xml = folder / (trial['key'] + '.xml')
            assert hashlib.sha256(xml.read_bytes()).hexdigest() == qualified['evidence_sha256'][str(xml.relative_to(ARCHIVE))]
            failures = list(ET.parse(xml).iter('failure'))
            assert failures
            for failure in failures:
                text = failure.text or ''
                site = locate_failure(text, sources)
                observed_5xx = sorted(set(int(a or b or c) for a, b, c in re.findall(r'<Response \[(5\d\d)\]>|\bgot (5\d\d)\b|E\s+assert (5\d\d) [=!<>]', text)))
                exceptions = re.findall(r'^E\s+([A-Za-z_][A-Za-z_0-9.]*(?:Error|Exception)):', text, re.MULTILINE)
                mechanism = 'other_exception' if any(e != 'AssertionError' for e in exceptions) else 'assertion_failure' if 'AssertionError' in exceptions or re.search(r'^E\s+assert ', text, re.MULTILINE) else 'unresolved'
                rows.append({'service': service, 'key': trial['key'], **site, 'failure_mechanism': mechanism, 'observed_5xx_in_failure_text': observed_5xx, 'failure_message': failure.get('message', '')})
    services = {}
    for service in qualified['services']:
        selected = [r for r in rows if r['service'] == service]
        services[service] = {'failure_elements': len(selected), 'sites': dict(Counter(r['kind'] for r in selected)), 'mechanisms': dict(Counter(r['failure_mechanism'] for r in selected)), 'failures_with_observed_5xx': sum(bool(r['observed_5xx_in_failure_text']) for r in selected)}
    return {'kind': 'restestbench_assertion_analysis_v1', 'post_hoc': True, 'services': services, 'rows': rows, 'interpretation': 'Observed first-failure sites only; not a status-only baseline replay, complete response trace, or semantic-defect adjudication.', 'source_bundle_sha256': hashlib.sha256(SOURCES.read_bytes()).hexdigest(), 'runtime_manifest_sha256': hashlib.sha256(qualified_path.read_bytes()).hexdigest(), 'new_application_executions': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    path = ROOT / 'manifests/restestbench-assertion-analysis-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        assert not path.exists()
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value['services'], indent=2))


if __name__ == '__main__':
    main()
