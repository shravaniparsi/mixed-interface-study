#!/usr/bin/env python3
"""Join exact fixture, schema and HTTP evidence without rerunning experiments."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'results/development-fixture-http-v1-ci-44100132954'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    inputs=ROOT/'results/development-test-serialization-v1/measurement.json'
    fixtures=read(inputs);schema=read(ROOT/'results/development-fixture-schema-v1/measurement.json');http=read(ARCHIVE/'measurement.json')
    assert schema['input_sha256']==http['input_sha256']==digest(inputs)
    assert len(fixtures['rows'])==len(schema['rows'])==len(http['rows'])==5 and not http['errors']
    assert http['specification']['body_sha256']==digest(ARCHIVE/'openapi.body')=='2c8546ccc3d04eb7166aec4a10aea1434a89a25ea3f78188bd3df5d0b8231af1'
    assert {i['ifname'] for i in read(ARCHIVE/'interfaces.json')}=={'lo'}
    image=read(ARCHIVE/'elasticsearch-image.json')[0]
    assert any(x.endswith('@sha256:b3fed35f7a43a3e16aa037bf9c8cb8139d1eec879ab5616f3c20746484de4010') for x in image['RepoDigests'])
    assert read(ARCHIVE/'harness-exit.json')['harness_exit']==0
    rows=[]
    for i,(f,s,h,expected) in enumerate(zip(fixtures['rows'],schema['rows'],http['rows'],[201,400,400,400,400])):
        assert f['id']==s['id']==h['id']
        assert f['body_sha256']==s['body_sha256']==h['request_sha256']==digest(ARCHIVE/(str(i)+'-request.body'))
        assert h['status']=='measured' and h['request_attempted'] and h['process_exit_after_cleanup']==143
        assert any(p.get('http_status')==200 for p in h['health_probes'])
        assert h['body_sha256']==digest(ARCHIVE/h['body_file'])
        rows.append({'id':f['id'],'schema_verdict':s['verdict'],'http_status':h['http_status'],'original_asserted_status':expected,'status_matches_assertion':h['http_status']==expected,'request_sha256':f['body_sha256']})
    run=read(ARCHIVE/'github-run.json');timing=read(ARCHIVE/'github-timing.json');artifact=read(ARCHIVE/'github-artifact.json')
    assert run['id']==44100132954 and run['conclusion']=='success' and run['head_sha']=='2e75736c98e0b9c0bc0bf65bee74a3a618231f9b'
    assert artifact['digest']=='sha256:a73f2dc31a9fbad6ab1f791e805326518715deb5b1c481949354778f1bb436ad'
    return {'kind':'closed_development_fixture_schema_http_comparison','freeze':run['head_sha'],'run_id':run['id'],'artifact_digest':artifact['digest'],'rows':rows,'http_status_matches':sum(r['status_matches_assertion'] for r in rows),'schema_accepted_http_rejected':sum(r['schema_verdict']=='satisfied' and r['http_status']==400 for r in rows),'http_elapsed_seconds':http['elapsed_seconds'],'reported_ubuntu_billable_ms':timing['billable']['UBUNTU']['total_ms'],'persistence_verified':False,'candidate_method_evaluated':False,'independent_evaluation_cases':0,'applications':1,'artifact_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sorted(ARCHIVE.iterdir()) if p.is_file()}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/development-fixture-comparison-v1.json'
    if a.verify:assert read(out)==d;print('Five fixture/schema/HTTP joins and archive checks verified.')
    else:out.write_text(json.dumps(d,indent=2)+'\n');print('Recorded five HTTP outcomes; three schema-accepted requests rejected by backend.')
