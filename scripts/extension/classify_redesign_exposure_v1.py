#!/usr/bin/env python3
"""Conservative provenance categories, never a certificate of no exposure."""
import hashlib
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ALLOWED_METADATA={
    'results/catalog-population-offline-v1/software-metadata.json',
    'results/catalog-population-offline-v1/selection.json',
}

def build():
    prior_path='manifests/prior-repository-reference-index-v2.json'
    current_path='manifests/prior-repository-reference-index-v3.json'
    closed_path='manifests/catalog-cohort-v1.json'
    old={r['repository'] for r in json.loads((ROOT/prior_path).read_text())['references']}
    current=json.loads((ROOT/current_path).read_text())
    closed=set(json.loads((ROOT/closed_path).read_text())['selected'])
    rows=[]
    for r in current['references']:
        repo=r['repository'];paths=set(r['referring_paths'])
        if repo in closed:category='closed_catalog_source_reviewed'
        elif repo in old:category='prior_reference_exposure_unresolved'
        elif paths and paths<=ALLOWED_METADATA:category='only_catalog_metadata_references_in_available_index'
        else:category='other_reference_provenance_unresolved'
        rows.append({'repository':repo,'category':category,'referring_paths':sorted(paths),
                     'unlisted_history_exposure':'unknown','independent_evaluation_eligible':False})
    assert len(rows)==len({r['repository'] for r in rows})==1567
    assert old<={r['repository'] for r in rows}
    assert sum(r['category']=='closed_catalog_source_reviewed' for r in rows)==12
    sources=[prior_path,current_path,closed_path,*sorted(ALLOWED_METADATA),
             'results/catalog-population-offline-v1/verification.json']
    return {'scope':'references in available tracked objects only; no app source acquisition or execution',
            'source_head':current['source_head'],'classification_is_sampling_selection':False,
            'global_history_gaps':current['status_counts'],'metadata_only_path_allowlist':sorted(ALLOWED_METADATA),
            'categories':dict(Counter(r['category'] for r in rows)),
            'rows':rows,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
            'absence_proves_no_exposure':False,'new_scientific_cases':0}

def main():
    import sys
    out=ROOT/'manifests/editability-repairability-exposure-classes-v1.json'
    result=build();encoded=json.dumps(result,indent=2)+'\n'
    if '--verify' in sys.argv:assert out.read_text()==encoded
    else:
        assert not out.exists();out.write_text(encoded)
    print(json.dumps(result['categories']))
if __name__=='__main__':main()
