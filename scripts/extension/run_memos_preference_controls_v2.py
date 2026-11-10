#!/usr/bin/env python3
"""Fresh containers and ephemeral actors for each ordinary continuation branch."""
import argparse,hashlib,json,os,secrets,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/memos-preference-controls-v2.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    registry=json.loads(REGISTRY.read_text());unit=next(x for x in registry['units'] if x['id']==a.unit)
    for path,h in {**registry['source_sha256'],**registry['qualification_sha256']}.items():
        if sha(ROOT/path)!=h:raise ValueError('Control source differs: '+path)
    a.output.mkdir(parents=True,exist_ok=False);report={'kind':'memos_ordinary_pair_v1','unit':unit,'registry_sha256':sha(REGISTRY),'source_commit':os.environ['GITHUB_SHA'],'run_identity':os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT'],'status':'incomplete','branches':[],'boundary_cases_executed':0};owned=[];commands=[]
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
            branch=a.output/channel;branch.mkdir();name='study-memos-'+os.environ['GITHUB_RUN_ID']+'-'+unit['id']+'-'+channel;owned.append(name)
            cmd(['docker','run','-d','--name',name,'-p','127.0.0.1:18080:5230','-e','TZ=UTC',registry['image_id']])
            deadline=time.monotonic()+240;ready=False
            while time.monotonic()<deadline:
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18080/api/instance/profile',timeout=5) as response:
                        if response.status==200:ready=True;break
                except Exception:pass
                time.sleep(2)
            if not ready:raise RuntimeError('Fresh service did not become ready')
            password=secrets.token_urlsafe(24)
            env=dict(os.environ);env['STUDY_EPHEMERAL_PASSWORD']=password
            cmd(['node','scripts/extension/memos_preference_control_v2.mjs','--registry',str(REGISTRY),'--workflow',unit['workflow'],'--channel',channel,'--out',str(branch)],env=env,timeout=180)
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
