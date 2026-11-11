#!/usr/bin/env python3
"""Pinned local API schema capture only; no candidate resource writes or UI reads."""
import argparse,hashlib,json,os,secrets,signal,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--app',choices=['paperless','vikunja','gitea'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();registry=ROOT/'manifests/independent-api-capture-v1.json';reg=json.loads(registry.read_text());app=reg['applications'][a.app];a.output.mkdir(parents=True,exist_ok=False)
    for path,h in reg['source_sha256'].items():
        if sha(ROOT/path)!=h:raise ValueError('Frozen capture source differs: '+path)
    report=dict(kind='independent_api_schema_capture_v1',app=a.app,registry_sha256=sha(registry),run_identity=os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT'],source_commit=os.environ['GITHUB_SHA'],status='incomplete',candidate_resource_writes=0,frontend_inspected=False);owned=[];commands=[];secret_values=[];network=None;prefix='study-schema-'+a.app+'-'+os.environ['GITHUB_RUN_ID']
    def interrupted(signum,frame):raise KeyboardInterrupt('Schema capture bound')
    signal.signal(signal.SIGTERM,interrupted)
    def scrub(s):
        for secret in secret_values:s=s.replace(secret,'[redacted]')
        return s
    def cmd(args,timeout=120,input=None,private=False,check=True):
        start=time.monotonic();r=subprocess.run(args,text=True,input=input,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);commands.append(dict(args=[scrub(x) for x in args],returncode=r.returncode,output='[private authentication output omitted]' if private else scrub(r.stdout),elapsed_s=time.monotonic()-start));write(a.output/'commands.json',commands)
        if check and r.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1])
        return r
    try:
        cmd(['docker','pull','--platform','linux/amd64',app['image']],timeout=360);image=json.loads(cmd(['docker','image','inspect',app['image']]).stdout)[0];assert image['Id']==app['image_id'];report['image']=dict(id=image['Id'],repo_digests=image['RepoDigests'])
        env=dict(app['environment']);args=['docker','run','-d','--name',prefix,'-p','127.0.0.1:18080:'+str(app['port'])];owned.append(prefix)
        if a.app=='paperless':
            network=prefix+'-network';cmd(['docker','network','create',network]);cmd(['docker','pull',app['broker_image']],timeout=360);broker=prefix+'-broker';owned.append(broker);cmd(['docker','run','-d','--name',broker,'--network',network,'--network-alias','broker',app['broker_image']]);args+=['--network',network];secret=secrets.token_urlsafe(64);secret_values.append(secret);env['PAPERLESS_SECRET_KEY']=secret
        args += [item for k,v in env.items() for item in ['-e',k+'='+v]]+[app['image_id']];cmd(args);deadline=time.monotonic()+420
        while True:
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080'+app['ready_path'],timeout=10) as response:
                    if response.status==200:break
            except Exception:pass
            if time.monotonic()>deadline:raise RuntimeError('Service readiness timed out')
            time.sleep(2)
        headers={'Accept':'application/json'}
        if a.app=='paperless':
            password=secrets.token_urlsafe(24);secret_values.append(password)
            setup="import json,sys; from django.contrib.auth.models import User; from rest_framework.authtoken.models import Token; from paperless.version import __full_version_str__; d=json.load(sys.stdin); u=User.objects.create_user(username='schema-reader',password=d['password']); t=Token.objects.create(user=u); print('STUDY_AUTH='+json.dumps({'token':t.key,'version':__full_version_str__,'is_staff':u.is_staff,'is_superuser':u.is_superuser}))"
            r=cmd(['docker','exec','-i',prefix,'python','manage.py','shell','-c',setup],input=json.dumps(dict(password=password)),private=True);auth=json.loads(next(x[len('STUDY_AUTH='):] for x in r.stdout.splitlines() if x.startswith('STUDY_AUTH=')));secret_values.append(auth['token']);assert auth['version']==app['version'] and not auth['is_staff'] and not auth['is_superuser'];report['version']=auth['version'];headers.update(Authorization='Token '+auth['token'],Accept='application/json; version=10')
        request=urllib.request.Request('http://127.0.0.1:18080'+app['schema_path'],headers=headers)
        with urllib.request.urlopen(request,timeout=120) as response:raw=response.read();report['response']=dict(path=app['schema_path'],status=response.status,content_type=response.headers.get('Content-Type'))
        value=json.loads(raw);assert isinstance(value.get('paths'),dict) and ('openapi' in value or 'swagger' in value);(a.output/'schema.json').write_bytes(raw);report['schema_sha256']=sha(a.output/'schema.json');report['path_count']=len(value['paths']);report['status']='schema_captured'
    except BaseException as e:report.update(error_type=type(e).__name__,error=scrub(str(e)))
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);clean=True
        for name in reversed(owned):
            try:cmd(['docker','rm','-f','-v',name],check=False,timeout=30);clean=cmd(['docker','inspect',name],check=False,timeout=10).returncode!=0 and clean
            except Exception:clean=False
        if network:
            try:clean=cmd(['docker','network','rm',network],check=False).returncode==0 and clean
            except Exception:clean=False
        report['cleanup_confirmed']=clean;report['files_sha256']={str(f.relative_to(a.output)):sha(f) for f in a.output.rglob('*') if f.is_file() and f.name!='report.json'};write(a.output/'report.json',report)
    return 0 if report['status']=='schema_captured' and report['cleanup_confirmed'] else 1
if __name__=='__main__':raise SystemExit(main())
