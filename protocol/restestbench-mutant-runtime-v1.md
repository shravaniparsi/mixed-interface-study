# Complete golden-test mutant runtime qualification v1

## Scope and exposure

Use RESTestBench commit 4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae. Include all 228 listed mutants in the frozen 106-requirement inventory (FastAPI 141, NestJS 65, TodoApp 22), in ascending requirement ID and original zero-based mutant order. All original golden tests and mutation labels are exposed. This is benchmark qualification, not a blind discovery study, a new method comparison or a natural-defect count.

The valid-service gate has passed for all 106 requirements, with the failed initial NestJS reset and its single correction preserved separately. For this new phase, execute a fresh original-source golden control for each requirement before its mutants. Stop a service if that control does not qualify. Do not run mutants under a failed control, substitute requirements, repair assertions or repeat outcomes to seek a pass.

## Installation, execution and classifications

Restore every mutation-target source file from the pinned original before each trial. Apply only the selected mutant using the unchanged upstream Mutator. Require successful application and changed source bytes. Restart the application process for each trial; do not rely on hot reload. Record container state and verify that the mutation target bytes inside the container match the installed bytes. Require checked database reset and HTTP health before testing. FastAPI uses checked schema reset/migrations/seed; NestJS uses the corrected six-table reset with zero-count checks; TodoApp recreates its isolated database volume.

Golden tests remain byte-for-byte unchanged and run individually with a 60-second process-group timeout. Preserve JUnit, test logs, application logs on non-pass outcomes, command exits, reset/health evidence, target hashes and runtime versions. Mutant installation failure, setup/readiness failure, missing or malformed JUnit, test error, skipped/no tests, timeout, and execution-qualified test failure remain separate categories. No failure to apply a mutation receives detection credit.

An execution-qualified test failure requires: a qualified original-source control, successfully installed changed bytes confirmed inside a restarted container, successful reset and health, executed nonempty unskipped JUnit with failures but no errors, and process exit code 1. This is a candidate oracle detection, not an adjudicated semantic defect: unrelated runtime exceptions may still appear as JUnit failures, and logs must be reviewed before stronger claims. A passing mutant test is labelled survived, not equivalent. A startup failure can be caused by the mutation, but is not silently counted as a semantic test detection. Restore pristine sources before moving to the next independent trial.

## Bounds and stopping

Three standard public Ubuntu jobs, max-parallel 1, each with a 40-minute hard limit and a 35-minute collection soft limit, allowing cleanup/artifact retention. Maximum initial application-job time 120 minutes. No automatic retries or correction job is registered. Any later instrument correction needs an explicit evidence-based amendment before dispatch, while retaining all initial failures. Zero paid model calls and no purchased compute. This phase does not change the existing $100 project ceiling.

At the soft limit, retain completed trials and explicitly enumerate unattempted keys. Do not treat a job conclusion as a scientific verdict. Record actual elapsed application-job minutes separately from unit CI and invoice cost. A complete result requires accounting for every registered key, even if some are unqualified or unattempted. No method superiority or Q1 readiness follows from benchmark qualification alone.
