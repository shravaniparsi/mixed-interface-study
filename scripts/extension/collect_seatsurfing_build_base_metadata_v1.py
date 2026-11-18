#!/usr/bin/env python3
"""Resolve registered public image manifests/configs without pulling layers."""
import argparse
import subprocess
import hashlib
import json
import signal
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-seatsurfing-build-base-metadata-v1'
ACCEPT=','.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])

def deadline(*args):raise TimeoutError('120-second image deadline')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',required=True);args=parser.parse_args()
    assert len(args.freeze)==40 and all(c in '0123456789abcdef' for c in args.freeze)
    names=['protocol/catalog-seatsurfing-build-base-metadata-v1.md','scripts/extension/collect_seatsurfing_build_base_metadata_v1.py']
    hashes={}
    for name in names:
        raw=(ROOT/name).read_bytes()
        assert raw==subprocess.check_output(['git','show',args.freeze+':'+name],cwd=ROOT)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    OUT.mkdir(exist_ok=False);result={'freeze':args.freeze,'artifact_hashes':hashes,'images':[],'status':'in_progress'}
    signal.signal(signal.SIGALRM,deadline)
    for label,repo,tag in [('cross','tonistiigi/xx','latest'),('frontend','library/node','24-alpine'),('backend','library/golang','1.27-bookworm'),('database','library/postgres','18')]:
        directory=OUT/label;directory.mkdir();start=time.monotonic()
        row={'repository':repo,'tag':tag,'status':'unavailable','requests':[],'redirects':[]};result['images'].append(row);signal.alarm(120)
        class BoundedRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                parsed=urlparse(newurl);host=parsed.hostname or ''
                allowed=any(host==suffix or host.endswith('.'+suffix) for suffix in ['docker.io','docker.com','cloudflarestorage.com'])
                if parsed.scheme!='https' or not allowed or len(row['redirects'])>=2:
                    raise ValueError('Redirect boundary')
                row['redirects'].append({'host':host,'status':code})
                redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
                if redirected is not None and host!=urlparse(req.full_url).hostname:
                    redirected.remove_header('Authorization')
                return redirected
        opener=urllib.request.build_opener(BoundedRedirect())
        def get(url,limit,headers=None,save=None):
            r={'url':url};row['requests'].append(r)
            if len(row['requests'])>4:raise ValueError('Request bound')
            with opener.open(urllib.request.Request(url,headers=headers or {}),timeout=30) as response:
                raw=response.read(limit+1);r['status']=response.status
            if len(raw)>limit:raise ValueError('Response byte bound')
            r.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            if save:(directory/save).write_bytes(raw);r['file']=label+'/'+save
            return raw,json.loads(raw)
        try:
            _,auth=get('https://auth.docker.io/token?'+urlencode({'service':'registry.docker.io','scope':'repository:'+repo+':pull'}),64*1024)
            headers={'Authorization':'Bearer '+auth['token'],'Accept':ACCEPT};del auth
            raw,index=get('https://registry-1.docker.io/v2/'+repo+'/manifests/'+tag,2*1024*1024,headers,'index.json')
            row['index_digest']='sha256:'+hashlib.sha256(raw).hexdigest()
            if 'manifests' in index:
                matches=[m for m in index['manifests'] if m.get('platform',{}).get('os')=='linux' and m.get('platform',{}).get('architecture')=='amd64']
                assert len(matches)==1
                digest=matches[0]['digest']
                raw,manifest=get('https://registry-1.docker.io/v2/'+repo+'/manifests/'+digest,1024*1024,headers,'manifest.json')
                assert 'sha256:'+hashlib.sha256(raw).hexdigest()==digest
            else:
                assert 'layers' in index and 'config' in index
                digest=row['index_digest'];manifest=index
                row['tag_is_direct_manifest']=True
            config_digest=manifest['config']['digest']
            raw,config=get('https://registry-1.docker.io/v2/'+repo+'/blobs/'+config_digest,256*1024,headers,'config.json')
            assert 'sha256:'+hashlib.sha256(raw).hexdigest()==config_digest
            assert config['os']=='linux' and config['architecture']=='amd64'
            row.update(status='metadata_verified_no_layers_pulled',manifest_digest=digest,config_digest=config_digest,compressed_layer_bytes=sum(m['size'] for m in manifest['layers']),layer_count=len(manifest['layers']))
            row['role']='original_build_dependency_not_application_revision'
            del headers
        except Exception as error:row.update(error_type=type(error).__name__,error=str(error))
        finally:signal.alarm(0)
        row['elapsed_seconds']=time.monotonic()-start
        (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k!='requests'}),flush=True)
    result['status']='image_metadata_stage_closed'
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
