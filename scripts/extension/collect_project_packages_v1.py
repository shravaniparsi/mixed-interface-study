"""Fetch only frozen package manifests; parse metadata without running scripts."""
import hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
NAMES=['@angular/core','@angular/forms','@angular/compiler','@angular/cli','angular','react','vue','generator-jhipster','jhipster']
def main():
    schedule=json.loads((ROOT/'manifests/project-package-read-schedule-v1.json').read_text());assert len(schedule['files'])==41
    private=Path('/private/tmp/project-package-screen-v1');private.mkdir(mode=0o700,exist_ok=False);started=time.monotonic()
    result=dict(kind='fixed_package_metadata_screen',rows=[],test_or_implementation_files_read=0)
    def save():
        result['elapsed_seconds']=time.monotonic()-started;p=private/'collection.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
    for index,item in enumerate(schedule['files'],1):
        row=dict(item,index=index,status='unread');result['rows'].append(row)
        if time.monotonic()-started>=180:row.update(status='not_run',reason='deadline');save();continue
        url='https://raw.githubusercontent.com/'+item['full_name']+'/'+item['commit']+'/'+urllib.parse.quote(item['path'],safe='/');row['url']=url
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'mixed-interface-research-package-metadata'})
            with urllib.request.urlopen(request,timeout=min(30,max(0.1,180-(time.monotonic()-started)))) as response:
                raw=response.read(256*1024+1);row['http_status']=response.status;row['response_date']=response.headers.get('Date')
            if len(raw)>256*1024:raise ValueError('256KiB file bound')
            p=private/(str(index)+'.json');p.write_bytes(raw);p.chmod(0o600)
            digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),observed_blob_sha=digest)
            if digest!=item['blob_sha']:raise ValueError('Git blob integrity mismatch')
            row['status']='parse_error'
            data=json.loads(raw)
            if not isinstance(data,dict):raise ValueError('manifest is not a JSON object')
            declarations={section:{name:values[name] for name in NAMES if name in values} for section in ['dependencies','devDependencies','peerDependencies','optionalDependencies'] if isinstance((values:=data.get(section)),dict)}
            row.update(status='parsed',metadata={k:data[k] for k in ['name','private','license','engines','workspaces'] if k in data},script_names=sorted(data.get('scripts',{})) if isinstance(data.get('scripts'),dict) else [],framework_declarations=declarations)
            angular=[values['@angular/core'] for values in declarations.values() if '@angular/core' in values]
            row['angular_core_declarations']=angular;row['qualification_signal']='exact_declaration_only' if '22.2.3' in angular else 'version_unqualified'
        except Exception as error:
            if row['status']!='parse_error':row['status']='fetch_or_integrity_error'
            row.update(error_type=type(error).__name__,message=str(error))
        save()
    result['status']='closed';save()
    from collections import Counter
    print(json.dumps(dict(rows=len(result['rows']),statuses=dict(Counter(r['status'] for r in result['rows'])))))
if __name__=='__main__':main()
