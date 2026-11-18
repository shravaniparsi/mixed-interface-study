"""Execute one frozen ordinary scenario against an already provisioned runtime.

Parent owns published registration, build/provisioning, shared job deadline and
cleanup. This module starts no new application/container and dispatches no job.
All evidence here is private. A completed sequence is not full qualification:
root-layer classification, topology and parent runtime gates remain mandatory.
"""
import json
import os
from datetime import datetime
import time
from pathlib import Path
from urllib.parse import urlsplit
import subprocess

from nginx_coordinated_checkpoint_v1 import ROOT
from nginx_startup_fixture_v1 import verify_startup_fixture, MARKERS
from nginx_ordinary_database_comparison_v1 import compare_ordinary_databases, records, integer
from nginx_ordinary_filesystem_delta_v1 import verify_ordinary_filesystem_delta
from nginx_restart_state_comparison_v1 import compare_restart_state
from nginx_root_layer_comparison_v1 import parse_diff, compare_root_layers


def canonical_request(envelope):
    request = envelope['request']
    path = request.get('path') or urlsplit(request['url']).path
    headers = {k.lower():v for k,v in request['headers'].items()}
    return {'method':request['method'], 'path':path, 'body':json.loads(request['body']),
            'authorization':headers['authorization'], 'content-type':headers['content-type']}


def verify_ordinary_fixture(database, ids, actor_id, producer):
    """Verify native/API ordinary producers against actual persisted values."""
    tables={t['name']:records(t)[1] for t in database['tables']}
    expected={
        'access_list':dict(name=['text',producer['name']],satisfy_any=['integer','0'],pass_auth=['integer','0'],owner_user_id=['integer',str(actor_id)],is_deleted=['integer','0']),
        'access_list_auth':dict(username=['text',producer['items'][0]['username']],password=['text',producer['items'][0]['password']]),
        'access_list_client':dict(directive=['text','allow'],address=['text',producer['clients'][0]['address']]),
    }
    for name,values in expected.items():
        rows=tables[name]
        if len(rows)!=3: raise ValueError('Unexpected ordinary fixture row count: '+name)
        key='id' if name=='access_list' else 'access_list_id'
        for subject in ids:
            matched=[r for r in rows if r[key]==['integer',str(subject)]]
            if len(matched)!=1 or any(matched[0].get(k)!=v for k,v in values.items()):
                raise ValueError('Ordinary persisted producer differs: '+name)


