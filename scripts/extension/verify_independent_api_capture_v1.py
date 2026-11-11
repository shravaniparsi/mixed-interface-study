#!/usr/bin/env python3
"""Verify API-only capture provenance and pinned-image evidence."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def build(root,registry):
    registry=Path(registry).resolve();root=Path(root).resolve();reg=read(registry);records={};runs=set()
    for p,h in reg['source_sha256'].items():assert sha(ROOT/p)==h,p
    for p in Path(root).rglob('report.json'):
        r=read(p);app=r['app'];assert app in reg['applications'] and app not in records;assert r['registry_sha256']==sha(registry);runs.add(r['run_identity'])
        for f,h in r['files_sha256'].items():assert sha(p.parent/f)==h,f
        qualified=r['status']=='schema_captured' and r['cleanup_confirmed'];assert r['candidate_resource_writes']==0 and r['frontend_inspected'] is False
        if qualified:
            spec=read(p.parent/'schema.json');assert r['image']['id']==reg['applications'][app]['image_id'];assert sha(p.parent/'schema.json')==r['schema_sha256'];assert len(spec['paths'])==r['path_count'] and r['response']['status']==200
        records[app]=dict(qualified=qualified,report=str(p.relative_to(ROOT)),report_sha256=sha(p),schema=str((p.parent/'schema.json').relative_to(ROOT)) if qualified else None,schema_sha256=r.get('schema_sha256'),path_count=r.get('path_count'),schema_info_version=spec.get('info',{}).get('version') if qualified else None,application_version=reg['applications'][app]['version'],source_commit=r['source_commit'])
    assert set(records)==set(reg['applications']) and len(runs)==1
    return dict(kind='independent_api_capture_results_v1',registry=str(Path(registry).relative_to(ROOT)),registry_sha256=sha(registry),verifier_sha256=sha(__file__),run_identity=next(iter(runs)),records=records)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();v=build(a.root,a.registry);assert not a.output.exists();a.output.write_text(json.dumps(v,indent=2)+'\n');print({k:x['qualified'] for k,x in v['records'].items()})
