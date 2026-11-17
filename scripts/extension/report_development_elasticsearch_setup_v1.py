import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=Path('/private/tmp/development-elasticsearch-setup-v1')
schedule=json.loads((ROOT/'manifests/development-elasticsearch-setup-schedule-v1.json').read_text())
c=json.loads((D/'collection.json').read_text());assert len(c['rows'])==2
for i,(s,r) in enumerate(zip(schedule['files'],c['rows']),1):
    assert all(r[k]==s[k] for k in s) and r['status']=='verified'
    raw=(D/(str(i)+'.txt')).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==s['blob_sha']
    r['selected_lines']=[dict(line=n,text=l) for n,l in enumerate(raw.decode().splitlines(),1)
      if any(x in l for x in ['docker.elastic.co/elasticsearch','xpack.security.enabled','discovery.type','bootstrap.memory_lock','ES_JAVA_OPTS','SPRING_ELASTICSEARCH_URIS','IPC_LOCK'])]
result=dict(kind='development_elasticsearch_setup',freeze='1771e5a',collection=c,independent_evaluation_cases=0,image_pulled=False)
p=ROOT/'manifests/development-elasticsearch-setup-v1.json';text=json.dumps(result,indent=2)+'\n'
import sys
if '--verify' in sys.argv:assert p.read_text()==text;print('Pinned deployment metadata verified')
else:p.write_text(text)
