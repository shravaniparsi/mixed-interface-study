"""Collect exactly four preregistered development service source files."""
import hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    schedule=json.loads((ROOT/'manifests/development-service-source-schedule-v1.json').read_text());partition=(ROOT/'manifests/project-family-partition-v1.json').read_bytes();assert hashlib.sha256(partition).hexdigest()==schedule['partition_sha256'];allowed={r['full_name'] for r in json.loads(partition)['rows'] if r['partition']=='development'}
    assert len(schedule['files'])==4 and all(r['full_name'] in allowed for r in schedule['files'])
    private=Path('/private/tmp/development-service-boundary-v1');private.mkdir(mode=0o700,exist_ok=False);start=time.monotonic();out=dict(rows=[],reserved_source_reads=0)
    for index,item in enumerate(schedule['files'],1):
        row=dict(item,index=index,status='not_run');out['rows'].append(row)
        try:
            if time.monotonic()-start>=120:raise RuntimeError('deadline')
            url='https://raw.githubusercontent.com/'+item['full_name']+'/'+item['commit']+'/'+urllib.parse.quote(item['path'],safe='/');row['url']=url
            with urllib.request.urlopen(url,timeout=min(30,max(0.1,120-(time.monotonic()-start)))) as response:raw=response.read(256*1024+1)
            if len(raw)>256*1024:raise ValueError('256KiB bound')
            p=private/(str(index)+'.ts');p.write_bytes(raw);p.chmod(0o600);sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),observed_blob_sha=sha)
            if sha!=item['blob_sha']:raise ValueError('blob integrity mismatch')
            row['status']='verified'
        except Exception as error:row.update(status='error',error_type=type(error).__name__,message=str(error))
        finally:out['elapsed_seconds']=time.monotonic()-start;p=private/'collection.json';p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o600)
    print(json.dumps(dict(statuses=[r['status'] for r in out['rows']])))
if __name__=='__main__':main()
