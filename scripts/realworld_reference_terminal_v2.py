"""Prospective terminal integration of the conservative reference proof."""
from copy import deepcopy
from realworld_legacy_jobs_v8 import extract as literal_extract
from realworld_reference_comparison_v1 import compare
from mixed_interface.terminal_outcomes import terminal


def extract(job, branches, spec, fixture, fixture_sha, cleanup, evidence):
    result=literal_extract(job,branches,spec,fixture,fixture_sha,cleanup,evidence)
    if job['entry_kind']=='singleton':return result
    proof=compare(job,branches,spec,fixture,fixture_sha,cleanup,evidence)
    result['literal_terminal']=deepcopy(result['terminal'])
    result['reference_comparison']=proof
    if proof['reference_comparison_qualified']:
        outcome=deepcopy(result['terminal']['outcome'])
        outcome.update(execution='complete',channel_discrepancy=False,check_failure=False)
        result['comparability']=deepcopy(proof['derived_gates'])
        outcome['observation_signature']['gates']=deepcopy(proof['derived_gates'])
        outcome['observation_signature']['reference_comparison']={
            'version':proof['comparison_version'],'local_bindings':deepcopy(proof['local_bindings'])}
        result['terminal']=terminal(outcome,'clean_observation',evidence)
    return result
