"""Read pinned development lockfile metadata, never resolve/install dependencies."""
import hashlib,json,re,time,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
NAMES=['@angular/forms','@angular/core','@angular/common','@angular/compiler','rxjs','tslib','zone.js']
def records(raw,path):
    text=raw.decode()
    if path.endswith('.json'):
        value=json.loads(text);version=value.get('lockfileVersion');out=[]
        for name in NAMES:
            entry=value.get('packages',{}).get('node_modules/'+name) if version in (2,3) else value.get('dependencies',{}).get(name) if version==1 else None
            out.append(dict(name=name,status='recorded' if entry else 'unresolved',**{k:entry[k] for k in ['version','resolved','integrity'] if entry and k in entry}))
        return dict(format='npm',lockfile_version=version,records=out)
    if path.endswith('yarn.lock') and '# yarn lockfile v1' in text:
        out=[]
        for match in re.finditer(r'(?m)^([^\s#][^\n]*):\n((?:[ \t]+[^\n]*\n|\n)*)',text):
            selector,body=match.groups();tokens=[s.strip().strip('"') for s in selector.split(',')]
            for name in NAMES:
                if any(s.startswith(name+'@') for s in tokens):
                    record=dict(name=name,selector=selector,status='recorded')
                    for key in ['version','resolved','integrity']:
                        m=re.search(r'^  '+key+r' (.+)$',body,re.M)
                        if m:record[key]=m[1].strip().strip('"')
                    out.append(record)
        return dict(format='yarn_v1',records=out,unresolved_names=[n for n in NAMES if not any(r['name']==n for r in out)])
    return dict(format='unsupported',records=[])
def main():
    schedule=json.loads((ROOT/'manifests/development-lockfile-schedule-v1.json').read_text());private=Path('/private/tmp/development-lockfile-screen-v1');private.mkdir(mode=0o700,exist_ok=False);started=time.monotonic();out=dict(rows=[])
    for index,item in enumerate(schedule['rows'],1):
        row=dict(item,index=index);out['rows'].append(row)
        if item['status']=='unavailable':continue
        try:
            if time.monotonic()-started>=120:raise RuntimeError('deadline')
            url='https://raw.githubusercontent.com/'+item['full_name']+'/'+item['commit']+'/'+urllib.parse.quote(item['path'],safe='/');row['url']=url
            with urllib.request.urlopen(url,timeout=min(30,max(0.1,120-(time.monotonic()-started)))) as response:raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024:raise ValueError('8MiB bound')
            p=private/(str(index)+'.lock');p.write_bytes(raw);p.chmod(0o600)
            sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),observed_blob_sha=sha)
            if sha!=item['blob_sha']:raise ValueError('Git blob mismatch')
            row.update(status='parsed',metadata=records(raw,item['path']))
        except Exception as error:row.update(status='error',error_type=type(error).__name__,message=str(error))
        finally:
            out['elapsed_seconds']=time.monotonic()-started;p=private/'collection.json';p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o600)
    print(json.dumps(dict(statuses=[r['status'] for r in out['rows']])) )
if __name__=='__main__':main()
