#!/usr/bin/env python3
"""Apply every pinned mutation independently; no services or generated tests run."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import tempfile
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/restestbench-applicability-v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    module_path = ROOT / 'evidence/restestbench-source-v1/src/mutator.py'
    spec = importlib.util.spec_from_file_location('upstream_mutator', module_path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    pins = json.loads((BASE / 'input-pins.json').read_text())
    inventory = json.loads((ROOT / 'manifests/restestbench-source-inventory-v1.json').read_text())
    source_check = json.loads((BASE / 'source-git-verification.json').read_text())
    assert source_check['commit'] == pins['commit'] == inventory['pin']
    for row in source_check['files']: assert pins['files'][row['path']] == row['git_blob']
    data = {}
    with tarfile.open(BASE / 'inputs.tar.gz') as archive:
        for member in archive:
            assert member.isfile() and member.name not in data
            raw = archive.extractfile(member).read()
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pins['files'][member.name]
            data[member.name] = raw
    assert set(data) == set(pins['files'])
    rows = []; requirements = []
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        for service, entries in sorted(inventory['services'].items()):
            for entry in entries:
                path = entry['path']; assert pins['files'][path] == entry['git_blob']
                req_file = temporary / 'requirement.json'; req_file.write_bytes(data[path])
                try: req = module.Requirement.from_file(req_file)
                except Exception as exc:
                    requirements.append({'path': path, 'parse_error': type(exc).__name__}); continue
                assert req.service == service
                requirements.append({'path': path, 'service': service, 'id': req.id, 'mutants': len(req.mutants), 'parse_error': None})
                for index, mutant in enumerate(req.mutants):
                    relative = Path(mutant.file)
                    assert not relative.is_absolute() and '..' not in relative.parts
                    source = 'services/' + service + '/original/' + mutant.file
                    target = temporary / 'working' / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists(): target.unlink()
                    before = data.get(source)
                    if before is not None: target.write_bytes(before)
                    outcome = {'requirement_path': path, 'requirement_id': req.id, 'service': service, 'mutant_index': index, 'target': source}
                    try:
                        applied = module.Mutator(temporary / 'working').apply_mutation(mutant)
                        after = target.read_bytes()
                        outcome.update(applied=applied, bytes_changed=after != before, error=None, before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(after).hexdigest())
                    except Exception as exc:
                        outcome.update(applied=False, bytes_changed=False, error=type(exc).__name__)
                    rows.append(outcome)
    counts = {service: dict(Counter('error' if r['error'] else 'applied_changed' if r['applied'] and r['bytes_changed'] else 'applied_unchanged' if r['applied'] else 'not_applied' for r in rows if r['service'] == service)) for service in sorted(inventory['services'])}
    return {'kind': 'restestbench_static_applicability_v1', 'commit': pins['commit'], 'requirement_files': len(requirements), 'parse_errors': sum(r['parse_error'] is not None for r in requirements), 'mutant_entries': len(rows), 'counts_by_service': counts, 'requirements': requirements, 'observations': rows, 'source_sha256': sha(module_path), 'inputs_sha256': sha(BASE / 'inputs.tar.gz'), 'pins_sha256': sha(BASE / 'input-pins.json'), 'source_git_verification_sha256': sha(BASE / 'source-git-verification.json'), 'real_application_executions': 0, 'golden_test_executions': 0, 'paid_model_calls': 0, 'semantic_validity_established': False, 'mutation_labels_exposed': True}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); path = ROOT / 'manifests/restestbench-applicability-v1.json'
    if args.verify: assert json.loads(path.read_text()) == value
    else:
        assert not path.exists(); path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('requirements', 'observations')}))
    for row in value['observations']:
        if not row['applied'] or not row['bytes_changed']: print(json.dumps(row))


if __name__ == '__main__': main()
