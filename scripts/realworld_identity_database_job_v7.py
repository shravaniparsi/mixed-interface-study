"""Source-qualified v7 paired identity/database loader; engineering diagnostics only."""
from pathlib import Path
from copy import deepcopy
from realworld_identity_campaign import ROOT, read, sha, reducer, validate_job
from realworld_identity_bridge_v1 import pair_result
from realworld_identity_measurements_v2 import extract
from validate_identity_database_capture_v2 import validate as validate_database
from mixed_interface.write_observations import measure
from mixed_interface.repetition import require


def bound_measurement(raw, directory, spec, fixture, classified):
    sidecar=extract(raw,spec,fixture,classified)
    require(sidecar['qualified'],'Trace measurement not qualified: '+str(sidecar.get('issues')))
    database=validate_database(raw,directory,fixture)
    snapshots=database['snapshots']
    def view(stage):
        value=snapshots[stage]
        return {'state':'observed','projection':{**value['user'],'articles':value['articles']}}
    measurement=measure(raw['observations']['prefix_status'],view('before_prefix'),view('after_prefix'),
                        {'state':'not_planned'},spec['prefix_payload'],sidecar['measurement']['readbacks'])
    measurement['continuation']=deepcopy(sidecar['measurement']['continuation'])
    final={'state':'not_executed'}
    if 'after_continuation' in snapshots:
        final={'state':'observed','projection':view('after_continuation')['projection']}
    return {'qualified':True,'measurement':measurement,'continuation_database':final,
            'requirement_policy':deepcopy(spec['expectation']),
            'database_scope':database['scope'],'snapshot_sha256':{k:v['sha256'] for k,v in raw['database_capture']['snapshots'].items()},
            'restart_observed':False}


def read_job(directory,job,registry,execution):
    directory=Path(directory);spec=validate_job(job,registry)
    require(execution.get('exit_confirmed') is True and not execution.get('errors') and execution.get('returncode')==0,'Runner exit not clean')
    summaries=list((directory/'run').glob('*/summary.json'))
    require(len(summaries)==1,'Expected one job summary')
    path=summaries[0];root=path.parent;summary=read(path)
    require(summary['job']==job and summary['job_sha256']==sha(directory/'job.json'),'Executed job differs')
    require(read(root/'registered-candidates.json')==registry and summary['registry_sha256']==sha(root/'registered-candidates.json'),'Registry differs')
    require(summary['status']=='completed' and summary['frontend_exit_confirmed'] is True,'Incomplete job')
    expected=[b['case_id'] for b in job['branches']]
    require([b['case_id'] for b in summary['branches']]==expected,'Branch order differs')
    require(summary['schedule']==[{'candidate_id':spec['candidate_id'],'order':[b['continuation'] for b in job['branches']]}],'Declared order differs')
    expected_sources={'run_realworld_pair_job_v7.py','realworld_identity_case_v2.mjs','run_realworld_pilot.py','response_capture.mjs','realworld_integrity.mjs','phase_clock.mjs','realworld_normalization.mjs','validate_realworld_paired_controls.py','summarize_realworld_oracle_components.py','normalization.py','realworld_identity_v1.mjs','realworld_identity_extract_v1.py','realworld_database_capture_v2.mjs','capture_identity_database_v2.py','realworld_identity_db_state_v1.py','validate_identity_database_capture_v2.py'}
    require(set(summary['source_sha256'])==expected_sources,'Runner source inventory differs')
    for name,h in summary['source_sha256'].items():
        live=ROOT/('src/mixed_interface/normalization.py' if name=='normalization.py' else 'scripts/'+name)
        require(sha(root/name)==h==sha(live),'Executed source differs: '+name)
    require(summary['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and summary['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','Application revision differs')
    fixture=read(root/'fixture-references.json');branches={};evidence={'summary':sha(path),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json')}
    for b in summary['branches']:
        require(b['evidence']==b['case_id']+'.json','Unexpected evidence path')
        raw=read(root/b['evidence']);reducer.validate_timing(raw,b)
        require(b['candidate_id']==spec['candidate_id'] and raw['candidate_id']==spec['candidate_id'] and raw['continuation_interface']==b['continuation'],'Raw branch identity differs')
        branches[b['continuation']]=(raw,b);evidence[b['evidence']]=sha(root/b['evidence'])
    legacy=pair_result(job,branches,spec,fixture,summary['fixture_sha256'],True,evidence)
    require(summary.get('database_capture_version')==2,'Database runner version differs')
    require(set(branches)=={'api','ui'},'Paired branch inventory differs')
    measurements={}
    for channel,(raw,branch) in branches.items():
        require(branch.get('status')=='completed' and type(branch.get('exit_code')) is int
                and branch['exit_code']==0 and branch.get('backend_exit_confirmed') is True
                and not branch.get('timed_out') and not branch.get('interrupted'),'Branch runtime incomplete')
        require(branch.get('reset_sha256')==summary['fixture_sha256'] and len(summary['fixture_sha256'])==64
                and all(c in '0123456789abcdef' for c in summary['fixture_sha256']),'Reset binding differs')
        require(branch['continuation']==next(b['continuation'] for b in job['branches'] if b['case_id']==branch['case_id']),
                'Assigned branch differs')
        measurements[channel]=bound_measurement(raw,root/(branch['case_id']+'-database'),spec,fixture,legacy['branches'][channel])
        measurements[channel]['raw_sha256']=sha(root/branch['evidence'])
        measurements[channel]['reset_sha256']=branch['reset_sha256']
    a,u=(measurements[c] for c in ('api','ui'))
    return {'schema_version':7,'job_id':job['job_id'],'legacy_result':legacy,'measurements':measurements,
            'database_pair_comparison':{'same_before_projection':a['measurement']['persistence']['before']==u['measurement']['persistence']['before'],
                'same_after_prefix_projection':a['measurement']['persistence']['immediate']==u['measurement']['persistence']['immediate']},
            'primary_freeze_complete':False,'new_primary_samples':0}

