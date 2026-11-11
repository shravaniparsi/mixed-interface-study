# Valid-service golden-test qualification v1

## Frozen scope

RESTestBench commit 4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae; all original golden tests corresponding to the existing 106-file requirement inventory: FastAPI IDs 1–63, NestJS IDs 1–29, TodoApp IDs 1–14, ascending within service. No substitutions, modified assertions, selected failures or test regeneration. Source, golden tests, requirement descriptions and released results are exposed; this is benchmark qualification, not a blind method comparison. No mutants are installed in this pass.

## Execution and gates

Use isolated Ubuntu 24.04 GitHub-hosted jobs, Python 3.12, pytest 8.4.2 and requests 2.32.5. Copy pinned original services to working directories. Build only backend services and their dependencies; do not build FastAPI frontend or browser tests. Preserve source/test hashes, package versions, Docker image IDs, setup/reset/health/test logs, process return codes and JUnit results.

Use explicit checked resets rather than the upstream scripts' ignored errors. FastAPI drops/recreates the public database schema, runs migrations and seeds initial data. NestJS restarts the application and truncates its seven listed domain tables with foreign-key checks disabled, checking the database command return code. TodoApp removes the isolated Compose stack and database volume, then restarts it. Require a successful reset and HTTP health status 200 before running each test. These are disclosed infrastructure adaptations; the application source and golden assertions remain unchanged.

Each golden test runs alone with a 60-second process-group timeout. Passing requires exit code zero and at least one JUnit test, with no failures, errors or skipped tests. Other outcomes retain separate test_failed, timeout, collection/no-test, setup/reset/health-failure classifications. A passing test only qualifies its behavior on this valid service; it does not establish mutant detection or general semantic validity. Continue independent requirement cases after test failures; stop that service after reset/health failure. Retain unattempted IDs explicitly. No repeated test to seek a pass.

## Resource and stopping rules

Three initial application jobs, each at most 25 minutes, matrix max-parallel 1: maximum 75 initial application-job minutes. One additional correction job, at most 25 minutes, may be registered for an evidenced infrastructure/instrument defect; not for a test assertion failure. Maximum aggregate 100 application-job minutes for this qualification, excluding unit CI. Zero paid models; public standard runners only, within the existing $100 total ceiling. No alternate infrastructure purchases or application scope expansion are authorized by this protocol.

No automatic retries, repeat runs, or mutant jobs. Record all failed/partial jobs and actual elapsed job minutes. A later mutant or method comparison needs a separate protocol, qualified baseline evidence, and frozen scoring/eligibility rules before execution. Success of this phase cannot itself establish a Q1 contribution.
