"""Runtime source inventory for the bounded generated mutation sweep."""
from realworld_generated_runtime_v3 import ROOT,read,branch,jobs,SOURCES as PREPARED
SOURCES=sorted(set(PREPARED+['scripts/realworld_generated_execution_v3.py',
 'scripts/run_realworld_generated_mutations_v3.py','scripts/validate_realworld_generated_mutations_v3.py',
 '.github/workflows/realworld_generated_v3.yml','protocol/realworld-generated-execution-v3.md']))
