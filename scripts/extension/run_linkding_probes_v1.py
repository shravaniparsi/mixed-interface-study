#!/usr/bin/env python3
"""Fresh containers and ephemeral actors for each ordinary continuation branch."""
import argparse,hashlib,json,os,secrets,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/linkding-extension-probes-v1.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    registry=json.loads(REGISTRY.read_text());unit=next(x for x in registry['units'] if x['id']==a.unit)
    for path,h in registry['source_sha256'].items():
        if sha(ROOT/path)!=h:raise ValueError('Control source differs: '+path)
    a.output.mkdir(parents=True,exist_ok=False);report={'kind':'linkding_ordinary_pair_v3','unit':unit,'registry_sha256':sha(REGISTRY),'source_commit':os.environ['GITHUB_SHA'],'run_identity':os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT'],'status':'incomplete','branches':[],'boundary_cases_executed':0};owned=[];commands=[]
    def interrupted(signum,frame):raise KeyboardInterrupt('Control bound reached')
    signal.signal(signal.SIGTERM,interrupted)
    def cmd(args,timeout=120,private=False,input=None,env=None,check=True):
        start=time.monotonic();r=subprocess.run(args,text=True,input=input,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
        commands.append({'args':args,'returncode':r.returncode,'output':'[ephemeral authentication output omitted]' if private else r.stdout,'elapsed_s':time.monotonic()-start});write(a.output/'commands.json',commands)
        if check and r.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1])
        return r
    try:
        cmd(['docker','pull','--platform','linux/amd64',registry['image']],timeout=360)
        image=json.loads(cmd(['docker','image','inspect',registry['image']]).stdout)[0]
        if image['Id']!=registry['image_id']:raise ValueError('Resolved image differs')
        report['image']={'id':image['Id'],'repo_digests':image['RepoDigests']}
        for channel in unit['branch_order']:
            branch=a.output/channel;branch.mkdir();name='study-linkding-'+os.environ['GITHUB_RUN_ID']+'-'+unit['id']+'-'+channel;owned.append(name)
            cmd(['docker','run','-d','--name',name,'-p','127.0.0.1:18080:9090','-e','LD_DISABLE_BACKGROUND_TASKS=True',registry['image_id']])
            deadline=time.monotonic()+240;ready=False
            while time.monotonic()<deadline:
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18080/login/',timeout=5) as response:
                        if response.status==200:ready=True;break
                except Exception:pass
                time.sleep(2)
            if not ready:raise RuntimeError('Fresh service did not become ready')
            password=secrets.token_urlsafe(24)
            setup="import json,sys; from django.contrib.auth.models import User; from bookmarks.models import ApiToken; d=json.load(sys.stdin); u=User.objects.create_user(username=d['username'],password=d['password']); t=ApiToken.objects.create(user=u,name='study-control'); print('STUDY_AUTH='+json.dumps({'username':u.username,'token':t.key,'password':d['password']}))"
            r=cmd(['docker','exec','-i',name,'python','manage.py','shell','-c',setup],private=True,input=json.dumps({'username':'study_actor','password':password}))
            auth=json.loads(next(line[len('STUDY_AUTH='):] for line in r.stdout.splitlines() if line.startswith('STUDY_AUTH=')))
            env=dict(os.environ);env['STUDY_EPHEMERAL_AUTH']=json.dumps(auth);env['STUDY_PROBE_ID']=unit['probe']
            cmd(['node','scripts/extension/linkding_probe_v1.mjs','--registry',str(REGISTRY),'--workflow',unit['workflow'],'--channel',channel,'--out',str(branch)],env=env,timeout=180)
            observed=json.loads((branch/'observation.json').read_text());report['branches'].append({'channel':channel,'status':observed['status'],'observation_sha256':sha(branch/'observation.json')})
            cmd(['docker','rm','-f','-v',name]);owned.remove(name)
        values=[json.loads((a.output/c/'observation.json').read_text()) for c in unit['branch_order']]
        if not all(v['status']=='ordinary_control_passed' and v['browser_cleanup_confirmed'] for v in values):raise ValueError('Ordinary control failed')
        for key in ('initial_business_state','prefix','final'):
            if values[0][key]!=values[1][key]:raise ValueError('Branch comparability differs: '+key)
        report['status']='ordinary_pair_passed'
    except BaseException as e:report.update(error_type=type(e).__name__,error=str(e))
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);clean=True
        for name in reversed(owned):
            try:
                cmd(['docker','rm','-f','-v',name],timeout=20,check=False)
                clean=cmd(['docker','inspect',name],timeout=10,check=False).returncode!=0 and clean
            except Exception:clean=False
        report['cleanup_confirmed']=clean
        report['files_sha256']={str(f.relative_to(a.output)):sha(f) for f in sorted(a.output.rglob('*')) if f.is_file() and f.name!='report.json'}
        write(a.output/'report.json',report)
    return 0 if report['status']=='ordinary_pair_passed' and report['cleanup_confirmed'] else 1
if __name__=='__main__':raise SystemExit(main())
