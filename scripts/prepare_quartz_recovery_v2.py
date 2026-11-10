"""Register identical recovery cases on the independently qualified public host."""
from copy import deepcopy
from datetime import datetime,timezone
from primary_preflight_v1 import ROOT,read,sha,sources
from quartz_recovery_preflight_v2 import PREPARATION
from prepare_quartz_recovery_v1 import derive
from verify_quartz_public_qualification_freeze_v1 import check
from retain_quartz_provider_failure_v1 import build,OUTPUT as RETENTION
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require
NEW_SOURCES=['scripts/quartz_recovery_preflight_v2.py', 'scripts/run_quartz_recovery_unit_v2.py', 'scripts/validate_quartz_recovery_unit_v2.py', 'scripts/quartz_recovery_matrix_v2.py', 'scripts/quartz_recovery_collection_v2.py', 'scripts/verify_quartz_recovery_collection_v2.py', 'scripts/prepare_quartz_recovery_followups_v2.py', 'scripts/freeze_quartz_recovery_v2.py', 'scripts/verify_quartz_recovery_release_v2.py', 'scripts/analyze_quartz_recovery_v2.py', 'scripts/verify_quartz_recovery_results_v2.py', '.github/workflows/quartz_recovery_v2.yml', 'protocol/quartz-provider-recovery-v2.md', 'scripts/prepare_quartz_recovery_v2.py']

def prepare():
    require(not PREPARATION.exists(),'Public recovery already registered')
    check()
    old_path=ROOT/'manifests/quartz-recovery-preparation-v1.json'
    old=read(old_path);sources(old)
    retained=build();require(retained==read(RETENTION),'Provider evidence differs')
    original=read(ROOT/'manifests/quartz-form-correction-preparation-v1.json')
    plan,links=derive(original,retained)
    require(plan==old['plan'] and links==old['original_case_links'],'Selected cases changed')
    public_path=ROOT/'manifests/quartz-public-qualification-preparation-v1.json'
    public=read(public_path);sources(public)
    value=deepcopy(old)
    value.update(kind='public_host_exposed_quartz_provider_recovery_v2',registered_at_utc=datetime.now(timezone.utc).isoformat(),
        superseded_unexecuted_preparation_sha256=sha(old_path),
        public_qualification_preparation_sha256=sha(public_path),
        qualification_sha256=sha(ROOT/'manifests/quartz-public-qualification-freeze-v1.json'),
        environment=public['environment'],
        scope='Separate exposed public four-core recovery cohort; disjoint case coverage, no independent-sample pooling or cross-host timing comparison')
    value['source_sha256'].update(public['source_sha256'])
    value['source_sha256'].update({p:sha(ROOT/p) for p in NEW_SOURCES})
    write(PREPARATION,value)
    return value
if __name__=='__main__':print('Public recovery units:',len(prepare()['plan']['initial_batches']))
