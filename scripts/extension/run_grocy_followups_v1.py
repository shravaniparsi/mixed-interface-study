#!/usr/bin/env python3
"""Fresh containers and ephemeral actors for each ordinary continuation branch."""
import argparse,hashlib,json,os,secrets,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/grocy-followup-execution-v1.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    registry=json.loads(REGISTRY.read_text());assert registry['execution_authorized'] is True;unit=next(x for x in registry['units'] if x['id']==a.unit)
    for path,h in {**registry['source_sha256'],**registry['qualification_sha256']}.items():
        if sha(ROOT/path)!=h:raise ValueError('Control source differs: '+path)
    a.output.mkdir(parents=True,exist_ok=False);report={'kind':'grocy_scientific_pair_v1','unit':unit,'registry_sha256':sha(REGISTRY),'source_commit':os.environ['GITHUB_SHA'],'run_identity':os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT'],'status':'incomplete','branches':[],'scientific_case_id':unit['case_id'],'cohort':unit['cohort']};owned=[];commands=[]
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
            branch=a.output/channel;branch.mkdir();name='study-grocy-'+os.environ['GITHUB_RUN_ID']+'-'+unit['id']+'-'+channel;owned.append(name)
            cmd(['docker','run','-d','--name',name,'-p','127.0.0.1:18080:80','-e','TZ=UTC',registry['image_id']])
            deadline=time.monotonic()+240;ready=False
            while time.monotonic()<deadline:
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18080/login',timeout=5) as response:
                        if response.status==200:ready=True;break
                except Exception:pass
                time.sleep(2)
            if not ready:raise RuntimeError('Fresh service did not become ready')
            password=secrets.token_urlsafe(24)
            cmd(['docker','cp','scripts/extension/grocy_actor_v1.php',name+':/tmp/study-actor.php'])
            php=cmd(['docker','exec',name,'sh','-c','command -v php || command -v php85 || command -v php84']).stdout.strip()
            if not php.startswith('/') or '\n' in php:raise ValueError('PHP runtime was not resolved uniquely')
            r=cmd(['docker','exec','-i',name,php,'/tmp/study-actor.php'],private=True,input=json.dumps({'username':'study_actor','password':password}))
            auth=json.loads(next(line[len('STUDY_AUTH='):] for line in r.stdout.splitlines() if line.startswith('STUDY_AUTH=')))
            if 'ADMIN' in auth['permissions']:raise ValueError('Unexpected admin role')
            report['actor_permissions']=auth['permissions']
            env=dict(os.environ);env['STUDY_EPHEMERAL_AUTH']=json.dumps(auth)
            cmd(['node','scripts/extension/grocy_case_v1.mjs','--registry',str(REGISTRY),'--workflow',unit['workflow'],'--channel',channel,'--out',str(branch),'--case',unit['case_id']],env=env,timeout=180,check=False)
            observed=json.loads((branch/'observation.json').read_text());report['branches'].append({'channel':channel,'status':observed['status'],'observation_sha256':sha(branch/'observation.json')})
            cmd(['docker','rm','-f','-v',name]);owned.remove(name)
        values=[json.loads((a.output/c/'observation.json').read_text()) for c in unit['branch_order']]
        report['comparability']={key:values[0].get(key)==values[1].get(key) for key in ('initial_business_state','fixture_ids','prefix_status','prefix')}
        report['status']='pair_observed' if all(v['status']=='observed' and v['browser_cleanup_confirmed'] for v in values) and all(report['comparability'].values()) else 'incomplete'
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
    return 0 if report['status']=='pair_observed' and report['cleanup_confirmed'] else 1
if __name__=='__main__':raise SystemExit(main())
