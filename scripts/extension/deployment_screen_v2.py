#!/usr/bin/env python3
"""Retain bounded deployment probes; these are not application defect experiments."""
import argparse,hashlib,json,os,platform,secrets,signal,subprocess,time,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'manifests/production-extension-screen-v2.json'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--app',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    def interrupted(signum,frame):raise KeyboardInterrupt('Deployment bound reached')
    signal.signal(signal.SIGTERM,interrupted)
    registry=json.loads(REGISTRY.read_text());app=next(x for x in registry['applications'] if x['id']==a.app)
    prior=ROOT/app['prior_failure_report']
    if sha(prior)!=app['prior_failure_sha256'] or json.loads(prior.read_text())['status']!='incomplete':raise ValueError('Prior failure proof differs')
    ephemeral={k:secrets.token_urlsafe(64) for k in app.get('ephemeral_env_names',[])}
    def scrub(text):
        for value in ephemeral.values():text=text.replace(value,'[ephemeral-value-redacted]')
        return text
    out=a.output;out.mkdir(parents=True,exist_ok=False)
    identity=os.environ.get('GITHUB_RUN_ID','local')+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
    prefix='study-ext-'+app['id']+'-'+identity;network=prefix+'-net';owned=[];network_created=False;commands=[]
    started=time.monotonic();report={'kind':'production_deployment_screen_v2','app':app['id'],'application':app,'registry_sha256':sha(REGISTRY),
      'source_sha256':{s:sha(ROOT/s) for s in ['scripts/extension/deployment_screen_v2.py','.github/workflows/production_extension_screen_v2.yml']},
      'run_identity':identity,'source_commit':os.environ.get('GITHUB_SHA'),'started_utc':datetime.now(timezone.utc).isoformat(),
      'redactions':['ephemeral process secrets'],'status':'incomplete','case_outcomes_observed':False,'images':{},'probes':[],
      'host':{'platform':platform.platform(),'logical_cpus':os.cpu_count(),'python':platform.python_version(),
              'image_version':os.environ.get('ImageVersion'),'image_os':os.environ.get('ImageOS')}}
    def run(args,timeout=120,check=True):
        before=time.monotonic()
        try:
            result=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            result.stdout=scrub(result.stdout)
            commands.append({'args':[scrub(x) for x in args],'returncode':result.returncode,'output':result.stdout,'elapsed_s':time.monotonic()-before})
            write(out/'commands.json',commands)
            if check and result.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1])
            return result
        except subprocess.TimeoutExpired as e:
            commands.append({'args':[scrub(x) for x in args],'timeout_s':timeout,'elapsed_s':time.monotonic()-before});write(out/'commands.json',commands);raise
    def image(ref):
        run(['docker','pull','--platform','linux/amd64',ref],timeout=360)
        data=json.loads(run(['docker','image','inspect',ref]).stdout)[0]
        require=bool(data.get('RepoDigests'))
        if not require:raise RuntimeError('Image has no retained registry digest')
        report['images'][ref]={'id':data['Id'],'repo_digests':data['RepoDigests'],'architecture':data['Architecture'],'os':data['Os'],'labels':data['Config'].get('Labels',{}),'size_bytes':data.get('Size')}
        write(out/('image-'+str(len(report['images']))+'.json'),data)
        return data['Id']
    try:
        app_image=image(app['image'])
        dep=app.get('dependency');dep_image=image(dep['image']) if dep else None
        run(['docker','network','create',network]);network_created=True
        if dep:
            name=prefix+'-broker';owned.append(name)
            run(['docker','run','-d','--name',name,'--network',network,'--network-alias',dep['name'],dep_image])
        name=prefix+'-app';owned.append(name)
        args=['docker','run','-d','--name',name,'--network',network,'-p','127.0.0.1:18080:'+str(app['port'])]
        for k,v in sorted({**app['env'],**ephemeral}.items()):args.extend(['-e',k+'='+v])
        args.append(app_image);run(args)
        url='http://127.0.0.1:18080'+app['path'];deadline=time.monotonic()+420
        while time.monotonic()<deadline:
            try:
                with urllib.request.urlopen(url,timeout=10) as response:
                    body=scrub(response.read(2000000).decode('utf8',errors='replace')).encode();status=response.status;final=response.url
                    report['probes'].append({'status':status,'url':url,'final_url':final,'elapsed_s':time.monotonic()-started,'body_sha256':hashlib.sha256(body).hexdigest()})
                    if status==200:
                        (out/'reachable-response.bin').write_bytes(body)
                        write(out/'reachable-response-headers.json',dict(response.headers));report['status']='http_reachable_only';break
            except Exception as error:report['probes'].append({'error':str(error),'elapsed_s':time.monotonic()-started})
            time.sleep(3)
        if report['status']!='http_reachable_only':raise RuntimeError('Deployment did not become HTTP reachable within bound')
    except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        clean=True
        for name in reversed(owned):
            try:
                result=run(['docker','logs',name],check=False);(out/(name+'-logs.txt')).write_text(result.stdout)
                inspect=run(['docker','inspect',name],check=False)
                if inspect.returncode==0:(out/(name+'-inspect.json')).write_text(inspect.stdout)
                run(['docker','rm','-f','-v',name],check=False)
                clean=clean and run(['docker','inspect',name],check=False).returncode!=0
            except Exception as e:clean=False;report.setdefault('cleanup_errors',[]).append(str(e))
        if network_created:
            try:clean=run(['docker','network','rm',network],check=False).returncode==0 and clean
            except Exception as e:clean=False;report.setdefault('cleanup_errors',[]).append(str(e))
        report['cleanup_confirmed']=clean;report['elapsed_s']=time.monotonic()-started
        report['files_sha256']={str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='report.json'}
        write(out/'report.json',report)
    return 0 if report['status']=='http_reachable_only' and report['cleanup_confirmed'] else 1
if __name__=='__main__':raise SystemExit(main())
