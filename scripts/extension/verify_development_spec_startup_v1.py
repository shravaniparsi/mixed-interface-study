#!/usr/bin/env python3
"""Verify the closed failed startup without reconstructing or rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'results/development-spec-startup-v1-ci-44088230544'
OUT=ROOT/'manifests/development-spec-startup-v1.json'
def build():
    run=json.loads((D/'run.json').read_text());m=json.loads((D/'measurement.json').read_text())
    assert run['id']==44088230544 and run['head_sha']=='5e6bd059dd2f157a18a7b091fef92f8b46bc3ee9'
    assert run['status']=='completed' and run['conclusion']=='failure' and run['run_attempt']==1
    assert m['jar_sha256']=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
    assert m['status']=='specification_unavailable' and m['process_exit_before_cleanup']==m['final_process_exit']==1
    assert m['readiness_response_observed'] is False
    assert json.loads((D/'harness-exit.json').read_text())['harness_exit']==1
    assert {r['ifname'] for r in json.loads((D/'interfaces.json').read_text())}=={'lo'}
    assert 'Temurin-17.0.2+8' in (D/'java-version.txt').read_text()
    assert len(m['requests'])==2
    assert all(r['path']=='/management/health' and r['error_type']=='URLError' and 'Connection refused' in r['message'] for r in m['requests'])
    log=(D/'application.log').read_text()
    for token in ['Application run failed','userSearchRepository','SimpleElasticsearchRepository','java.net.ConnectException: Connection refused']:assert token in log
    return dict(kind='closed_development_spec_startup_failure',run_id=run['id'],freeze=run['head_sha'],
        artifact_id=14330431787,artifact_zip_sha256='402af58bdd1f277932c3475816edff323c1de56cce97c30404277508da4d3612',
        jar_sha256=m['jar_sha256'],status='startup_failed_before_http_readiness',
        immediate_failure_evidence='Elasticsearch repository initialization connection refused',
        health_probe_count=2,specification_requests_executed=0,specifications_obtained=0,
        harness_seconds=m['elapsed_seconds'],github_timing=json.loads((D/'timing.json').read_text()),
        independent_evaluation_cases=0,baseline_qualified=False,
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(D.iterdir()) if p.is_file()})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:
        assert OUT.read_text()==text
        print('Failed startup evidence and zero executed specification requests verified')
    else:OUT.write_text(text)
