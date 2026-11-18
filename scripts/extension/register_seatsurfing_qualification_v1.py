#!/usr/bin/env python3
"""Deterministic prospective registration; does not dispatch application jobs."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'manifests/catalog-seatsurfing-qualification-v1.json'


def registration():
    paths=set()
    for pattern in ['scripts/extension/*seatsurfing*','protocol/catalog-seatsurfing*',
                    'manifests/catalog-seatsurfing*',
                    'results/catalog-seatsurfing-build-base-metadata-v1/**/*',
                    'results/catalog-seatsurfing-image-metadata-v1/**/*',
                    'results/catalog-seatsurfing-source-build-preparation-v[1-4]/**/*']:
        paths.update(p for p in ROOT.glob(pattern) if p.is_file() and p!=OUT)
    paths.update(ROOT/p for p in [
        '.github/workflows/catalog_seatsurfing_ordinary_v1.yml',
        'scripts/extension/seal_nginx_evidence_v1.py',
        'manifests/catalog-nginx-evidence-recipient-v1.pem',
        'protocol/catalog-application-qualification-v1.md',
        'protocol/catalog-population-selection-v1.md',
        'protocol/continuation-request-matching-policy-v2.md',
        'results/catalog-application-metadata-v1/09/3.json',
        'results/development-admin-control-v2-api-ci-44105779135/node-tools-package-lock.json'])
    for wave in range(1,40):
        directory=ROOT/f'results/catalog-source-wave{wave}-v1'
        collection=directory/'collection.json';paths.add(collection)
        for row in json.loads(collection.read_text())['rows']:
            if row['repository']=='seatsurfing/seatsurfing':paths.add(directory/row['file'])
    # Freeze transitive local Python/JS helpers, including shared components.
    examined=set()
    while paths-examined:
        path=(paths-examined).pop();examined.add(path)
        if path.suffix=='.py':
            for node in ast.walk(ast.parse(path.read_text())):
                modules=[]
                if isinstance(node,ast.ImportFrom) and node.module:modules=[node.module]
                if isinstance(node,ast.Import):modules=[alias.name for alias in node.names]
                for name in modules:
                    candidate=path.parent/(name.replace('.','/')+'.py')
                    if candidate.is_file():paths.add(candidate)
        elif path.suffix=='.mjs':
            for name in re.findall(r'''(?:from\s*|import\s*\()\s*['"](\.[^'"]+)['"]''',path.read_text()):
                candidate=(path.parent/name).resolve()
                if candidate.is_file():paths.add(candidate)
    return {'status':'qualification_registered','repository':'seatsurfing/seatsurfing',
        'application_revision':'9953f452324bab6fb8f7106dd8965cc401aa456c',
        'qualification_attempt':1,'max_qualification_jobs':2,'max_job_minutes':30,
        'shared_execution_seconds':1380,'cleanup_absolute_seconds':1560,'max_build_seconds':1080,
        'scientific_inputs_in_this_job':0,'ordinary_scenarios':2,'branches_per_scenario':3,
        'ordinary_edits':[{'path':'/announcement','value':'Edit notice'},{'path':'/description','value':'Edit description'}],
        'workflow':'.github/workflows/catalog_seatsurfing_ordinary_v1.yml',
        'runtime_qualified':False,'success_requires':'retained_evidence_audit_after_both_ordinary_cycles',
        'script_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    raw=(json.dumps(registration(),indent=2)+'\n').encode()
    if args.verify:
        if OUT.read_bytes()!=raw:raise ValueError('Qualification registration differs from frozen inputs')
        print('SeatSurfing qualification registration hashes verified; no application executed.')
    else:OUT.write_bytes(raw)


if __name__=='__main__':main()
