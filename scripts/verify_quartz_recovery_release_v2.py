"""Validate a release only against successful hosted checks and retained qualification."""
from quartz_recovery_preflight_v2 import ROOT,PREPARATION,FREEZE,read,sha,sources
from verify_quartz_public_qualification_freeze_v1 import check as qualification
from retain_quartz_provider_failure_v1 import build,OUTPUT as RETENTION
from prepare_quartz_recovery_v1 import derive
from mixed_interface.repetition import require

def ci_accepted(value,source_commit):
    require(value['status']=='completed' and value['conclusion']=='success','Hosted CI has not passed')
    require(value['name']=='Unit checks' and value['head_sha']==source_commit,'Hosted CI source differs')
    require(value['repository']['full_name']=='shravaniparsi/mixed-interface-study','Foreign CI repository')

def preparation_verified():
    prep=read(PREPARATION);sources(prep);qualification()
    retained=build();require(retained==read(RETENTION) and prep['provider_retention_sha256']==sha(RETENTION),'Provider retention differs')
    original_path=ROOT/'manifests/quartz-form-correction-preparation-v1.json'
    require(prep['original_correction_preparation_sha256']==sha(original_path),'Original preparation differs')
    plan,links=derive(read(original_path),retained)
    require(prep['plan']==plan and prep['original_case_links']==links,'Recovery selection differs')
    require(prep['qualification_sha256']==sha(ROOT/'manifests/quartz-public-qualification-freeze-v1.json'),'Qualification differs')
    public=read(ROOT/'manifests/quartz-public-qualification-preparation-v1.json')
    require(prep['environment']==public['environment'],'Public host context differs')
    return prep

def verify():
    prep=preparation_verified();frozen=read(FREEZE)
    require(frozen['primary_freeze_complete'] and frozen['preparation_sha256']==sha(PREPARATION),'Recovery release differs')
    require(frozen['qualification_sha256']==prep['qualification_sha256'],'Qualification release differs')
    ci_path=ROOT/frozen['hosted_ci_record'];require(sha(ci_path)==frozen['hosted_ci_record_sha256'],'CI record differs')
    ci=read(ci_path);ci_accepted(ci,frozen['source_commit']);require(ci['id']==frozen['hosted_ci_run'],'CI identity differs')
    return {'recovery_initial_units':len(prep['plan']['initial_batches']),'hosted_ci_run':ci['id'],'scope':prep['scope']}
if __name__=='__main__':print(verify())
