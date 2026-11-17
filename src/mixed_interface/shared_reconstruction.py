"""Shared evidence packaging, not automatic model reconstruction or truth verification.

Requirements are declared by the caller. Their completeness, provenance truth and
acquisition cost must be established separately. No missing values are inferred.
"""
import copy
import hashlib
import json

TARGETS={'field_validation','form_validation','submit_decision','api_conformance'}
ORIGINS={'observed_frontend','provided_context','qualified_transform'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def package_shared_evidence(observation, requirements, facts):
    """Bind identical evidence to both consumers; unresolved facts remain explicit."""
    # Reject non-JSON containers/key types; copying prevents caller aliasing.
    def json_types(value):
        if type(value) is dict:
            if any(type(k) is not str for k in value):
                raise ValueError("JSON object keys must be strings")
            for v in value.values():json_types(v)
        elif type(value) is list:
            for v in value:json_types(v)
        elif value is not None and type(value) not in (str,int,float,bool):
            raise ValueError("JSON values required")
    json_types({"observation":observation,"requirements":requirements,"facts":facts})
    data=copy.deepcopy({'observation':observation,'requirements':requirements,'facts':facts})
    digest(data)
    obs=data['observation']
    if obs['target'] not in TARGETS:
        raise ValueError('Unknown observable target')
    context=obs['context']
    if not isinstance(context,dict) or any(not isinstance(context.get(k),str) or not context[k]
            for k in ('revision','operation','actor','lifecycle')):
        raise ValueError('Explicit revision/operation/actor/lifecycle context required')
    if not isinstance(obs['document'],dict):
        raise ValueError('Object observation required')
    if not isinstance(obs.get('point'),str) or not obs['point']:
        raise ValueError('Observation point required')
    binding=digest(obs)
    if not isinstance(requirements,list) or not requirements or any(not isinstance(k,str) or not k for k in requirements):
        raise ValueError('Nonempty declared evidence requirements required')
    if len(set(requirements))!=len(requirements):
        raise ValueError('Duplicate requirements')
    indexed={}
    for fact in data['facts']:
        key=fact['id']
        if not isinstance(key,str) or not key or key in indexed:
            raise ValueError('Invalid or duplicate fact identity')
        indexed[key]=fact
    resolved={};unresolved=[]
    for key in requirements:
        fact=indexed.get(key)
        if fact is None:
            unresolved.append({'id':key,'reason':'not_supplied'});continue
        if fact.get('observation_sha256')!=binding:
            unresolved.append({'id':key,'reason':'stale_or_different_observation'});continue
        if fact.get('origin') not in ORIGINS or not isinstance(fact.get('evidence'),str) or not fact['evidence']:
            unresolved.append({'id':key,'reason':'provenance_assertion_missing'});continue
        status=fact.get('status')
        if status=='known' and 'value' in fact:
            resolved[key]=fact
        elif status=='absent' and 'value' not in fact:
            resolved[key]=fact
        elif status=='unknown':
            unresolved.append({'id':key,'reason':'explicitly_unknown','detail':fact.get('reason')})
        else:
            raise ValueError('Malformed fact state: '+key)
    package={'observation':obs,'declared_requirements':list(requirements),
             'resolved':resolved,'unresolved':unresolved,
             'unused_fact_ids':sorted(set(indexed)-set(requirements)),
             'evidence_complete_for_declared_requirements':not unresolved,
             'requirement_completeness_verified':False,'provenance_truth_verified':False}
    package['shared_input_sha256']=digest(package)
    return package
