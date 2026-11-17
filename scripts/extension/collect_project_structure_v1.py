"""Pinned directory trees only; no file content or outcomes."""
import hashlib,json,os,re,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    frame=json.loads((ROOT/'manifests/independent-project-frame-feasibility-v1.json').read_text())
    private=Path('/private/tmp/project-structure-screen-v1');private.mkdir(mode=0o700,exist_ok=False)
    result=dict(kind='pinned_filename_only_structure_screen',frame='independent-project-frame-feasibility-v1.json',rows=[],file_contents_read=0);started=time.monotonic()
    def save():
        result['elapsed_seconds']=time.monotonic()-started
        p=private/'collection.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
    excluded={'node_modules','vendor','.git','target','dist','build'}
    test=re.compile(r'(^|/)(test|tests|__tests__|e2e|cypress)(/|$)|\.spec\.|\.test\.|Test\.java$')
    for item in frame['rows']:
        row=dict(rank=item['rank'],full_name=item['full_name'],commit=item['pin'].get('sha'),status='tree_unavailable');result['rows'].append(row)
        if item['pin']['status']!='received':row['reason']='pin_unresolved';save();continue
        if time.monotonic()-started>=180:row['reason']='deadline';save();continue
        endpoint='repos/'+item['full_name']+'/git/trees/'+row['commit']+'?recursive=1';row['endpoint']=endpoint
        try:
            request=urllib.request.Request('https://api.github.com/'+endpoint,headers={'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-research-structure'})
            with urllib.request.urlopen(request,timeout=min(30,max(0.1,180-(time.monotonic()-started)))) as response:
                raw=response.read(4*1024*1024+1);row['http_status']=response.status;row['rate_limit_remaining']=response.headers.get('X-RateLimit-Remaining');row['response_date']=response.headers.get('Date')
            if len(raw)>4*1024*1024:raise RuntimeError('4MiB response limit')
            p=private/(str(item['rank'])+'.json');p.write_bytes(raw);p.chmod(0o600)
            row.update(response_sha256=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw))
            tree=json.loads(raw);row['tree_sha']=tree['sha'];row['truncated']=tree['truncated'];row['status']='tree_truncated' if tree['truncated'] else 'structure_recorded'
            blobs=[e['path'] for e in tree['tree'] if e['type']=='blob'];paths=sorted(p for p in blobs if not excluded.intersection(p.split('/')))
            groups=dict(package_manifests=[p for p in paths if p.split('/')[-1]=='package.json'],jvm_builds=[p for p in paths if p.split('/')[-1] in {'pom.xml','build.gradle','build.gradle.kts'}],api_spec_candidates=[p for p in paths if re.fullmatch(r'(openapi|swagger).*\.(json|yaml|yml)',p.split('/')[-1],re.I)],generator_markers=[p for p in paths if p.split('/')[-1]=='.yo-rc.json'])
            row.update(total_blob_paths=len(blobs),retained_path_count=len(paths),test_like_path_count=sum(bool(test.search(p)) for p in paths))
            row['path_groups']={k:dict(count=len(v),paths=v[:200],list_truncated=len(v)>200) for k,v in groups.items()}
            row['manifest_build_signals_cooccur']=bool(groups['package_manifests'] and groups['jvm_builds'])
            row['eligibility']='unresolved_filename_signals_only'
        except Exception as error:row.update(error_type=type(error).__name__,message=str(error))
        save()
    result['status']='closed';save()
    from collections import Counter
    print(json.dumps(dict(rows=len(result['rows']),statuses=dict(Counter(r['status'] for r in result['rows'])))))
if __name__=='__main__':main()
