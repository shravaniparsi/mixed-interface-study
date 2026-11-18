"""Private inventory and cleanup of only the disposable SeatSurfing fixture."""
import json
from pathlib import Path
import subprocess
from seatsurfing_postgres_checkpoint_v2 import APP, PG, BROWSER
from provision_seatsurfing_ordinary_v1 import VOLUME

LABEL_KEY='org.mixed-interface.study'
LABEL_VALUE='seatsurfing-qualification-v1'
NAMES={APP,PG,BROWSER,'study-seatsurfing-tools-install','study-seatsurfing-transport-calibration',
       'study-seatsurfing-schema-probe','study-seatsurfing-api-ordinary-create',
       'study-seatsurfing-api-independent-load','study-seatsurfing-api-ordinary-continue'}


def verify_inventory(items):
    owned={}
    for item in items:
        name=item['Name'].lstrip('/')
        labelled=(item['Config'].get('Labels') or {}).get(LABEL_KEY)==LABEL_VALUE
        if name in NAMES and not labelled:raise ValueError('Named fixture resource has different ownership')
        if labelled:
            if name not in NAMES:raise ValueError('Unexpected study-labelled client/resource')
            if name in owned:raise ValueError('Duplicate resource name')
            owned[name]=item
    # Reject an unregistered client that shares, or joins via a container that
    # shares, the original isolated namespace. Other CI containers are untouched.
    aliases={PG}
    if PG in owned:aliases.add(owned[PG]['Id'])
    changed=True
    while changed:
        changed=False
        for item in items:
            mode=item['HostConfig']['NetworkMode']
            if mode.startswith('container:') and mode[len('container:'):] in aliases:
                name=item['Name'].lstrip('/')
                if name not in owned:raise ValueError('Unregistered client in fixture network namespace')
                for alias in [name,item['Id']]:
                    if alias not in aliases:aliases.add(alias);changed=True
    return owned


def inspect_resources():
    ids=subprocess.check_output(['docker','ps','-aq'],timeout=15).decode().splitlines()
    if len(ids)>64:raise ValueError('CI container inventory bound')
    if not ids:return {}
    raw=subprocess.check_output(['docker','inspect',*ids],timeout=20)
    if len(raw)>8*1024*1024:raise ValueError('Container inspection evidence bound')
    return verify_inventory(json.loads(raw))


def cleanup_fixture(directory):
    """Caller first stops its coordinator process; never prune shared resources."""
    directory=Path(directory);directory.mkdir(parents=True,mode=0o700,exist_ok=False)
    report={'status':'cleanup_pending','removed_container_ids':[],'volume_removed':False}
    try:
        owned=inspect_resources()
        # Capture pre-cleanup configuration privately, including sensitive env.
        (directory/'container-inspection.json').write_text(json.dumps(owned,indent=2))
        # Stop writers before final log capture. These names and IDs passed the
        # exact ownership inventory; no arbitrary container is selected.
        for name,item in owned.items():
            if item['State']['Running']:
                if item['State'].get('Paused'):
                    subprocess.run(['docker','unpause',item['Id']],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
                result=subprocess.run(['docker','kill',item['Id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
                (directory/(name+'-kill.stdout')).write_bytes(result.stdout);(directory/(name+'-kill.stderr')).write_bytes(result.stderr)
                if result.returncode:raise RuntimeError('Fixture writer stop failed')
        for name,item in owned.items():
            result=subprocess.run(['docker','logs',item['Id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
            (directory/(name+'.stdout')).write_bytes(result.stdout);(directory/(name+'.stderr')).write_bytes(result.stderr)
            if result.returncode or len(result.stdout)+len(result.stderr)>32*1024*1024:raise RuntimeError('Final fixture log observation unavailable')
            current,=json.loads(subprocess.check_output(['docker','inspect',item['Id']],timeout=15))
            if current['State']['Running'] or current['State'].get('Paused'):raise RuntimeError('Fixture writer remains active')
            if verify_inventory([current]).get(name,{}).get('Id')!=item['Id']:raise RuntimeError('Fixture ownership changed')
            subprocess.run(['docker','rm',item['Id']],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
            report['removed_container_ids'].append(item['Id'])
        volumes=subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],timeout=15).decode().splitlines()
        if VOLUME in volumes:
            volume,=json.loads(subprocess.check_output(['docker','volume','inspect',VOLUME],timeout=15))
            if (volume.get('Labels') or {}).get(LABEL_KEY)!=LABEL_VALUE:raise ValueError('Database volume ownership mismatch')
            (directory/'volume-inspection.json').write_text(json.dumps(volume,indent=2))
            subprocess.run(['docker','volume','rm',VOLUME],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
            report['volume_removed']=True
        if inspect_resources():raise RuntimeError('Fixture resources remain after cleanup')
        final_volumes=subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],timeout=15).decode().splitlines()
        if VOLUME in final_volumes:raise RuntimeError('Fixture volume remains after cleanup')
        report['status']='owned_fixture_absent_after_cleanup'
    except Exception as error:
        report.update(status='cleanup_unverified',error_type=type(error).__name__)
        raise
    finally:(directory/'cleanup-result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    import argparse
    import os
    parser=argparse.ArgumentParser();parser.add_argument('--private',type=Path,required=True)
    args=parser.parse_args();os.umask(0o077)
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='shravaniparsi/mixed-interface-study':
        raise RuntimeError('Disposable registered CI fixture only')
    cleanup_fixture(args.private)
