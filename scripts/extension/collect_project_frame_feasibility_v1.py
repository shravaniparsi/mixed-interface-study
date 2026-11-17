"""Bounded repository metadata frame; no source or outcome reads."""
import hashlib,json,os,pathlib,subprocess,time,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[2]
QUERY='topic:angular topic:spring-boot fork:false archived:false created:<2026-01-01'
def main():
    private=pathlib.Path('/private/tmp/project-frame-feasibility-v1');private.mkdir(mode=0o700,exist_ok=False)
    started=time.monotonic();records=[]
    exposure=json.loads((ROOT/'manifests/project-reference-exposure-index-v1.json').read_text())
    result=dict(kind='metadata_only_feasibility',query=QUERY,sort='stars',order='desc',page=1,per_page=20,rows=[],requests=records,source_or_outcome_reads=0)
    def save():
        result['elapsed_seconds']=time.monotonic()-started
        (private/'collection.json').write_text(json.dumps(result,indent=2)+'\n');os.chmod(private/'collection.json',0o600)
    def get(endpoint):
        if len(records)>=21 or time.monotonic()-started>=180:raise RuntimeError('request/deadline bound')
        row=dict(endpoint=endpoint);records.append(row)
        try:
            request=urllib.request.Request('https://api.github.com/'+endpoint,headers={'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-research-metadata'})
            with urllib.request.urlopen(request,timeout=30) as response:
                raw=response.read(2*1024*1024+1);row['http_status']=response.status
                row['rate_limit_remaining']=response.headers.get('X-RateLimit-Remaining');row['response_date']=response.headers.get('Date')
            if len(raw)>2*1024*1024:raise RuntimeError('response size bound')
            path=private/(str(len(records))+'.json');path.write_bytes(raw);path.chmod(0o600)
            row.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),status='received')
            return json.loads(raw)
        except Exception as error:
            row.update(status='error',error_type=type(error).__name__,message=str(error));return None
        finally:save()
    query=urllib.parse.urlencode(dict(q=QUERY,sort='stars',order='desc',page=1,per_page=20))
    data=get('search/repositories?'+query)
    if data is None:result['status']='search_failed';save();return
    result.update(total_count=data['total_count'],incomplete_results=data['incomplete_results'])
    if len(data['items'])>20:raise RuntimeError('unexpected result count')
    for rank,item in enumerate(data['items'],1):
        row={k:item.get(k) for k in ['id','full_name','html_url','default_branch','language','topics','stargazers_count','created_at','updated_at','fork','archived','size']}
        row.update(rank=rank,license_spdx=(item.get('license') or {}).get('spdx_id'),prior_references=exposure['repositories'].get(item['full_name'].lower(),[]),exposure_interpretation='reference_matches_only_not_independence_proof')
        result['rows'].append(row)
        endpoint='repos/'+item['full_name']+'/git/ref/heads/'+urllib.parse.quote(item['default_branch'],safe='')
        pin=get(endpoint)
        row['pin']={'status':'unresolved'} if pin is None else dict(status='received',sha=pin.get('object',{}).get('sha'),object_type=pin.get('object',{}).get('type'))
        save()
    result['status']='collected';save()
    print(json.dumps(dict(status=result['status'],returned=len(result['rows']),total_count=result['total_count'],requests=len(records))))
if __name__=='__main__':main()
