#!/usr/bin/env python3
import base64,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 out=ROOT/'results/redesign-evaluation-source-wave1-v1';x=json.loads((out/'collection.json').read_text());assert x['status']=='source_wave_closed' and x['application_executed'] is False
 for p,h in x['input_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 schedule=json.loads((ROOT/'manifests/redesign-evaluation-source-wave1-v1.json').read_text())['rows'];assert len(schedule)==len(x['rows'])==4;total=0
 for expected,row in zip(schedule,x['rows']):
  assert all(row[k]==v for k,v in expected.items());assert row['status']=='collected_verified';raw=(out/row['file']).read_bytes();envelope=(out/row['envelope']).read_bytes();assert hashlib.sha256(envelope).hexdigest()==row['envelope_sha256'];assert base64.b64decode(json.loads(envelope)['content'])==raw;assert hashlib.sha256(raw).hexdigest()==row['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha'];assert len(raw)==row['declared_bytes']==row['bytes'];total+=len(raw)
 assert sum(x['decoded_bytes'].values())==total;summary={'status':'verified','files':4,'decoded_bytes':total,'application_executed':False,'scientific_cases':0};(out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
