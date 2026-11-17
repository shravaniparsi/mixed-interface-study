"""Read only frozen development source blobs, never imports or held-out sources."""
import hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    schedule=json.loads((ROOT/'manifests/development-form-source-schedule-v1.json').read_text())
    raw_partition=(ROOT/'manifests/project-family-partition-v1.json').read_bytes();assert hashlib.sha256(raw_partition).hexdigest()==schedule['partition_sha256']
    allowed={r['full_name'] for r in json.loads(raw_partition)['rows'] if r['partition']=='development'}
    assert len(schedule['files'])==12 and all(r['full_name'] in allowed for r in schedule['files'])
    private=Path('/private/tmp/development-form-source-screen-v1');private.mkdir(mode=0o700,exist_ok=False);started=time.monotonic();result=dict(kind='development_source_collection',rows=[],reserved_source_reads=0)
    def save():
        result['elapsed_seconds']=time.monotonic()-started;p=private/'collection.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
    for index,item in enumerate(schedule['files'],1):
        row=dict(item,index=index,status='not_run');result['rows'].append(row)
        if time.monotonic()-started>=180:row['reason']='deadline';save();continue
        url='https://raw.githubusercontent.com/'+item['full_name']+'/'+item['commit']+'/'+urllib.parse.quote(item['path'],safe='/');row['url']=url
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'mixed-interface-research-development-source'})
            with urllib.request.urlopen(request,timeout=min(30,max(0.1,180-(time.monotonic()-started)))) as response:raw=response.read(256*1024+1);row['http_status']=response.status
            if len(raw)>256*1024:raise ValueError('256KiB limit')
            p=private/(str(index)+'.txt');p.write_bytes(raw);p.chmod(0o600)
            sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),observed_blob_sha=sha)
            if sha!=item['blob_sha']:raise ValueError('blob integrity mismatch')
            row['status']='verified'
        except Exception as error:row.update(status='error',error_type=type(error).__name__,message=str(error))
        save()
    result['status']='closed';save()
    from collections import Counter
    print(json.dumps(dict(files=len(result['rows']),statuses=dict(Counter(r['status'] for r in result['rows'])))))
if __name__=='__main__':main()
