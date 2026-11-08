"""Sequential dispatch with immutable job identities and fail-closed stops."""
from copy import deepcopy
from .repetition import followups, summarize, validate_outcome, validate_plan


def drive(plan, execute, checkpoint):
    validate_plan(plan)
    state = {'status': 'running', 'plan_sha256': plan['plan_sha256'], 'initial': [], 'repeated': [],
             'dispatches': [], 'primary_freeze_complete': False}
    def run(job, phase):
        state['dispatches'].append({'job': deepcopy(job), 'phase': phase, 'status': 'started'})
        checkpoint(deepcopy(state))  # Durable intent before application launch.
        try:
            result = execute(deepcopy(job))
            validate_outcome(result)
            if result['job_id'] != job['job_id']: raise ValueError('Executor returned another job')
            state[phase].append(deepcopy(result))
            state['dispatches'][-1]['status'] = 'recorded'
            if not result['cleanup_confirmed'] or result['execution'] != 'complete':
                state['status'] = 'halted_execution_or_cleanup'
            checkpoint(deepcopy(state))
            return state['status'] == 'running'
        except BaseException as error:
            state['status'] = 'halted_executor_error'
            state['dispatches'][-1]['error'] = type(error).__name__+': '+str(error)
            checkpoint(deepcopy(state))
            raise
    for job in plan['initial_jobs']:
        if not run(job, 'initial'): return state
    schedule = followups(plan, state['initial'])
    state['followup_plan'] = schedule
    checkpoint(deepcopy(state))
    for job in schedule['jobs']:
        if not run(job, 'repeated'): return state
    state['repeat_summary'] = summarize(plan, state['initial'], state['repeated'])
    state['status'] = 'completed_observations'
    checkpoint(deepcopy(state))
    return state
