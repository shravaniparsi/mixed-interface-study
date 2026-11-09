#!/usr/bin/env python3
"""Verify all four retained batches without pooling repeated attempts as samples."""
from collections import Counter,defaultdict
from petclinic_expanded_campaign import ROOT,CONTROL,REGISTRY,read,sha
from validate_petclinic_expanded_campaign import validate
from mixed_interface.repetition import require

def summarize(directory):
    contract=read(ROOT/CONTROL);names=set(contract['batches'])
    require({p.name for p in directory.iterdir() if p.is_dir()}==names,'Batch inventory differs')
    reports={};kinds=defaultdict(set);initials=defaultdict(list);counts=Counter();commits=set()
    for name in contract['batches']:
        d=directory/name;report=validate(d)
        require(report==read(d/'verification.json'),'Batch verification differs')
        reports[name]=report;counts.update(report['terminal_counts']);commits.add(report['source_commit'])
        state=read(d/'campaign.json');observations=state['initial']+state['repeated']
        for dispatch,observation in zip(state['dispatches'],observations):
            cid=dispatch['job']['pair_id'];kinds[cid].add(observation['kind'])
            if dispatch['phase']=='initial':initials[cid].append({'batch':name,'kind':observation['kind'],'prefix_http_status':observation['outcome']['observation_signature']['prefix_http_status']})
    require(len(commits)==1,'Mixed source commits')
    registered=[c['id'] for c in read(ROOT/REGISTRY)['candidates']]
    require(set(initials)==set(registered),'Unique candidate coverage differs')
    return {'verified':True,'source_commit':next(iter(commits)),'unique_candidates':len(initials),
        'initial_pair_attempts':sum(r['initial_pairs'] for r in reports.values()),
        'pair_attempts':sum(r['pair_attempts'] for r in reports.values()),
        'branches':sum(r['branches'] for r in reports.values()),'followup_jobs':sum(r['followup_jobs'] for r in reports.values()),
        'terminal_counts':dict(counts),'candidate_terminal_kinds':{cid:sorted(kinds[cid]) for cid in registered},
        'candidate_initial_observations':dict(initials),'batches':reports,
        'independent_sample_size':None,'new_boundary_cases_executed':0,'primary_freeze_complete':False}

def main():
    q=read(ROOT/'manifests/petclinic-expanded-integration-qualification.json');d=ROOT/q['evidence_directory']
    files={str(p.relative_to(d)):p for p in d.rglob('*') if p.is_file()}
    require(set(files)==set(q['input_sha256']),'Archive inventory differs')
    for name,p in files.items():require(sha(p)==q['input_sha256'][name],'Archive hash differs: '+name)
    require(summarize(d)==q['verification'],'Combined verification differs')
    print('PetClinic expanded archive verified across four bounded batches and eighteen unique development candidates.')
if __name__=='__main__':main()
