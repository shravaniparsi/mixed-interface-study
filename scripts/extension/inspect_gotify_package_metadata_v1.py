"""Bounded, one-shot registry metadata inspection; no layers or execution."""
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/maintained-gotify-package-metadata-v1'
MANIFEST=ROOT/'manifests/maintained-gotify-package-metadata-v1.json'
SOURCE='01086b95a8b69ee87383f6e8bcae601d8c33384b'
ACCEPT=', '.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def main():
    if OUT.exists() or MANIFEST.exists():
        raise SystemExit('Refusing to repeat collection')
    OUT.mkdir(parents=True)
    opener=urllib.request.build_opener(NoRedirect())
    events=[]
    result=dict(kind='maintained_gotify_package_metadata',protocol_freeze='5c230a550222c1a98775b0bd766dfd613291d7bd',image='ghcr.io/gotify/server:master',source_commit=SOURCE,requests=events,application_executed=False,layers_downloaded=False)
    def request(url,stage,token=None,expected=None,secret=False):
        if len(events)>=5:raise ValueError('Request cap reached')
        headers={'Accept':ACCEPT,'User-Agent':'mixed-interface-study'}
        if token:headers['Authorization']='Bearer '+token
        req=urllib.request.Request(url,headers=headers)
        event={'stage':stage};events.append(event)
        try:
            response=opener.open(req,timeout=30)
        except urllib.error.HTTPError as exc:
            response=exc
        with response:
            data=response.read(2*1024*1024+1)
            event.update(status=response.code,bytes=len(data),content_type=response.headers.get('Content-Type'))
            digest=response.headers.get('Docker-Content-Digest')
        if not secret:
            path=OUT/(stage+'.json');path.write_bytes(data)
            event.update(archive=str(path.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest())
            if digest:event['reported_digest']=digest
        if len(data)>2*1024*1024:raise ValueError(stage+': oversized response')
        if expected and 'sha256:'+hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError(stage+': descriptor digest mismatch')
        return event['status'],data
    try:
        url='https://ghcr.io/v2/gotify/server/manifests/master'
        status,raw=request(url,'tag-anonymous')
        token=None
        if status==401:
            status,authraw=request('https://ghcr.io/token?scope=repository%3Agotify%2Fserver%3Apull&service=ghcr.io','anonymous-pull-token',secret=True)
            if status!=200:raise ValueError('Anonymous token unavailable')
            token=json.loads(authraw)['token'];del authraw
            status,raw=request(url,'tag-authenticated',token)
        if status!=200:raise ValueError('Tag response status '+str(status))
        result['tag_digest']='sha256:'+hashlib.sha256(raw).hexdigest()
        manifest=json.loads(raw)
        if 'manifests' in manifest:
            candidates=sorted([r for r in manifest['manifests'] if r.get('platform',{}).get('os')=='linux' and r.get('platform',{}).get('architecture')=='amd64' and not r.get('platform',{}).get('variant')],key=lambda r:r['digest'])
            result['linux_amd64_candidates']=candidates
            if not candidates:raise ValueError('No linux/amd64 manifest')
            digest=candidates[0]['digest']
            if not digest.startswith('sha256:'):raise ValueError('Unsupported manifest digest')
            status,raw=request('https://ghcr.io/v2/gotify/server/manifests/'+digest,'platform-manifest',token,expected=digest)
            if status!=200:raise ValueError('Platform manifest unavailable')
            manifest=json.loads(raw)
        result['manifest_digest']='sha256:'+hashlib.sha256(raw).hexdigest()
        digest=manifest['config']['digest']
        if not digest.startswith('sha256:'):raise ValueError('Unsupported config digest')
        status,raw=request('https://ghcr.io/v2/gotify/server/blobs/'+digest,'image-config',token)
        if status!=200:raise ValueError('Config unavailable; redirects are not followed: '+str(status))
        if 'sha256:'+hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Config descriptor digest mismatch')
        config=json.loads(raw)
        result.update(config_digest=digest,os=config.get('os'),architecture=config.get('architecture'),labels=config.get('config',{}).get('Labels',{}))
        if result['os']!='linux' or result['architecture']!='amd64':raise ValueError('Config platform mismatch')
        revision=result['labels'].get('org.opencontainers.image.revision')
        result['status']='declared_revision_match' if revision==SOURCE else ('revision_missing' if not revision else 'revision_mismatch')
    except Exception as exc:
        result.update(status='unavailable',error_type=type(exc).__name__,error=str(exc))
    MANIFEST.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result.get(k) for k in ('status','error','manifest_digest','config_digest','labels')},indent=2))

if __name__=='__main__':
    main()
