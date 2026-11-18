#!/usr/bin/env python3
"""Run the prospectively published, local-only redesign feasibility screen."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_catalog_population_v1 import evaluate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',required=True);args=parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.freeze)
    sources=['protocol/editability-repairability-metadata-screen-v1.md','scripts/extension/screen_redesign_metadata_v1.py','scripts/extension/collect_catalog_population_v1.py','manifests/editability-repairability-exposure-classes-v1.json','results/catalog-population-offline-v1/software-metadata.json','results/catalog-population-offline-v1/selection.json']
    hashes={}
    for p in sources:
        raw=(ROOT/p).read_bytes();assert raw==subprocess.check_output(['git','show',args.freeze+':'+p],cwd=ROOT)
        hashes[p]=hashlib.sha256(raw).hexdigest()
    versions=subprocess.check_output(['ruby','-r','yaml','-e','puts RUBY_VERSION;puts Psych::VERSION'],text=True).split()
    assert versions==['2.6.10','3.1.0']
    texts=json.loads((ROOT/sources[4]).read_text());assert len(texts)==1362
    ruby='x=JSON.parse(STDIN.read); out={}; x.each{|k,v| begin; out[k]={"data"=>YAML.safe_load(v, permitted_classes: [Date,Time], aliases: false)}; rescue => e; out[k]={"error"=>e.class.to_s+": "+e.message}; end}; puts JSON.generate(out)'
    parsed=json.loads(subprocess.check_output(['ruby','-r','yaml','-r','json','-r','date','-e',ruby],input=json.dumps(texts).encode(),timeout=30))
    exposure=json.loads((ROOT/sources[3]).read_text())
    categories={r['repository']:r['category'] for r in exposure['rows']}
    allowed='only_catalog_metadata_references_in_available_index'
    prior={repo for repo,c in categories.items() if c!=allowed}
    rows=[];passing={}
    for path,value in sorted(parsed.items()):
        data=value.get('data');row={'path':path,**evaluate(path,data,prior)}
        if 'error' in value:row['parse_error']=value['error']
        description=data.get('description') if isinstance(data,dict) else None
        if not isinstance(description,str) or not re.search(r'\bAPI\b',description,re.I):row['failed_checks'].append('explicit_API_advertising')
        if categories.get(row['repository'])!=allowed:row['failed_checks'].append('reference_provenance_not_metadata_only')
        rows.append(row)
        if not row['failed_checks']:passing.setdefault(row['repository'],[]).append(path)
    from collections import Counter
    result={'freeze':args.freeze,'input_sha256':hashes,'population_entries':len(rows),'rows':rows,'passing_repositories':[{'repository':r,'catalog_paths':paths,'workflow_eligible':'unknown','lineage_independence':'unknown'} for r,paths in sorted(passing.items())],
            'passing_repository_count':len(passing),'passing_owner_count':len({r.split('/')[0] for r in passing}),
            'failed_predicate_counts':dict(Counter(e for r in rows for e in r['failed_checks'])),
            'sample_selected':False,'network_requests':0,'application_runs':0,'scientific_cases':0,'scope':'metadata feasibility only; prior metadata exposure and unresolved historical gaps retained'}
    out=ROOT/'results/editability-repairability-metadata-screen-v1';out.mkdir(exist_ok=False)
    (out/'screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['population_entries','passing_repository_count','passing_owner_count','sample_selected']}))
if __name__=='__main__':main()
