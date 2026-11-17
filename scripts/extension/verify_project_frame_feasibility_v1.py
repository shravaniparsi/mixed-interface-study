"""Audit metadata collection bounds, pins and reference overlap; no source reads."""
import argparse,hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main(private):
    x=json.loads((ROOT/'manifests/independent-project-frame-feasibility-v1.json').read_text())
    e=json.loads((ROOT/'manifests/project-reference-exposure-index-v1.json').read_text())
    assert x['freeze']=='682fe2e' and x['query']=='topic:angular topic:spring-boot fork:false archived:false created:<2026-01-01'
    assert (x['sort'],x['order'],x['page'],x['per_page'])==('stars','desc',1,20)
    assert len(x['requests'])<=21 and len(x['rows'])<=20 and x['source_or_outcome_reads']==0
    assert len({r['id'] for r in x['rows']})==len(x['rows'])
    assert len({r['full_name'] for r in x['rows']})==len(x['rows'])
    for rank,row in enumerate(x['rows'],1):
        assert row['rank']==rank and not row['fork'] and not row['archived']
        assert row['created_at']<'2026-01-01'
        assert {'angular','spring-boot'}<=set(row['topics'])
        assert row['prior_references']==e['repositories'].get(row['full_name'].lower(),[])
        if row['pin']['status']=='received':assert row['pin']['object_type']=='commit' and re.fullmatch('[0-9a-f]{40}',row['pin']['sha'])
    assert all(a['stargazers_count']>=b['stargazers_count'] for a,b in zip(x['rows'],x['rows'][1:]))
    if private:
        for index,request in enumerate(x['requests'],1):
            if request['status']!='received':continue
            raw=(private/(str(index)+'.json')).read_bytes()
            assert len(raw)==request['bytes']<=2*1024*1024
            assert hashlib.sha256(raw).hexdigest()==request['sha256']
        original=json.loads((private/'1.json').read_text())
        assert original['total_count']==x['total_count'] and original['incomplete_results']==x['incomplete_results']
        assert [r['id'] for r in original['items']]==[r['id'] for r in x['rows']]
        for index,row in enumerate(x['rows'],2):
            if row['pin']['status']=='received':assert json.loads((private/(str(index)+'.json')).read_text())['object']['sha']==row['pin']['sha']
    summary=dict(returned=len(x['rows']),search_total=x['total_count'],incomplete_results=x['incomplete_results'],pins_received=sum(r['pin']['status']=='received' for r in x['rows']),prior_reference_matches=sum(bool(r['prior_references']) for r in x['rows']),distinct_owner_names=len({r['full_name'].split('/')[0] for r in x['rows']}),languages=dict(Counter(str(r['language']) for r in x['rows'])),independent_projects_established=0,applications_admitted=0)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-directory',type=Path);a=p.parse_args();main(a.private_directory)
