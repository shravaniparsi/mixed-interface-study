#!/usr/bin/env python3
"""Prepare only the pinned backend and existing Python lock for a SQLite diagnostic."""
import argparse,json,os,subprocess,sys,hashlib
from pathlib import Path
from prepare_realworld import BACKEND,checkout,run,PROJECT


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args()
    if sys.version_info[:2]!=(3,12):raise RuntimeError('Python 3.12 required')
    root=args.runtime.resolve();root.mkdir(parents=True,exist_ok=True);subject=root/'realworld-django-ninja';python=root/'venv/bin/python';lock=PROJECT/'manifests/realworld-python-lock.txt'
    report={'backend_commit':BACKEND[1],'python_lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),'application_source_modified':False,'status':'preparing'}
    try:
        checkout(subject,BACKEND);run([sys.executable,'-m','venv',root/'venv'],root,timeout=60)
        run([python,'-m','pip','install','--no-cache-dir','--report',args.report.with_name('diagnostic-pip-install.json'),'-r',lock],root)
        run(['git','diff','--exit-code','HEAD','--'],subject,timeout=30)
        report['resolved_python_packages']=subprocess.check_output([python,'-m','pip','freeze','--all'],text=True).splitlines()
        report.update(status='prepared_not_started',subject=str(subject),python=str(python))
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
