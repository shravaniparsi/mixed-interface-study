"""Source/environment acceptance and immutable selection; primary requires a dated freeze."""
from pathlib import Path
import sys,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.common_execution_v1 import read,sha
from mixed_interface.repetition import require,digest
from mixed_interface.primary_batches_v1 import plan,followups
PREPARATION=ROOT/'manifests/primary-execution-preparation-v1.json'
FREEZE=ROOT/'manifests/primary-execution-freeze-v1.json'

def prepare():
    from primary_catalog_v1 import templates
    catalog=templates();require(catalog==read(ROOT/'manifests/primary-runtime-catalog-v1.json'),'Catalog changed')
    p=plan(catalog);smoke=[]
    for profile in ('rw_identity','petclinic_v4','generated_mutation_v3','quartz_v2'):
        b=next(b for b in catalog['bindings'] if b['runtime']['profile']==profile)
        from mixed_interface.primary_batches_v1 import batch
        unit=batch(b,1);runtime=b['reference_runtime'];require(runtime is not None,'Smoke needs paired reference')
        unit['batch_id']='smoke-'+profile;unit['target_pair_id']=b['reference_pair_id']
        unit['jobs']=[{'attempt_id':unit['batch_id']+f'-r{r}','target_pair_id':b['reference_pair_id'],'entry_pair_id':b['reference_pair_id'],
            'role':'engineering_reference','repetition':r,'entry_kind':'pair','runtime':runtime,'binding_sha256':b['binding_sha256']} for r in (1,2)]
        smoke.append(unit)
    import importlib
    names=set()
    for module in ('run_realworld_expanded_campaign','run_realworld_field_campaign','run_realworld_rejection_campaign',
                   'run_realworld_paired_database_v7','run_realworld_legacy_campaign_v10','run_common_generated_v1','run_quartz_terminal_campaign'):
        names.update(importlib.import_module(module).SOURCES)
    names.update(['scripts/primary_catalog_v1.py','scripts/primary_runtime_v1.py','scripts/primary_attempt_v1.py',
        'scripts/primary_preflight_v1.py','scripts/run_primary_unit_v1.py','scripts/validate_primary_unit_v1.py','scripts/primary_matrix_v1.py','scripts/primary_collection_v1.py',
        'src/mixed_interface/primary_batches_v1.py','scripts/ci/prepare_quartz.py','scripts/ci/capture_versions.py',
        'scripts/ci/install_browser.sh','scripts/ci/package.json',
        'manifests/primary-runtime-catalog-v1.json','manifests/realworld-identity-controls-v1.json',
        'manifests/quartz-declared-dependencies.json','protocol/primary-independent-units-v1.md',
        'protocol/primary-runtime-catalog-v1.md','protocol/primary-cost-scope-v2.md','.github/workflows/primary_diagnostics_v1.yml'])
    paths={ROOT/name for name in names}
    return {'kind':'primary_execution_preparation_v1','plan':p,'smoke_units':smoke,
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)},
        'environment':{'ImageOS':'ubuntu24','ImageVersion':'20261101.360.1','RUNNER_OS':'Linux','RUNNER_ARCH':'X64','architecture':'x86_64',
                       'python_prefix':'3.12.16 ','node':{'petclinic':'v24.22.2','realworld':'v20.20.2','quartz':'v20.20.2'},
                       'java':{'petclinic':'17.0.2+8','quartz':'21.0.13+9'},'browser_version':'151.0.7922.34','browser_sha256':'0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71','logical_cpus':2},
        'primary_freeze_complete':False,'execution_authorized':False}

def sources(value):
    for p,h in value['source_sha256'].items():require(sha(ROOT/p)==h,'Frozen source changed: '+p)

def environment(value,app,versions,browser,bootstrap):
    expected=value['environment'];require(all(versions['runner'][k]==expected[k] for k in ('ImageOS','ImageVersion','RUNNER_OS','RUNNER_ARCH')),'Hosted image differs')
    require(versions['architecture']==expected['architecture'] and versions['logical_cpus']==expected['logical_cpus'],'Machine class differs')
    require(versions['python'].startswith(expected['python_prefix']) and versions['node']['exit_code']==0 and versions['node']['output']==expected['node'][app],'Runtime version differs')
    if app in expected['java']:require(expected['java'][app] in versions['java']['output'],'Java differs')
    require(browser['declared']['browserVersion']==expected['browser_version'] and browser['executable_sha256']==expected['browser_sha256'],'Browser differs')
    if app=='petclinic':
        registry=read(ROOT/'manifests/petclinic-candidates-v1.json')
        require(bootstrap['source_modified'] is False and bootstrap['commits']=={'backend':registry['backend_commit'],'frontend':registry['frontend_commit']} and bootstrap['native_backend_verify']==bootstrap['native_frontend_test_ci']=='passed','PetClinic bootstrap differs')
    elif app=='realworld':
        require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False and bootstrap['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and bootstrap['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','RealWorld bootstrap differs')
    else:
        lock=read(ROOT/'manifests/quartz-artifact-lock.json');expected_jars=[{k:a[k] for k in ('name','sha256','size_bytes')} for a in lock['artifacts']+lock['additional_declared_dependencies'] if a['name'].endswith('.jar')]
        require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False and bootstrap['artifact_lock_sha256']==sha(ROOT/'manifests/quartz-artifact-lock.json') and bootstrap['verified_jars']==expected_jars,'Quartz bootstrap differs')

def units(mode):
    value=read(PREPARATION);sources(value)
    if mode=='smoke':return value['smoke_units']
    freeze=read(FREEZE);require(freeze['primary_freeze_complete'] is True and freeze['preparation_sha256']==sha(PREPARATION),'Primary freeze absent or differs')
    if mode=='initial':return value['plan']['initial_batches']
    require(mode in ('repeat2','repeat3'),'Unknown phase')
    selection=read(ROOT/f'manifests/primary-execution-{mode}-v1.json')
    require(selection['preparation_sha256']==sha(PREPARATION) and selection['freeze_sha256']==sha(FREEZE),'Follow-up context differs')
    expected=followups(value['plan'],selection['initial'],int(mode[-1]),selection.get('previous'))
    require(selection['schedule']==expected,'Follow-up selection differs')
    return expected['batches']
