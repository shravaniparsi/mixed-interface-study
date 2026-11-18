"""Prepared combined-job Maxun controls; separate execution freeze required."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from maxun_snapshot_v1 import VolumeSnapshots, file_sha

NETWORK = 'study-maxun-network'
NAMES = {role: 'study-maxun-' + role for role in ['postgres','minio','backend','frontend']}


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Only registered CI control jobs may execute')
    out = Path(os.environ['RUNNER_TEMP']) / 'evidence'
    work = out / 'maxun-controls-work'
    work.mkdir()  # Refuse repeats in one job.
    deadline = float(os.environ['STUDY_JOB_DEADLINE']) - 60
    result = {'status':'unavailable','scientific_cases':0,'arms':[], 'application_snapshots':{}}
    build = json.loads((out / 'maxun-build.json').read_text())
    if build['status'] != 'built':
        raise SystemExit('No successful frozen source build')
    images = {role:build[role+'_image_id'] for role in ['backend','frontend']}
    infrastructure = json.loads((out / 'maxun-runtime-images.json').read_text())
    for role, repository in [('postgres','postgres'),('minio','minio/minio')]:
        digest = infrastructure[role]['digest']
        if not re.fullmatch(re.escape(repository)+r'@sha256:[0-9a-f]{64}',digest):
            raise ValueError('Unpinned persistence image')
        images[role] = digest
    snapshots = VolumeSnapshots(deadline)
    volumes = []

    def command(args, **kwargs):
        seconds = deadline - time.time()
        if seconds <= 0:
            raise TimeoutError('Shared qualification deadline')
        return subprocess.run(args,check=True,timeout=min(90,seconds),**kwargs)

    def text(args):
        return command(args,capture_output=True,text=True).stdout

    def create(role, image, args):
        command(['docker','create','--name',NAMES[role],'--network',NETWORK,
                 '--network-alias',role,'--security-opt','no-new-privileges']+args+[image],capture_output=True)

    def create_stack(label, application_images):
        destinations = {}
        for role in ['postgres','minio']:
            volume = 'study-maxun-' + label + '-' + role
            command(['docker','volume','create',volume],capture_output=True)
            volumes.append(volume);destinations[role] = volume
        create('postgres',images['postgres'],['-e','POSTGRES_USER=study','-e','POSTGRES_PASSWORD=StudyDatabase2026!',
               '-e','POSTGRES_DB=study','-v',destinations['postgres']+':/var/lib/postgresql/data'])
        # MinIO's original image requires server /data arguments after the image.
        command(['docker','create','--name',NAMES['minio'],'--network',NETWORK,'--network-alias','minio',
                 '--security-opt','no-new-privileges','-e','MINIO_ROOT_USER=studyaccess',
                 '-e','MINIO_ROOT_PASSWORD=StudyObjectStore2026!','-v',destinations['minio']+':/data',
                 images['minio'],'server','/data'],capture_output=True)
        environment = {
          'NODE_ENV':'production','DB_USER':'study','DB_PASSWORD':'StudyDatabase2026!',
          'DB_HOST':'postgres','DB_PORT':'5432','DB_NAME':'study','DB_SSL':'false',
          'JWT_SECRET':'study-jwt-fixture-2026-fixed','SESSION_SECRET':'study-session-fixture-2026-fixed',
          'ENCRYPTION_KEY':'0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
          'MAXUN_TELEMETRY':'false','WORKER_CONCURRENCY':'1','BACKEND_PORT':'8080',
          'BACKEND_URL':'http://localhost:8080','PUBLIC_URL':'http://localhost:5173',
          'MINIO_ENDPOINT':'minio','MINIO_PORT':'9000','MINIO_USE_SSL':'false',
          'MINIO_ACCESS_KEY':'studyaccess','MINIO_SECRET_KEY':'StudyObjectStore2026!',
          'BROWSER_WS_HOST':'browser','BROWSER_WS_PORT':'3001',
        }
        args=['--cap-drop','ALL','-p','127.0.0.1:8080:8080']
        for key,value in environment.items():args += ['-e',key+'='+value]
        create('backend',application_images['backend'],args)
        create('frontend',application_images['frontend'],['--cap-drop','ALL','-p','127.0.0.1:5173:5173',
               '-e','FRONTEND_PORT=5173','-e','VITE_BACKEND_URL=http://localhost:8080'])

    def ready(url):
        until=min(deadline,time.time()+60); observations=[]
        while time.time()<until:
            try:
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=2) as response:
                    observations.append({'status':response.status})
                    if response.status==200:return observations
            except Exception as exc:observations.append({'error':str(exc)})
            time.sleep(1)
        raise RuntimeError('Readiness unavailable: '+json.dumps(observations))

    def start_stack():
        command(['docker','start',NAMES['postgres'],NAMES['minio']],capture_output=True)
        until=min(deadline,time.time()+60)
        while True:
            check=subprocess.run(['docker','exec',NAMES['postgres'],'pg_isready','-U','study','-d','study'],capture_output=True,timeout=5)
            if check.returncode==0:break
            if time.time()>=until:raise RuntimeError('PostgreSQL not ready')
            time.sleep(1)
        minio_info=json.loads(text(['docker','inspect',NAMES['minio']]))[0]
        minio_ip=minio_info['NetworkSettings']['Networks'][NETWORK]['IPAddress']
        ready('http://'+minio_ip+':9000/minio/health/ready')
        command(['docker','start',NAMES['backend'],NAMES['frontend']],capture_output=True)
        ready('http://localhost:8080');ready('http://localhost:5173')
        until=min(deadline,time.time()+60)
        while True:
            logs=command(['docker','logs',NAMES['backend']],capture_output=True,text=True)
            if 'All workers started in main process' in logs.stdout+logs.stderr:break
            if time.time()>=until:raise RuntimeError('Full worker startup not established')
            time.sleep(1)

    def stop_stack(label):
        for role in ['frontend','backend','minio','postgres']:
            command(['docker','stop','-t','20',NAMES[role]],capture_output=True)
            info=snapshots.stopped(NAMES[role])
            (out/(label+'-'+role+'-container.json')).write_text(json.dumps(info,indent=2)+'\n')
            logs=command(['docker','logs',NAMES[role]],capture_output=True,text=True)
            (out/(label+'-'+role+'.log')).write_text(logs.stdout+logs.stderr)
            (out/(label+'-'+role+'-diff.txt')).write_text(text(['docker','diff',NAMES[role]]))

    def remove_stack():
        for name in NAMES.values():command(['docker','rm',name],capture_output=True)

    def arm(label,fixture=None):
        record={'arm':label,'status':'started','started_unix':time.time()};result['arms'].append(record)
        dest=out/label
        args=['node','scripts/extension/qualify_maintained_maxun_v1.mjs','--arm',label,'--out',str(dest)]
        if fixture:args += ['--fixture',str(fixture)]
        with (out/(label+'-adapter.log')).open('wb') as log:
            seconds=deadline-time.time()
            if seconds<=0:raise TimeoutError('Shared qualification deadline')
            process=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=min(180,seconds))
        record['exit_code']=process.returncode
        record['status']=json.loads((dest/'control.json').read_text())['status'] if (dest/'control.json').exists() else 'adapter_unavailable'
        record['finished_unix']=time.time()
        expected='producer_prepared' if label=='producer' else 'ordinary_arm_passed'
        if process.returncode or record['status']!=expected:raise RuntimeError('Ordinary arm unavailable: '+label)

    try:
        command(['docker','network','create','--internal',NETWORK],capture_output=True)
        network=json.loads(text(['docker','network','inspect',NETWORK]))
        if not network[0]['Internal']:raise RuntimeError('Runtime network is not isolated')
        (out/'maxun-network.json').write_text(json.dumps(network,indent=2)+'\n')
        create_stack('native',images);start_stack();arm('ui-ui');stop_stack('native');remove_stack()
        create_stack('producer',images);start_stack();arm('producer');stop_stack('producer')
        source=work/'snapshot'
        captured=snapshots.capture({role:NAMES[role] for role in ['postgres','minio']},source)
        snapshot_manifest_hash=file_sha(source/'snapshot.json')
        checkpoint=dict(images)
        for role in ['backend','frontend']:
            image=text(['docker','commit',NAMES[role]]).strip()
            if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise ValueError('Invalid application snapshot image')
            checkpoint[role]=image
            result['application_snapshots'][role]=json.loads(text(['docker','image','inspect',image]))[0]
        fixture=out/'producer/fixture.json';fixture_hash=file_sha(fixture)
        remove_stack()
        for label in ['api','ui']:
            create_stack(label,checkpoint)
            snapshots.restore(source,{role:NAMES[role] for role in ['postgres','minio']},work/(label+'-restore'))
            if file_sha(fixture)!=fixture_hash:raise RuntimeError('Browser/actor fixture changed')
            start_stack();arm(label,fixture);stop_stack(label);remove_stack()
        # Both branches must have identical complete public application rows,
        # exact numeric representation and fresh full API readback.
        for filename in ['after-readback.json','after-database.json']:
            left=json.loads((out/'api'/filename).read_text());right=json.loads((out/'ui'/filename).read_text())
            if filename=='after-database.json':
                left=[{'schema':t['schema'],'table':t['table'],'rows':t['exact_rows']} for t in left['tables'] if t['schema']=='public']
                right=[{'schema':t['schema'],'table':t['table'],'rows':t['exact_rows']} for t in right['tables'] if t['schema']=='public']
            if left!=right:raise RuntimeError('Continuation results differ: '+filename)
        if file_sha(fixture)!=fixture_hash:raise RuntimeError('Immutable browser fixture changed')
        if file_sha(source/'snapshot.json')!=snapshot_manifest_hash:raise RuntimeError('Snapshot manifest changed')
        for role,volume in captured['volumes'].items():
            if file_sha(source/volume['archive'])!=volume['sha256']:raise RuntimeError('Snapshot archive changed')
        result['status']='ordinary_controls_qualified'
    except Exception as exc:
        result.update(error_type=type(exc).__name__,error=str(exc))
    finally:
        (out/'maxun-controls.json').write_text(json.dumps(result,indent=2)+'\n')
        for name in NAMES.values():
            for action in ['inspect','logs']:
                try:
                    p=subprocess.run(['docker',action,name],capture_output=True,timeout=10)
                    (out/(name+'-final-'+action+'.txt')).write_bytes(p.stdout+p.stderr)
                except subprocess.TimeoutExpired:pass
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15,check=False)
        for volume in volumes:subprocess.run(['docker','volume','rm',volume],capture_output=True,timeout=15,check=False)
        subprocess.run(['docker','network','rm',NETWORK],capture_output=True,timeout=15,check=False)
    raise SystemExit(0 if result['status']=='ordinary_controls_qualified' else 1)


if __name__=='__main__':main()
