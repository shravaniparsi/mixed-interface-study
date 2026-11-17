#!/usr/bin/env python3
import argparse,base64,hashlib,json,os,signal,subprocess,time,urllib.request,urllib.error
from pathlib import Path
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def main():
    p=argparse.ArgumentParser();p.add_argument('--java',required=True);p.add_argument('--jar',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=Path('results/development-test-serialization-v1/measurement.json').read_bytes();fixtures=json.loads(source)
    encoded=fixtures['commands'][-1]['stdout'].splitlines()
    result={'kind':'fixed_original_fixture_http_qualification','input_sha256':hashlib.sha256(source).hexdigest(),'rows':[{'id':r['id'],'status':'not_run'} for r in fixtures['rows']],'errors':[],'actor':'unauthenticated public registration','persistence_verified':False,'independent_evaluation_cases':0}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def request(path,label,data=None):
        req=urllib.request.Request('http://127.0.0.1:8080'+path,data=data,headers={'Content-Type':'application/json'} if data is not None else {})
        try:r=opener.open(req,timeout=15 if data is not None else 3)
        except urllib.error.HTTPError as e:r=e
        with r:body=r.read(4*1024*1024+1);status=r.code;headers=list(r.headers.items())
        assert len(body)<=4*1024*1024
        (out/(label+'.body')).write_bytes(body)
        return {'http_status':status,'body_file':label+'.body','body_sha256':hashlib.sha256(body).hexdigest(),'headers':headers}
    start=time.monotonic()
    try:
        jar=a.jar.resolve();assert hashlib.sha256(jar.read_bytes()).hexdigest()=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
        interfaces=subprocess.check_output(['ip','-j','link'],text=True);(out/'interfaces.json').write_text(interfaces);assert {r['ifname'] for r in json.loads(interfaces)}=={'lo'}
        v=subprocess.run([a.java,'-version'],capture_output=True,text=True,check=True);(out/'java-version.txt').write_text(v.stdout+v.stderr);assert 'Temurin-17.0.2+8' in v.stdout+v.stderr
        for i,row in enumerate(result['rows']):
            proc=None;log=None;row['health_probes']=[]
            try:
                name,b64=encoded[i].split('\t');assert name==row['id'];body=base64.b64decode(b64,validate=True)
                assert hashlib.sha256(body).hexdigest()==fixtures['rows'][i]['body_sha256']
                row['request_sha256']=hashlib.sha256(body).hexdigest();(out/(str(i)+'-request.body')).write_bytes(body)
                work=out/('runtime-'+str(i));work.mkdir(exist_ok=False)
                log=(out/(str(i)+'-application.log')).open('w')
                proc=subprocess.Popen([a.java,'-Xmx1g','-jar',str(jar),'--spring.profiles.active=dev,api-docs','--server.address=127.0.0.1','--server.port=8080'],cwd=work,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+180;ready=False
                while time.monotonic()<deadline and proc.poll() is None:
                    try:h=request('/management/health',str(i)+'-health-'+str(len(row['health_probes'])));row['health_probes'].append(h);ready=h['http_status']==200
                    except Exception as e:row['health_probes'].append({'error':str(e)})
                    if ready:break
                    time.sleep(5)
                if not ready:raise RuntimeError('Application not ready; exit='+str(proc.poll()))
                if i==0:
                    try:result['specification']=request('/v3/api-docs','openapi')
                    except Exception as e:result['specification']={'error':str(e)}
                row['request_attempted']=True
                row.update(request('/api/register',str(i)+'-response',body));row['status']='measured'
            except Exception as e:row.update(status='error',error_type=type(e).__name__,message=str(e))
            finally:
                if proc is not None and proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
                row['process_exit_after_cleanup']=proc.returncode if proc else None
                if log:log.close()
                (out/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    except Exception as e:result['errors'].append(str(e))
    result['elapsed_seconds']=time.monotonic()-start
    (out/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    return int(bool(result['errors']) or any(r['status']!='measured' for r in result['rows']))
if __name__=='__main__':raise SystemExit(main())
