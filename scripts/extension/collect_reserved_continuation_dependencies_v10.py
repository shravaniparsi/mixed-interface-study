#!/usr/bin/env python3
"""Read only pre-scheduled pinned blobs, retain failures, never execute source."""
import argparse,hashlib,json,os,subprocess,time,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--freeze',required=True);a=p.parse_args()
os.umask(0o077);a.out.mkdir(exist_ok=False)
schedule=json.loads((ROOT/'manifests/reserved-continuation-dependency-schedule-v10.json').read_text());result={'freeze':a.freeze,'kind':'reserved_dependency_collection','rows':[]};start=time.monotonic();idx=0
for project in schedule['rows']:
 for item in project['files']:
  idx+=1;row={'index':idx,'repository':project['full_name'],'revision':project['commit'],**item};result['rows'].append(row)
  if not item['eligible_bytes']:row['status']='oversized_not_read'
  elif time.monotonic()-start>=900:row['status']='deadline_not_run'
  else:
   dest=a.out/(str(idx)+'.txt');url='https://raw.githubusercontent.com/'+project['full_name']+'/'+project['commit']+'/'+urllib.parse.quote(item['path'],safe='/')
   try:
    proc=subprocess.run(['curl','--fail','--silent','--show-error','--max-time',str(min(30,max(1,int(900-(time.monotonic()-start))))),'--max-filesize','262144','--output',str(dest),url],capture_output=True,text=True,timeout=32)
    row['exit_code']=proc.returncode
    if proc.returncode:row.update(status='retrieval_failed',error=proc.stderr[:1000])
    else:
     raw=dest.read_bytes();assert len(raw)<=262144
     blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
     assert blob==item['blob_sha'],'Pinned blob identity mismatch'
     row.update(status='retrieved',sha256=hashlib.sha256(raw).hexdigest(),actual_bytes=len(raw))
   except Exception as e:row.update(status='collection_error',error=str(e))
  (a.out/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({'index':idx,'repository':row['repository'],'status':row['status']}),flush=True)
result['elapsed_seconds']=time.monotonic()-start
(a.out/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
