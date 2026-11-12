#!/usr/bin/env python3
import json,pathlib,sys,time,urllib.request,urllib.error
out=pathlib.Path(sys.argv[1]);start=time.monotonic();attempts=[];ready=False
while time.monotonic()-start<600:
    row={'elapsed_seconds':round(time.monotonic()-start,3)}
    try:
        with urllib.request.urlopen('http://127.0.0.1:8023/-/health',timeout=10) as response:
            row.update(status=response.status,body=response.read(4096).decode(errors='replace'))
        ready=row['status']==200 and row['body'].strip()=='GitLab OK'
    except urllib.error.HTTPError as exc:row.update(status=exc.code,error_type=type(exc).__name__)
    except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:row['error_type']=type(exc).__name__
    attempts.append(row);out.write_text(json.dumps({'ready':ready,'attempts':attempts},indent=2)+'\n')
    if ready:break
    time.sleep(2)
sys.exit(0 if ready else 1)
