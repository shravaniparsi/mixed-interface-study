"""Validate original transport evidence before applying the reference terminal bridge."""
from pathlib import Path
from realworld_legacy_jobs_v8 import read_job as literal_read_job,validate_job
from realworld_terminal_campaign import read,sha
from realworld_reference_terminal_v2 import extract
from mixed_interface.repetition import require


def read_job(directory,job,registry,execution):
    original=literal_read_job(directory,job,registry,execution)
    if job['entry_kind']=='singleton':return original
    directory=Path(directory);path=next((directory/'run').glob('*/summary.json'))
    root=path.parent;summary=read(path)
    branches={b['continuation']:(read(root/b['evidence']),b) for b in summary['branches']}
    evidence={'summary':sha(path),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json'),
              **{b['evidence']:sha(root/b['evidence']) for b in summary['branches']}}
    result=extract(job,branches,validate_job(job,registry),read(root/'fixture-references.json'),
                   summary['fixture_sha256'],True,evidence)
    require(result['literal_terminal']==original['terminal'] and result['branches']==original['branches'],
            'Evidence changed during reference reconstruction')
    return result
