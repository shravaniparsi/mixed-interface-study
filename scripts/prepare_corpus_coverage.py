#!/usr/bin/env python3
"""Build/verify source-pinned coverage for every retained pair and singleton."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.coverage import build, validate
from mixed_interface.evaluation import file_hashes

CONTRACT='manifests/workflow-contract-bindings-v1.json'
OUTPUT='manifests/retained-corpus-coverage-v1.json'
SELECTIONS={'petclinic_terminal':'manifests/petclinic-terminal-integration-qualification.json',
            'realworld_rejection':'manifests/realworld-rejection-controls-v1.json',
            'realworld_paired':'manifests/realworld-paired-controls-v1.json',
            'realworld_integrity':'manifests/realworld-integrity-controls-v1.json',
            'petclinic_integrity':'manifests/petclinic-integrity-controls-v1.json'}


def inputs(root=ROOT):
    read=lambda p:json.loads((root/p).read_bytes())
    contracts=read(CONTRACT)
    return read('manifests/paired-candidate-inventory-v1.json'), {c:read(p) for c,p in contracts['catalog_sources'].items()}, contracts, {k:read(p) for k,p in SELECTIONS.items()}


def generate(root=ROOT):
    inventory,registries,contracts,selections=inputs(root)
    data=build(inventory,registries,contracts,selections)
    paths={CONTRACT,'manifests/paired-candidate-inventory-v1.json','src/mixed_interface/coverage.py',
           'src/mixed_interface/evaluation.py','scripts/prepare_corpus_coverage.py','protocol/retained-corpus-bindings-v1.md',
           *contracts['catalog_sources'].values(),*SELECTIONS.values(),*contracts['shared_contract_sources']}
    qualification=contracts['path_families']['realworld_paired_controls'].get('engineering_qualification')
    if qualification:
        q=json.loads((root/qualification).read_bytes())
        expected_ids=[c['candidate_id'] for c in selections['realworld_paired']['cases']]
        registry_hash=file_hashes(root,[SELECTIONS['realworld_paired']])[SELECTIONS['realworld_paired']]
        if (q.get('status')!='ordinary_exposed_controls_independently_verified'
            or q.get('qualified_candidate_ids')!=expected_ids or q.get('registry_sha256')!=registry_hash
            or q.get('verification',{}).get('verified') is not True
            or q.get('pairs')!=7 or q.get('branches')!=14):
            raise ValueError('RealWorld qualification does not cover the exact engineering registry')
        paths.add(qualification)
    qualification=contracts['path_families'].get('realworld_rejection_controls',{}).get('engineering_qualification')
    if qualification:
        q=json.loads((root/qualification).read_bytes())
        expected_ids=[c['candidate_id'] for c in selections['realworld_rejection']['cases']]
        registry_hash=file_hashes(root,[SELECTIONS['realworld_rejection']])[SELECTIONS['realworld_rejection']]
        if (q.get('status')!='known_rejections_independently_verified'
            or q.get('qualified_candidate_ids')!=expected_ids or q.get('registry_sha256')!=registry_hash
            or q.get('verification',{}).get('verified') is not True
            or q.get('verification',{}).get('matched_rejection_pairs')!=3
            or q.get('pairs')!=6 or q.get('branches')!=12):
            raise ValueError('RealWorld rejection qualification differs from its exact selection')
        paths.add(qualification)
    qualification=contracts['path_families'].get('petclinic_terminal_controls',{}).get('engineering_qualification')
    if qualification:
        q=selections['petclinic_terminal']
        from mixed_interface.evaluation import digest
        expected=selections['petclinic_integrity']['cases']
        if (q.get('status')!='selected_control_paths_independently_verified'
            or q.get('selection')!=expected
            or q.get('registry_semantic_sha256')!=digest(registries['petclinic_development'])
            or q.get('registry_sha256')!=file_hashes(root,[contracts['catalog_sources']['petclinic_development']])[contracts['catalog_sources']['petclinic_development']]
            or q.get('verification',{}).get('verified') is not True
            or q.get('pairs')!=6 or q.get('branches')!=12):
            raise ValueError('PetClinic qualification differs from exact registry and selection')
        paths.add(qualification)
    for family in contracts['path_families'].values():
        paths.update(v for k,v in family.items() if k in ('adapter','runner','pair_runner','extractor','terminal_v2_bridge') and v is not None)
    for workflow in contracts['workflows'].values():
        guard=workflow['input_and_binding_checks'];text=(root/guard['source']).read_text()
        if not all(symbol in text for symbol in guard['symbols']):raise ValueError('Guard symbol missing: '+guard['source'])
        rejection=workflow['rejected_state']
        if rejection['symbol'] not in (root/rejection['source']).read_text():raise ValueError('Rejection predicate missing')
        policy=workflow['normalization'];rules=json.loads((root/policy['policy']).read_bytes())['rules']
        if not set(policy['rules'])<=set(rules):raise ValueError('Unknown normalization rule')
        paths.update((guard['source'],rejection['source'],policy['policy']))
    for row in data['rows']:paths.update(row['recorded_engineering_evidence'])
    # Each derived semantic row must refer to the exact pinned registry bytes.
    observed=file_hashes(root,contracts['catalog_sources'].values())
    if observed!=inventory['source_sha256']:raise ValueError('Registry source hashes differ from inventory')
    return {'coverage':data,'input_sha256':file_hashes(root,paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    expected=generate();path=ROOT/OUTPUT
    if args.verify:
        saved=json.loads(path.read_bytes())
        if saved!=expected:raise ValueError('Coverage map or source hashes changed; review and regenerate prospectively')
        validate(saved['coverage'],*inputs())
    else:path.write_text(json.dumps(expected,indent=2)+'\n')
    print(json.dumps({'verified':args.verify,**expected['coverage']['counts'],'open_gap_counts':expected['coverage']['open_gap_counts'],'execution_authorized':False},indent=2))


if __name__=='__main__':main()
