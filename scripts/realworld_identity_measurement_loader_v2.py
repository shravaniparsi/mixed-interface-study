"""Source-qualified paired measurement replay; not a campaign dispatch adapter."""
from realworld_identity_campaign import read_job as read_legacy_job, read, sha, validate_job
from realworld_identity_measurements_v2 import extract
from pathlib import Path


def read_job(directory, job, registry, execution):
    # Frozen loader checks source inventory, runtime, selection, timing and cleanup.
    legacy = read_legacy_job(directory, job, registry, execution)
    root = next((Path(directory) / 'run').glob('*/summary.json')).parent
    summary = read(root / 'summary.json')
    fixture = read(root / 'fixture-references.json')
    spec = validate_job(job, registry)
    measurements = {}
    for branch in summary['branches']:
        channel = branch['continuation']
        raw = read(root / branch['evidence'])
        valid_reset = (isinstance(summary['fixture_sha256'], str) and len(summary['fixture_sha256']) == 64
                       and all(c in '0123456789abcdef' for c in summary['fixture_sha256'])
                       and branch.get('reset_sha256') == summary['fixture_sha256'])
        if (branch.get('backend_exit_confirmed') is not True or branch.get('status') != 'completed'
                or type(branch.get('exit_code')) is not int or branch['exit_code'] != 0
                or branch.get('timed_out') or branch.get('interrupted') or not valid_reset):
            measured = {'qualified': False, 'issues': ['Incomplete runtime or cleanup']}
        else:
            measured = extract(raw, spec, fixture, legacy['branches'][channel])
        measurements[channel] = {**measured, 'raw_sha256': sha(root / branch['evidence']),
                                 'fixture_sha256': summary['fixture_sha256']}
    return {'schema_version': 2, 'job_id': job['job_id'], 'legacy_result': legacy,
            'measurements': measurements, 'dispatch_authorized': False,
            'scope': 'derived paired measurements; original terminal decisions retained'}
