"""Evaluate a lowered predicate only for an evidenced Angular model field.

This development adapter does not infer API obligations or acquire field-state
observations. Evidence identifiers are provenance assertions, not proof of truth.
"""
import hashlib
import json
from .constraint_transfer import evaluate, outcome


def snapshot_sha256(document):
    encoded=json.dumps(document,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def evaluate_model_template(template, observation, field_state):
    try:
        return _evaluate(template, observation, field_state)
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        return outcome('code_error',f'{type(error).__name__}: {error}')


def _evaluate(template, observation, state):
    if template['framework_version'] != '22.2.3':
        return outcome('unknown','framework_version_unqualified')
    if observation['point'] != 'frontend_model' or observation['complete'] is not True:
        return outcome('unknown','frontend_model_observation_required')
    context=observation['context']
    if any(not context.get(k) for k in ('revision','operation','actor','lifecycle')):
        raise ValueError('Explicit frontend context required')
    if not state or not state.get('evidence'):
        return outcome('unknown','field_state_evidence_missing')
    field=template['field']
    if (state.get('context')!=context or state.get('field')!=field
            or state.get('framework_version')!=template['framework_version']
            or state.get('snapshot_sha256')!=snapshot_sha256(observation['document'])):
        return outcome('unknown','field_state_observation_mismatch')
    materialized=state.get('materialized')
    if materialized is False:
        return outcome('unknown','field_not_materialized',False)
    if materialized is not True:
        return outcome('unknown','field_materialization_unknown')
    document=observation['document']
    if not isinstance(document,dict) or field not in document:
        return outcome('unknown','materialized_field_value_unavailable')
    # No JavaScript undefined sentinel is silently converted to null or empty.
    if any(type(state.get(k)) is not bool for k in ('disabled','hidden','readonly')):
        return outcome('unknown','field_activity_unknown')
    if state['hidden'] or state['readonly']:
        return outcome('unknown','activity_mode_not_runtime_qualified')
    if state['disabled']:
        return outcome('unknown','field_disabled',False)
    value=document[field]
    if value is not None and not isinstance(value,str):
        return outcome('unknown','string_template_domain_mismatch',True)
    # Bounds remain general evaluator instructions, not fully runtime-qualified
    # ranges. The fixed runtime experiment exercised only length bound2.
    rule=dict(rule_id='angular-model:'+field+':'+template['validator'],
              source_evidence=template['source_id'],conflicting_evidence=False,
              scope=context,mapping=dict(status='known',evidence='explicit model field',
                  path=[field],transform='identity'),guards=[],observation_point='frontend_model',
              predicate=template['predicate'],value_policy=template['value_policy'])
    return evaluate(rule,observation)
