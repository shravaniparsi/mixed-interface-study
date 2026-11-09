#!/usr/bin/env python3
"""Verify a halted identity campaign without promoting it to completed evidence."""
import hashlib,json
from pathlib import Path
from run_realworld_identity_campaign import ROOT,SOURCES
from realworld_identity_campaign import read,sha,plan_for,read_job
from mixed_interface.campaign_v2 import drive
from mixed_interface.repetition import require


def reconstruct_halt(directory):
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for name,h in cert['sources'].items():require(sha(directory/'sources'/name)==h==sha(ROOT/name),'Executed source differs: '+name)
    registry=read(directory/'sources/manifests/realworld-identity-controls-v1.json')
    require(cert['plan']==plan_for(registry),'Plan differs')
    visited=[]
    def execute(job):
        d=directory/job['job_id'];require(read(d/'job.json')==job and read(d/'dispatch.json')['job']==job,'Dispatched job differs')
        result=read_job(d,job,registry,read(d/'execution.json'))
        require(result==read(d/'observations.json'),'Recorded observations differ')
        summaries=list((d/'run').glob('*/summary.json'));require(len(summaries)==1 and read(summaries[0])['source_commit']==cert['source_commit'],'Declared source commit differs')
        visited.append(job['job_id']);return result['terminal']
    state=drive(cert['plan'],execute,lambda _:None)
    require(state==read(directory/'campaign.json'),'Halted ledger differs')
    require(sorted(p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources')==sorted(visited),'Attempt directory inventory differs')
    require(state['status']=='halted_terminal_outcome' and len(state['initial'])==5 and not state['repeated'],'Expected complete initial sweep followed by terminal halt')
    kinds=[v['kind'] for v in state['initial']]
    require(kinds==['clean_observation','matched_rejection','matched_rejection','unresolved_policy','missing_evidence'],'Terminal sequence differs')
    incomplete=read(directory/'initial-004/observations.json')
    require(incomplete['terminal']['outcome']['cleanup_confirmed'] is True,'Cleanup unconfirmed')
    details={}
    for p in (directory/'initial-004/run').glob('*/*-r1.json'):
        raw=read(p);channel=raw['continuation_interface'];after=raw['identity']['after']
        require(raw['observations']['prefix_status']==500 and after['readable'] is False,'Incomplete case response differs')
        responses={x['path']:x['status'] for x in after['reads']}
        require(responses.get('/api/user')==500 and sum(status==500 for status in responses.values())==4,'Post-write unreadability differs')
        require(not raw['observations']['api_continuation_started'] and not raw['observations']['ui_continuation_started'],'Unexpected continuation after 500')
        # Bind retained diagnostic reads to the original capture even though they cannot form a readable projection.
        for probe in after['reads']:
            e=raw['trace'][probe['response_sequence']-1]
            require(e['type']=='response' and e['source']=='state_probe' and e['method']=='GET' and e['phase']=='failed_prefix_followup','Unbound failure probe')
            require(all(e[k]==probe[k] for k in ('path','status','data')),'Failure probe differs from trace')
        details[channel]=responses
    require(set(details)=={'api','ui'},'Missing incomplete-case channel')
    return {'verified_halted_ledger':True,'campaign_completed':False,'initial_pair_attempts':5,'branches_executed':10,'followup_jobs':0,'terminal_sequence':kinds,'incomplete_case':'profile-username-length61','incomplete_case_read_statuses':details,'source_commit':cert['source_commit'],'campaign_sha256':sha(directory/'campaign.json'),'primary_freeze_complete':False}


def verify_failed_setup():
    manifest=json.loads((ROOT/'manifests/realworld-identity-setup-failure.json').read_bytes())
    directory=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(manifest['input_sha256']):raise ValueError('Failed setup inventory differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['input_sha256'][name]:raise ValueError('Failed setup hash differs: '+name)
    if manifest['qualified'] is not False or manifest['candidate_prefix_writes']!=0:raise ValueError('Failed setup qualification differs')
    raws=list(directory.glob('*/run/*/profile-bio-valid-api-r1.json'))
    if len(raws)!=1:raise ValueError('Failed setup branch inventory differs')
    raw=json.loads(raws[0].read_bytes())
    if any(e.get('phase')=='prefix' and e.get('type')=='request' for e in raw['trace']):raise ValueError('Unexpected candidate prefix in setup attempt')



def main():
    verify_failed_setup()
    manifest=read(ROOT/'manifests/realworld-identity-halted-integration.json');d=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(d)):p for p in d.rglob('*') if p.is_file()}
    require(set(files)==set(manifest['input_sha256']),'Halted archive inventory differs')
    for name,path in files.items():require(sha(path)==manifest['input_sha256'][name],'Halted archive hash differs: '+name)
    observed=reconstruct_halt(d)
    require(observed==manifest['verification'],'Halted archive reconstruction differs')
    require(observed['source_commit']==manifest['source_commit'] and manifest['campaign_completed'] is False and manifest['coverage_promoted'] is False,'Halted result promoted or source changed')
    print('Verified halted identity ledger: five attempted pairs, ten branches; final case remains incomplete.')


if __name__=='__main__':main()
