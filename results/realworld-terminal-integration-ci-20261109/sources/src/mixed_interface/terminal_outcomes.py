"""Version 2 terminal contract; semantic observations and dispatch safety are separate."""
from copy import deepcopy
from .repetition import digest, require, validate_outcome

SCHEMA_VERSION = 2
# action, repeat eligibility, contributes complete semantic evidence
POLICY = {
    'clean_observation': ('continue', False, True),
    'completed_mismatch': ('continue', True, True),
    'matched_rejection': ('continue', False, True),
    'unresolved_policy': ('continue', False, False),
    'application_response_failure': ('continue', True, False),
    'incomparable_observation': ('continue', True, False),
    'missing_evidence': ('halt', False, False),
    'case_timeout': ('halt', False, False),
    'environment_failure': ('halt', False, False),
    'cleanup_unconfirmed': ('halt', False, False),
    'interrupted': ('halt', False, False),
}
POLICY_SHA256 = digest(POLICY)


def terminal(outcome, kind, evidence):
    """Called by source-qualified bridges, never inferred from a process exit alone.

    evidence contains immutable artifact references, not a substitute for a bridge's
    source/selection/trace checks. The contract validates shape and consistency.
    """
    value = {'schema_version': SCHEMA_VERSION, 'policy_sha256': POLICY_SHA256,
             'kind': kind, 'outcome': deepcopy(outcome), 'evidence': deepcopy(evidence)}
    validate(value)
    return value


def validate(value):
    require(set(value) == {'schema_version', 'policy_sha256', 'kind', 'outcome', 'evidence'}, 'Terminal fields differ')
    require(type(value['schema_version']) is int and value['schema_version'] == SCHEMA_VERSION, 'Terminal version differs')
    require(value['policy_sha256'] == POLICY_SHA256, 'Terminal policy differs')
    require(value['kind'] in POLICY, 'Unknown terminal kind')
    o = value['outcome']; validate_outcome(o)
    require(isinstance(o['job_id'], str) and bool(o['job_id']), 'Missing job identity')
    refs = value['evidence']
    require(isinstance(refs, dict) and bool(refs), 'Evidence references required')
    for name, sha in refs.items():
        require(isinstance(name, str) and bool(name) and isinstance(sha, str) and len(sha) == 64
                and all(c in '0123456789abcdef' for c in sha), 'Invalid evidence reference')
    kind = value['kind']; action, repeat, complete = POLICY[kind]
    if kind == 'cleanup_unconfirmed':
        require(not o['cleanup_confirmed'], 'Cleanup classification contradicts evidence')
    else:
        require(o['cleanup_confirmed'], 'Unconfirmed cleanup takes precedence')
    if complete:
        require(o['execution'] == 'complete' and o['prefix'] in ('accepted', 'rejected'), 'Complete terminal lacks comparable evidence')
    if kind in ('clean_observation', 'matched_rejection'):
        require(o['channel_discrepancy'] is False and o['check_failure'] is False, 'Clean terminal contains diagnostic failure')
        require(o['prefix'] == ('accepted' if kind == 'clean_observation' else 'rejected'), 'Prefix classification differs')
    if kind == 'completed_mismatch':
        require(o['check_failure'] is True or o['channel_discrepancy'] is True, 'Mismatch has no diagnostic signal')
    if kind == 'unresolved_policy':
        require(o['check_failure'] is not True and o['channel_discrepancy'] is not True, 'Diagnostic failure takes precedence over policy')
    if kind in ('application_response_failure', 'incomparable_observation'):
        require(o['execution'] == 'incomplete', 'Partial observation must remain incomplete')
        require(isinstance(o['observation_signature'], dict) and bool(o['observation_signature']), 'Partial observation lacks retained signature')
    digest(value)


def decision(value):
    validate(value)
    action, repeat, complete = POLICY[value['kind']]
    return {'action': action, 'repeat': repeat, 'semantic_evidence_complete': complete}


def observation_signature(value):
    validate(value)
    return {'kind': value['kind'], **{k: value['outcome'][k] for k in
        ('execution', 'prefix', 'channel_discrepancy', 'check_failure', 'observation_signature')}}
