#!/usr/bin/env python3
"""Qualify actual regex targets, without claiming semantic equivalence from syntax."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile
from audit_vibe_released_v1 import ROOT, ARCHIVE, DIGEST, PREFIX


class RemoveDocstrings(ast.NodeTransformer):
    def strip(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node
    visit_Module = strip
    visit_FunctionDef = strip
    visit_AsyncFunctionDef = strip
    visit_ClassDef = strip


def normalized(code):
    return ast.dump(RemoveDocstrings().visit(ast.parse(code)), include_attributes=False)


def build():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == DIGEST
    with zipfile.ZipFile(ARCHIVE) as archive:
        source = archive.read(PREFIX + '02_target_api/app/crud.py').decode()
        worker = archive.read(PREFIX + '07_mutation_testing/scripts/_mutation_worker.py').decode()
    operators = None
    for node in ast.parse(worker).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MUTATIONS' for t in node.targets):
            operators = ast.literal_eval(node.value)
    assert len(operators) == 15
    released_path = ROOT / 'manifests/vibe-released-evaluation-audit-v1.json'
    released = json.loads(released_path.read_text())
    rows = []
    for name, pattern, replacement in operators:
        changed, count = re.subn(pattern, replacement, source, count=1)
        match = re.search(pattern, source)
        row = {'name': name, 'pattern': pattern, 'replacement': replacement, 'substitutions': count, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'mutated_sha256': hashlib.sha256(changed.encode()).hexdigest(), 'matched_line': source[:match.start()].count('\n') + 1 if match else None}
        if not count:
            row['source_class'] = 'not_applied'
        else:
            try:
                ast.parse(changed)
                row['source_class'] = 'docstring_only_ast_change' if normalized(source) == normalized(changed) else 'other_parseable_change'
            except SyntaxError as error:
                row['source_class'] = 'syntax_invalid'
                row['syntax_error'] = {'message': error.msg, 'line': error.lineno, 'text': error.text}
        joined = [r for suite in released['rows'] for r in suite['data'].get('mutations', []) if r['name'] == name]
        row['released_records'] = len(joined)
        row['released_outcomes'] = dict(Counter('not_applied' if not r.get('applied') else 'execution_error' if 'error' in r else 'killed' if r.get('killed') is True else 'survived' if r.get('killed') is False else 'missing' for r in joined))
        row['released_error_messages'] = dict(Counter(r['error'] for r in joined if 'error' in r))
        rows.append(row)
    return {'kind': 'vibe_mutation_source_audit_v1', 'post_hoc': True, 'operators': rows, 'source_class_counts': dict(Counter(r['source_class'] for r in rows)), 'archive_sha256': DIGEST, 'released_audit_sha256': hashlib.sha256(released_path.read_bytes()).hexdigest(), 'runtime_equivalence_established': False, 'new_application_executions': 0}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(); out = ROOT / 'manifests/vibe-mutation-source-audit-v1.json'
    if args.verify:
        assert json.loads(out.read_text()) == value
    else:
        assert not out.exists(); out.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value['source_class_counts']))
    for row in value['operators']:
        print(row['name'], row['source_class'], row['released_outcomes'])


if __name__ == '__main__':
    main()
