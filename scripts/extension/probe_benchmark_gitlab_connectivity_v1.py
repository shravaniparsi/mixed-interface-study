#!/usr/bin/env python3
"""Compare host and container connectivity without retaining response bodies."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--container',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result={'scientific_cases_executed':0,'diagnostic_only':True,'rounds':[]}
    start=time.monotonic()
    for index in range(6):
        rows=[]
        for path in ('/-/health','/users/sign_in'):
            for mode in ('default','no_proxy'):
                row={'vantage':'host','port':8023,'path':path,'proxy_mode':mode}
                client=urllib.request.build_opener(*([urllib.request.ProxyHandler({})] if mode=='no_proxy' else []))
                try:
                    with client.open('http://127.0.0.1:8023'+path,timeout=10) as response:
                        row.update(status=response.status,final_path=urllib.parse.urlsplit(response.url).path)
                except urllib.error.HTTPError as exc:
                    row.update(status=exc.code,error_type=type(exc).__name__)
                except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
                    reason=getattr(exc,'reason',exc)
                    row.update(error_type=type(exc).__name__,reason_type=type(reason).__name__,errno=getattr(reason,'errno',None))
                rows.append(row)
            for port in (8023,80):
                row={'vantage':'container','port':port,'path':path}
                try:
                    proc=subprocess.run(['docker','exec',args.container,'curl','--noproxy','*','-s','-o','/dev/null','--max-time','10','-w','%{http_code}',f'http://127.0.0.1:{port}'+path],capture_output=True,text=True,timeout=15)
                    row.update(exit_code=proc.returncode,status=int(proc.stdout.strip()) if proc.stdout.strip().isdigit() else None)
                except subprocess.TimeoutExpired:
                    row['error_type']='TimeoutExpired'
                rows.append(row)
        result['rounds'].append({'index':index,'elapsed_seconds':round(time.monotonic()-start,3),'observations':rows})
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        if index<5:
            time.sleep(45)
    print('Six connectivity diagnostic rounds retained; no scientific cases.')
if __name__=='__main__':main()
