#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'results/development-native-login-v1-ci-44103015430'
def read(name):return json.loads((ARCHIVE/name).read_text())
def build():
    ui=read('native-login.json');runtime=read('measurement.json');browser=read('browser.json');run=read('github-run.json');artifact=read('github-artifact.json');timing=read('github-timing.json')
    assert run['id']==44103015430 and run['conclusion']=='success' and run['head_sha']=='196530e3948ac4aa7198f395024e43feba229f4c'
    assert artifact['digest']=='sha256:543cc320b9bef29fdf6fb84a99b30af5e5918fd1c8cd8b4f8f9f6c5864961cdc'
    assert runtime['status']=='native_login_qualified' and runtime['browser_exit']==0 and runtime['final_process_exit']==143
    assert runtime['jar_sha256']=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
    assert {r['ifname'] for r in read('interfaces.json')}=={'lo'}
    assert any(x.endswith('@sha256:b3fed35f7a43a3e16aa037bf9c8cb8139d1eec879ab5616f3c20746484de4010') for x in read('elasticsearch-image.json')[0]['RepoDigests'])
    assert ui['status']=='qualified' and ui['authentication_posts']==1 and ui['account_login']=='user'
    assert ui['authentication_status']==ui['account_status']==200
    assert ui['node']=='v20.20.2' and ui['browser_version']==browser['declared']['browserVersion']=='151.0.7922.34'
    assert browser['playwright']=='1.62.1' and browser['declared']['revision']=='1234'
    writes=[r for r in ui['responses'] if r['method'] not in ['GET','HEAD']]
    assert writes==[{'path':'/api/authenticate','status':200,'method':'POST'}]
    assert ui['business_object_writes']==ui['independent_evaluation_cases']==0
    for name in ['before-login.png','after-login.png']:assert (ARCHIVE/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    return {'kind':'closed_native_browser_login_control','freeze':run['head_sha'],'run_id':run['id'],'status':'qualified','account_login':'user','authentication_posts':1,'application_elapsed_seconds':runtime['elapsed_seconds'],'reported_ubuntu_billable_ms':timing['billable']['UBUNTU']['total_ms'],'page_errors':ui['page_errors'],'blocked_requests':ui['blocked'],'request_failures':ui['request_failures'],'business_object_writes':0,'api_to_ui_transition_measured':False,'independent_evaluation_cases':0,'artifact_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ARCHIVE.iterdir()) if p.is_file()}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/development-native-login-v1.json'
    if a.verify:assert json.loads(out.read_text())==d;print('Original browser login, account identity and archive identities verified.')
    else:out.write_text(json.dumps(d,indent=2)+'\n');print('Recorded successful ordinary native-login control; no business-object transition.')
