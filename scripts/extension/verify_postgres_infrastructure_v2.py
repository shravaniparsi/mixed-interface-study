import argparse,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/postgres-infrastructure-v2'
def main():
 p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('--sha256',required=True);p.add_argument('--run',type=pathlib.Path,required=True);a=p.parse_args();raw=a.archive.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.sha256;run=json.loads(a.run.read_text())
 with zipfile.ZipFile(a.archive) as z:
  assert len(z.namelist())==len(set(z.namelist())) and sum(r.file_size for r in z.infolist())<4*1024**2
  assert all(pathlib.PurePosixPath(n).name==n for n in z.namelist())
  assert z.read('freeze.txt').decode().strip()==run['head_sha']
  get=lambda n:json.loads(z.read(n+'.json'))
  publication=get('publication');assert set(z.namelist())=={r['name'] for r in publication['files']}|{'publication.json'}
  for row in publication['files']:assert hashlib.sha256(z.read(row['name'])).hexdigest()==row['sha256'] and len(z.read(row['name']))==row['bytes']
  result=get('result') if 'result.json' in z.namelist() else {'status':'result_unavailable'};checks={}
  if result['status']=='infrastructure_checks_passed':
   assert run['status']=='completed' and run['conclusion']=='success';assert result['scientific_cases']==0 and result['application_executed'] is False
   names=sorted(n for n in z.namelist() if n[:2].isdigit() and n.endswith('.json'));rows=[json.loads(z.read(n)) for n in names]
   expected=['postgres','service_permissions','initialize','expected_nonempty_failure','start','createdb','psql','psql','pg_dump','psql','psql','dropdb','createdb','pg_restore','psql','stop','stopped_status']
   assert [r['stage'] for r in rows]==expected and result['command_count']==17
   for r in rows:
    assert r['captured_bytes']<=65536 and not r['arguments_retained'] and not r['environment_retained']
    if r['stage']=='expected_nonempty_failure':assert r['status']=='failed' and r['exit_code']!=0 and 'not empty' in r['output'].lower()
    elif r['stage']=='stopped_status':assert r['status']=='failed' and r['exit_code']==3 and 'no server running' in r['output'].lower()
    else:assert r['status']=='succeeded' and r['exit_code']==0
   before=get('before');changed=get('changed');restored=get('restored');assert before==restored and changed!=before
   assert before=={'rows':[{'id':1,'value':'ordinary','payload':{'present':None}},{'id':2,'value':'other','payload':{}}],'sequence':{'last_value':'2','is_called':True}}
   assert changed['sequence']['last_value']=='3' and len(changed['rows'])==3
   assert json.loads(rows[7]['output'])==before and json.loads(rows[10]['output'])==changed and json.loads(rows[14]['output'])==restored
   assert get('network-routes')==[] and all(x['ifname']=='lo' for x in get('network-interfaces'))
   checks={'service_permissions':True,'expected_failure_diagnostic':True,'rows_null_missing_and_sequence_restored':True,'shutdown':True,'loopback_only':True}
  OUT.mkdir(exist_ok=True)
  for n in z.namelist():(OUT/n).write_bytes(z.read(n))
  v=dict(status='verified_infrastructure_success' if checks else 'failure_evidence_retained',run_id=run['id'],artifact_sha256=a.sha256,checks=checks,observed_status=result['status'],application_executed=False,scientific_cases=0)
  (OUT/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()
