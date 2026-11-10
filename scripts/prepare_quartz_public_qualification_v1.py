"""Prospectively register the public host controls without altering prior freezes."""
from copy import deepcopy
from datetime import datetime,timezone
from primary_preflight_v1 import ROOT,read,sha,sources
from quartz_public_qualification_preflight_v1 import PREPARATION
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require
NEW_SOURCES=['scripts/run_quartz_public_qualification_unit_v1.py', 'scripts/validate_quartz_public_qualification_unit_v1.py', 'scripts/quartz_public_qualification_matrix_v1.py', 'scripts/quartz_public_qualification_collection_v1.py', 'scripts/verify_quartz_public_qualification_collection_v1.py', 'scripts/freeze_quartz_public_qualification_v1.py', 'scripts/verify_quartz_public_qualification_freeze_v1.py', 'scripts/quartz_public_qualification_preflight_v1.py', '.github/workflows/quartz_public_qualification_v1.yml', 'protocol/quartz-public-host-qualification-v1.md', 'scripts/prepare_quartz_public_qualification_v1.py']

def prepare():
    require(not PREPARATION.exists(),'Public qualification already registered')
    original=ROOT/'manifests/quartz-form-correction-preparation-v1.json'
    prior=read(original);sources(prior)
    value=deepcopy(prior)
    value.update(kind='public_host_quartz_qualification_v1',registered_at_utc=datetime.now(timezone.utc).isoformat(),
        original_correction_preparation_sha256=sha(original),
        plan={'initial_batches':[], 'potential_followup_batches':{}},
        scope='Four exposed public-host controls; no independent research samples or cross-host timing claims')
    value['environment']['logical_cpus']=4
    for unit in value['smoke_units']:
        unit['batch_id']=unit['batch_id'].replace('qfix-','qpublic-')
        for job in unit['jobs']:job['attempt_id']=job['attempt_id'].replace('qfix-','qpublic-')
    value['source_sha256'].update({p:sha(ROOT/p) for p in NEW_SOURCES})
    write(PREPARATION,value)
    return value
if __name__=='__main__':print('Public qualification units:',len(prepare()['smoke_units']))
