#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'results/development-spec-startup-v2-ci-44089249914'
OUT=ROOT/'manifests/development-spec-startup-v2.json'
def build():
    run=json.loads((D/'run.json').read_text());m=json.loads((D/'measurement.json').read_text())
    assert run['id']==44089249914 and run['head_sha']=='168de73dc86fd6a8e474d62cf25f089051dd40ab'
    assert run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
    assert m['jar_sha256']=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
    assert m['status']=='specification_obtained' and m['readiness_response_observed']
    assert m['process_exit_before_cleanup'] is None and m['final_process_exit']==143
    assert json.loads((D/'harness-exit.json').read_text())['harness_exit']==0
    assert {r['ifname'] for r in json.loads((D/'interfaces.json').read_text())}=={'lo'}
    assert 'Temurin-17.0.2+8' in (D/'java-version.txt').read_text()
    image=json.loads((D/'elasticsearch-image.json').read_text())[0]
    container=json.loads((D/'elasticsearch-container.json').read_text())[0]
    assert container['Image']==image['Id'] and container['HostConfig']['NetworkMode']=='none'
    assert json.loads((D/'elasticsearch-pull-exit.json').read_text())['pull_exit']==0
    readiness=(D/'elasticsearch-readiness.txt').read_text().splitlines()
    assert len(readiness)<=60 and readiness[-1].split()[1:]==['0','200']
    index=readiness[-1].split()[0]
    assert json.loads((D/('elasticsearch-health-'+index+'.json')).read_text())['version']['number']=='7.17.4'
    specs=[];docs=[]
    for r in m['requests']:
        if 'body_file' in r:
            body=(D/r['body_file']).read_bytes();assert len(body)==r['bytes']
            assert hashlib.sha256(body).hexdigest()==r['sha256']
        if not r['label'].startswith('health-'):
            docs.append({'path':r['path'],'http_status':r.get('http_status')})
            if r.get('obtained_specification'):
                d=json.loads(body)
                assert r['http_status']==200 and isinstance(d['openapi'],str) and isinstance(d['paths'],dict) and d['paths']
                specs.append(dict(path=r['path'],body_file=r['body_file'],sha256=r['sha256'],openapi=d['openapi'],path_count=len(d['paths'])))
    assert [d['path'] for d in docs]==['/v3/api-docs','/v3/api-docs/default','/v3/api-docs/swagger-config']
    assert [d['http_status'] for d in docs]==[200,500,500] and len(specs)==1
    return dict(kind='closed_development_specification_availability',run_id=run['id'],freeze=run['head_sha'],
        prior_failed_run=44088230544,artifact_id=14330792705,
        artifact_zip_sha256='429f7a079919773f101b8322752d7baa53740b0dfc1c8c507135eae1b6682181',
        jar_sha256=m['jar_sha256'],image_id=image['Id'],image_repo_digests=image['RepoDigests'],
        documentation_outcomes=docs,obtained_specifications=specs,harness_seconds=m['elapsed_seconds'],
        github_timing=json.loads((D/'timing.json').read_text()),
        full_openapi_schema_validation=False,baseline_qualified=False,independent_evaluation_cases=0,
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(D.iterdir()) if p.is_file()})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Specification availability and retained documentation failures verified')
    else:OUT.write_text(text)