class OrdinaryScenario:
    def __init__(self, checkpoint, bridge, evidence, deadline):
        self.checkpoint, self.bridge = checkpoint, bridge
        self.evidence = Path(evidence).resolve()
        self.evidence.mkdir(mode=0o700, exist_ok=False)
        self.deadline = deadline
        self.serial = 0
        self.startup = None
        self.process_identity = None

    def remaining(self, bound):
        left = self.deadline-time.monotonic()
        if left <= 0: raise TimeoutError('Original scenario/job deadline expired')
        return min(bound,left)

    def save(self,name,value):
        path=self.evidence/name
        with path.open('x') as stream: json.dump(value,stream,indent=2); stream.write('\n')
        return path

    def browser(self,operation,**values):
        self.serial+=1
        command=dict(requestId=f'step-{self.serial:02d}-{operation.replace("_","-")}',operation=operation,**values)
        try: return self.bridge.send(command,command_seconds=self.remaining(90),observe_seconds=self.remaining(25))
        except TimeoutError:
            # Observe the SAME pending command. Never resend, restart or reset its deadline.
            while self.bridge.pending is not None and not self.bridge.failed:
                try: return self.bridge.observe_pending(self.remaining(25))
                except TimeoutError: continue
            raise

    def docker(self,args,input=None,bound=30):
        result=subprocess.run(['docker',*args],input=input,capture_output=True,timeout=self.remaining(bound),check=True)
        if len(result.stdout)>128*1024*1024 or len(result.stderr)>2*1024*1024:
            raise ValueError('Runtime command output bound')
        return result.stdout

    def logs(self,metadata):
        # stderr contains original application output too. Retain it privately.
        result=subprocess.run(['docker','logs','--since',metadata['State']['StartedAt'],metadata['Id']],
            capture_output=True,timeout=self.remaining(15),check=True)
        raw=result.stdout+result.stderr
        if len(raw)>2*1024*1024: raise ValueError('Startup log bound')
        return raw

    def settle_startup(self,label):
        limit=time.monotonic()+self.remaining(120)
        initial=self.checkpoint.metadata()
        if not initial['State']['Running'] or initial['State']['Paused']:
            raise ValueError('Original application is not running')
        while True:
            metadata=self.checkpoint.metadata()
            if any(metadata['State'][k]!=initial['State'][k] for k in ('Pid','StartedAt')) or not metadata['State']['Running']:
                raise ValueError('Application exited/restarted during startup observation')
            raw=self.logs(metadata)
            if all(first.encode() in raw and last.encode() in raw for first,last in MARKERS): break
            if time.monotonic()>=limit: raise TimeoutError('Original startup deadline expired')
            time.sleep(min(1,max(0,limit-time.monotonic())))
        (self.evidence/f'{label}-startup.log').write_bytes(raw)
        state=self.checkpoint.database('inspect',self.checkpoint.roots['/data'],self.evidence/f'{label}-startup-database.json')['state']
        proof=verify_startup_fixture(state,raw)
        started=datetime.fromisoformat(metadata['State']['StartedAt'].replace('Z','+00:00')).timestamp()
        if time.time()-started>120: raise TimeoutError('Startup exceeded registered interval')
        self.startup={'metadata':metadata,'proof':proof,'window':dict(timezone='UTC',start_epoch_seconds=started,end_epoch_seconds=time.time())}
        self.process_identity = None  # Only an explicitly observed startup resets continuity.
        self.save(f'{label}-startup.json',self.startup)
        return self.startup

    def quiescence(self):
        proof=self.browser('quiescence')
        metadata=self.checkpoint.metadata()
        if self.startup is None or any(metadata['State'][k]!=self.startup['metadata']['State'][k] for k in ('Pid','StartedAt')) or not metadata['State']['Running']:
            raise ValueError('Application continuity failed')
        raw=self.logs(metadata)
        # No scheduled operation is outstanding: browser operations synchronously
        # await their original responses; immediate timers must remain completed.
        self.serial+=1
        state=self.checkpoint.database('inspect',self.checkpoint.roots['/data'],self.evidence/f'quiescence-{self.serial}.json')['state']
        timer=verify_startup_fixture(state,raw)
        proof.update(timer,application_operations_settled=True)
        self.save(f'quiescence-proof-{self.serial}.json',proof)
        return proof

    def snapshot(self,label,list_id):
        self.quiescence()
        before=self.checkpoint.metadata()
        runtime=json.loads(self.docker(['exec',before['Id'],'node',str(ROOT/'scripts/extension/nginx_runtime_observation_v1.mjs'),str(os.getuid()),str(os.getgid())]))
        processes={key:runtime[key] for key in ('backend','master')}
        if self.process_identity is not None and processes!=self.process_identity:
            raise ValueError('Original backend/nginx process changed inside branch')
        self.process_identity=processes
        database=self.checkpoint.database('inspect',self.checkpoint.roots['/data'],self.evidence/f'{label}-database.json')['state']
        raw=self.docker(['exec',before['Id'],'cat',f'/data/access/{list_id}'])
        after=self.checkpoint.metadata()
        if any(before['State'][k]!=after['State'][k] for k in ('Pid','StartedAt')):
            raise ValueError('Application changed during snapshot')
        self.save(f'{label}-runtime.json',runtime)
        self.save(f'{label}-container.json',after)
        diff=self.docker(['diff',before['Id']])
        paths=sorted(parse_diff(diff))
        layer=json.loads(self.docker(['exec','-i',before['Id'],'python3',str(ROOT/'scripts/extension/nginx_root_layer_inventory_v1.py')],input=json.dumps(paths).encode(),bound=60))
        if self.docker(['diff',before['Id']])!=diff:
            raise ValueError('Docker root-layer diff changed during inventory')
        (self.evidence/f'{label}-container-diff.txt').write_bytes(diff)
        self.save(f'{label}-root-layer.json',layer)
        (self.evidence/f'{label}-access.bin').write_bytes(raw)
        return dict(runtime=runtime,database=database,access=raw,root_layer=layer,diff=diff)

    def derive_hash(self,password,salt):
        return self.docker(['exec','-i',self.checkpoint.container,'openssl','passwd','-apr1','-salt',salt,'-stdin'],
            input=(password+'\n').encode(),bound=10).decode().strip()

    def schema(self,label,request):
        source=self.save(f'{label}-schema-input.json',dict(method=request['method'],body=request['body']))
        # Parent mounts this private directory read/write at its identical path.
        result=json.loads(self.docker(['exec',self.checkpoint.container,'node',str(ROOT/'scripts/extension/nginx_schema_command_v1.mjs'),str(source)],bound=30))
        self.save(f'{label}-schema-result.json',result)
        if result['status']!='accepted': raise ValueError('Ordinary original schema rejected request')
        return result

    def run(self,identity,secret,producer,edit):
        self.settle_startup('initial')
        self.browser('login',identity=identity,secret=secret)
        seed=self.browser('api_create',producer=producer)
        native=self.browser('native_create',producer=producer)
        subject=self.browser('api_create',producer=producer)
        ids=[seed['json']['id'],native['response']['id'],subject['json']['id']]
        if len(set(ids))!=3: raise ValueError('Distinct ordinary fixture IDs required')
        self.schema('producer',subject['request'])
        list_id=ids[-1]
        readbacks=[self.browser('read',id=i) for i in ids]
        for item,i in zip(readbacks,ids):
            if item['status']!=200 or item['json']['id']!=i: raise ValueError('Ordinary fixture readback failed')
        warm=self.snapshot('warm-before',list_id)
        users=next(t for t in warm['database']['tables'] if t['name']=='user')
        matches=[r for r in records(users)[1] if r['email']==['text',identity]]
        if len(matches)!=1: raise ValueError('Synthetic actor is not uniquely identified')
        actor_id=integer(matches[0]['id'])
        verify_ordinary_fixture(warm['database'],ids,actor_id,producer)
        self.browser('save_storage')
        checkpoint_path=self.evidence/'checkpoint'
        self.checkpoint.capture(checkpoint_path,self.quiescence)
        resumed=self.snapshot('warm-after-checkpoint',list_id)
        if resumed['database']!=warm['database'] or resumed['runtime']['inventories']!=warm['runtime']['inventories']:
            raise ValueError('Warm state changed across checkpoint')
        self.save('warm-checkpoint-root-layer.json',compare_root_layers(warm['root_layer'],resumed['root_layer'],warm['diff'],resumed['diff'],'operation',dict(timezone='UTC',start_epoch_seconds=time.time(),end_epoch_seconds=time.time())))
        warm=resumed
        outcomes=[]
        for branch in ('warm-native','restored-native','restored-api'):
            before=warm
            if branch!='warm-native':
                self.checkpoint.stop_and_restore(checkpoint_path,self.evidence/f'{branch}-restore')
                self.docker(['start',self.checkpoint.container])
                startup=self.settle_startup(branch)
                self.browser('restore_storage')
                before=self.snapshot(f'{branch}-before',list_id)
                self.save(f'{branch}-restart-comparison.json',compare_restart_state(warm['runtime'],before['runtime'],warm['database'],before['database'],startup['window']))
                self.save(f'{branch}-restart-root-layer.json',compare_root_layers(warm['root_layer'],before['root_layer'],warm['diff'],before['diff'],'restart',startup['window']))
                readback=self.browser('read',id=list_id)
                if readback['json']!=readbacks[-1]['json']: raise ValueError('Restored original readback differs')
            start=time.time()
            result=self.browser('api_update' if branch=='restored-api' else 'native_update',id=list_id,edit=edit)
            end=time.time()
            envelope=result['result'] if branch=='restored-api' else result
            request=canonical_request(envelope)
            self.schema(branch,envelope['request'])
            after=self.snapshot(f'{branch}-after',list_id)
            window=dict(timezone='UTC',start_epoch_seconds=start,end_epoch_seconds=end)
            self.save(f'{branch}-operation-comparison.json',verify_ordinary_filesystem_delta(before['runtime'],after['runtime'],before['database'],after['database'],list_id,actor_id,edit,window,before['access'],after['access'],self.derive_hash))
            self.save(f'{branch}-operation-root-layer.json',compare_root_layers(before['root_layer'],after['root_layer'],before['diff'],after['diff'],'operation',window))
            outcomes.append(dict(request=request,after=after,window=window))
            if len(outcomes)>1:
                if request!=outcomes[0]['request']: raise ValueError('Complete native/API requests or authorization differ')
                self.save(f'{branch}-database-comparison.json',compare_ordinary_databases(warm['database'],outcomes[0]['after']['database'],after['database'],list_id,actor_id,edit,outcomes[0]['window'],window))
        result={'status':'ordinary_sequence_executed_parent_runtime_gates_unqualified','subject_id':list_id,'actor_id':actor_id,'branches':3,'scientific_inputs':0}
        self.save('sequence-result.json',result)
        return result
