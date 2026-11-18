#!/usr/bin/env python3
"""Explain the closed ordinary restore mismatch without reclassifying it."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/redesign-gomodel-ordinary-v1'
def read(name):return json.loads((OUT/(name+'.json')).read_text())
def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))
def differences(a,b,p=''):
    if type(a)!=type(b):return [{'path':p,'before':a,'after':b}]
    if isinstance(a,dict):
        rows=[]
        for k in sorted(a.keys()|b.keys()):
            if k in a and k in b:rows+=differences(a[k],b[k],p+'/'+k)
            else:rows.append({'path':p+'/'+k,'before':a.get(k),'after':b.get(k),'missing_side':'before' if k not in a else 'after'})
        return rows
    if isinstance(a,list) and len(a)==len(b):return sum((differences(x,y,p+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
    return [] if same(a,b) else [{'path':p,'before':a,'after':b}]
a,b=read('checkpoint-state'),read('restored-precheck-state')
diff=differences(a,b)
assert {x['path'] for x in diff}=={'/files/data/gomodel.pid/sha256','/tables/sqlite_stat1/rows'}
pids=[]
for state,start in [('checkpoint-state','startup-1'),('restored-precheck-state','startup-2')]:
    pid=read(start)['pid'];row=read(state)['files']['data/gomodel.pid'];matches=hashlib.sha256((str(pid)+'\n').encode()).hexdigest()==row['sha256'];assert matches
    pids.append({'snapshot':state,'live_process_id':pid,'stored_file_bytes':row['bytes'],'matches_pid_with_newline':matches})
checks={k:same(a['tables'][k],b['tables'][k]) for k in a['tables'] if k!='sqlite_stat1'}
assert all(checks.values()) and same(a['schema'],b['schema'])
summary={'pid_checks':pids,'all_other_tables_equal':True,'other_table_count':len(checks),'schema_equal':True,'table_checks':checks,'original_qualification_status':'failed_restore_gate','restored_write_executed':False,'scientific_cases':0}
(OUT/'restored-start-differences.json').write_text(json.dumps(diff,indent=2)+'\n')
(OUT/'restoration-diagnostic.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'difference_paths':[x['path'] for x in diff],'other_tables_equal':len(checks),'status':'original_failure_preserved'}))
