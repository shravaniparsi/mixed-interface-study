"""Fixed, previously exposed diagnostic selection, not a primary campaign."""
from realworld_identity_campaign import plan_for
from mixed_interface.repetition import require
IDS=('profile-bio-valid','profile-username-null','profile-username-length60','profile-username-length61')


def jobs(registry):
    initial=plan_for(registry)['schedule']['initial_jobs']
    selected=[j for j in initial if j['pair_id'] in IDS]
    require(tuple(j['pair_id'] for j in selected)==IDS,'Bounded diagnostic order differs')
    return selected
