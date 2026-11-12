#!/usr/bin/env python3
"""Run one frozen repetition with fresh containers and retained partial evidence."""
import argparse,hashlib,json,os,runpy,shutil,signal,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
IMAGE='am1n3e/webarena-verified-gitlab@sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
def main():
    p=argparse.ArgumentParser();p.add_argument('--repetition',type=int,choices=[1,2],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    reg=json.loads((ROOT/'manifests/benchmark-gitlab-issue-execution-v1.json').read_text())
    for name,digest in reg['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert json.loads((ROOT/'manifests/benchmark-gitlab-issue-controls-v1.json').read_text())['ordinary_triple_qualified']
    a.out.mkdir(parents=True,exist_ok=True)
    report={'kind':'benchmark_gitlab_issue_batch_v1','repetition':a.repetition,'status':'incomplete','executions':[],'image':IMAGE,'source_commit':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID']}
    def save():(a.out/'batch.json').write_text(json.dumps(report,indent=2)+'\n')
    def interrupted(signum,frame):raise KeyboardInterrupt('Batch timeout')
    signal.signal(signal.SIGTERM,interrupted)
    network='study-issue-scientific-'+str(a.repetition);owned=None;credential_path=None
    def command(args,timeout=60,log=None,check=True):
        if log:
            with log.open('w') as stream:r=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,text=True)
        else:r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        if check and r.returncode:raise RuntimeError('Command failed: '+args[0])
        return r
    def ns(pid,args):return ['sudo','nsenter','--target',str(pid),'--net','--']+args
    try:
        assert shutil.disk_usage('/').free>=70000000000
        command(['docker','pull',IMAGE],timeout=900,log=a.out/'pull.log')
        image=command(['docker','image','inspect',IMAGE,'--format','{{json .RepoDigests}} {{.Id}}']).stdout.strip();(a.out/'image-identity.txt').write_text(image+'\n')
        command(['docker','network','create','--internal',network])
        credentials=runpy.run_path(str(ROOT/'scripts/extension/qualify_benchmark_gitlab_auth_v1.py'))['benchmark_credentials']()
        fd,filename=tempfile.mkstemp(prefix='study-gitlab-credentials-');credential_path=Path(filename)
        with os.fdopen(fd,'w') as stream:json.dump(credentials,stream)
        del credentials
        schedule=next(s for s in reg['schedules'] if s['repetition']==a.repetition)['executions']
        for index,item in enumerate(schedule):
            assert shutil.disk_usage('/').free>=35000000000,'Insufficient fresh-container headroom'
            folder=a.out/f'{index:02d}';folder.mkdir();owned=f'study-issue-r{a.repetition}-{index}'
            entry=dict(item,index=index,folder=folder.name,status='starting');report['executions'].append(entry);save()
            cid=command(['docker','run','-d','--name',owned,'--network',network,'--memory','10g','--cpus','4',IMAGE],timeout=180).stdout.strip()
            entry['container_id']=cid;save()
            pid=command(['docker','inspect',owned,'--format','{{.State.Pid}}']).stdout.strip()
            command(ns(pid,['/usr/bin/python3',str(ROOT/'scripts/extension/wait_benchmark_gitlab_ready_v1.py'),str(folder/'readiness.json')]),timeout=620,log=folder/'readiness.log')
            argv=ns(pid,['env','PLAYWRIGHT_MODULE_PATH='+os.environ['PLAYWRIGHT_MODULE_PATH'],'CHROME_EXECUTABLE='+os.environ['CHROME_EXECUTABLE'],shutil.which('node'),str(ROOT/'scripts/extension/run_benchmark_gitlab_issue_case_v1.mjs'),'--credentials',str(credential_path),'--out',str(folder),'--branch',item['branch'],'--case',item['case_id']])
            try:
                response=command(argv,timeout=90,log=folder/'case.log',check=False);entry['process_exit_code']=response.returncode
            except subprocess.TimeoutExpired:
                entry['process_timeout']=True;save();raise
            command(['docker','rm','-f','-v',owned],timeout=60);entry['container_removed']=True;owned=None
            case_path=folder/'issue-case.json';entry['status']='recorded' if case_path.exists() else 'missing_case_evidence'
            if case_path.exists():
                case=json.loads(case_path.read_text());entry['case_passed']=case['case_passed']
                entry['scientific_production_attempted']=case['scientific_cases_executed']
                entry['browser_cleanup_confirmed']=case.get('browser_cleanup_confirmed',False)
            save()
            assert entry.get('browser_cleanup_confirmed'), 'Browser cleanup not established; stop before another fresh case'
            if item['role']=='control' and not entry.get('case_passed'):
                report['status']='control_failed';save();return
        report['status']='completed';save()
    except BaseException as exc:report['error_type']=type(exc).__name__;report['status']='infrastructure_or_instrument_abort';save();raise
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        if owned:command(['docker','rm','-f','-v',owned],timeout=60,check=False)
        command(['docker','network','rm',network],timeout=30,check=False)
        if credential_path:credential_path.unlink(missing_ok=True)
        save()
if __name__=='__main__':main()
