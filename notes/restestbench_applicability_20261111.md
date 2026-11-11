# Complete static mutation applicability qualification

All 106 requirement files parse with the pinned upstream parser. All 228 listed mutants apply independently to fresh copies of their target files and change source bytes: 141 FastAPI, 65 NestJS RealWorld and 22 TodoApp mutations. No mutation returns false, raises an exception or reports success without changing bytes.

This closes a narrow admission gate: the declared edits can be installed into the source snapshot. It does not establish compilation, service health, changed observable behavior, golden-test adequacy or semantic correctness. No service, generated test or golden test ran.

The scope was fixed in `protocol/restestbench-mutation-applicability-v1.md` before reading requirement bodies. Every file in the existing inventory was included, with no substitutions or repairs. Each application starts from the original target bytes and uses unmodified upstream `Requirement` and `Mutator` code. The 106 requirement hashes match the earlier directory inventory. All 13 target source hashes also match GitHub contents metadata at commit 4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae. A compact input archive and complete per-mutant before/after hashes permit reconstruction.

TodoApp requirement 12, mutant index 1 also applies in this snapshot. Therefore the six historical failed-application records identified in the released-result audit cannot be explained by simply replaying the edit against this snapshot. The earlier execution environment or code state is not established here, and the historical false credits are not erased by current applicability.

This pass exposes all mutation definitions to the research process. The benchmark must not be presented as a blind held-out discovery set. A future test generator must receive only its registered input information in an isolated directory, with no mutation definitions, golden tests or released test outputs available.

Remaining benchmark gates are (1) bounded compilation/service qualification, (2) original golden tests passing on valid implementations and their behavior on applied mutants, and (3) explicit classification of setup failures and test outcomes. A scientific method comparison additionally requires a specific novelty hypothesis and competent baselines fixed before its outcomes. Static applicability is not evidence that our proposed method improves on those baselines.

Reproduce with Python 3.12: `python scripts/extension/qualify_restestbench_applicability_v1.py --verify`. This requires no installed dependencies, Docker, network or model calls. Upstream material remains under the license copied in `evidence/restestbench-source-v1/LICENSE`. The complete input source is [the pinned benchmark](https://github.com/casablancahotelsoftware/RESTestBench/tree/4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae).
