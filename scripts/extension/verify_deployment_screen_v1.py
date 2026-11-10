#!/usr/bin/env python3
"""Reconstruct a complete deployment screen without promoting it to experiment data."""
import argparse,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(root):
    root=Path(root);registry=ROOT/'manifests/production-extension-screen-v1.json';expected={a['id']:a for a in json.loads(registry.read_text())['applications']};rows={};runs=set();commits=set()
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():raise ValueError('Unexpected archive entry')
        p=folder/'report.json';r=json.loads(p.read_text());app=r['app']
        if app not in expected or app in rows:raise ValueError('Foreign or duplicate application')
        if r['application']!=expected[app] or r['registry_sha256']!=sha(registry):raise ValueError('Registry differs')
        if r['case_outcomes_observed'] is not False:raise ValueError('Deployment cannot claim case outcomes')
        actual={str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and f.name!='report.json'}
        if actual!=r['files_sha256']:raise ValueError('Evidence inventory differs')
        for path,h in r['source_sha256'].items():
            if sha(ROOT/path)!=h:raise ValueError('Screen source differs')
        if r['status']=='http_reachable_only':
            data=folder/'reachable-response.bin'
            if not r['probes'] or r['probes'][-1].get('status')!=200 or r['probes'][-1]['body_sha256']!=sha(data):raise ValueError('Reachability proof absent')
            if not r['images'] or any(not i['repo_digests'] for i in r['images'].values()):raise ValueError('Image identity absent')
        elif r['status']!='incomplete' or 'error' not in r:raise ValueError('Unknown failure status')
        runs.add(r['run_identity']);commits.add(r['source_commit'])
        rows[app]={'status':r['status'],'cleanup_confirmed':r['cleanup_confirmed'],'error':r.get('error'),'images':r['images'],'report_sha256':sha(p)}
    if set(rows)!=set(expected):raise ValueError('Incomplete subject inventory')
    if len(runs)!=1 or len(commits)!=1:raise ValueError('Mixed workflow attempts')
    return {'kind':'verified_production_deployment_screen_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'subjects':rows,'subjects_retained':len(rows),'http_reachable':sum(r['status']=='http_reachable_only' for r in rows.values()),'scientific_case_results':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=verify(a.root)
    if a.output:
        out=Path(a.output)
        if out.exists():raise ValueError('Screen already registered')
        out.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'subjects_retained':v['subjects_retained'],'http_reachable':v['http_reachable'],'scientific_case_results':0}))
