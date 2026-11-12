# All 106 valid-service golden tests qualify

The original golden tests pass against all three pinned valid implementations after one documented reset-instrument correction. This establishes a valid-service baseline. It does not yet validate mutant behavior, detect new application defects, or demonstrate an advantage of a proposed research method.

| Service | Golden tests executed | Passed | Qualification run |
|---|---:|---:|---|
| FastAPI | 63 | 63 | 43133202268 |
| TodoApp | 14 | 14 | 43133202268 |
| NestJS RealWorld | 29 | 29 | 43134240767 |
| Total qualified requirements | 106 | 106 | Two runs, four application jobs |

The first NestJS job stopped on its initial reset before executing any golden test. It attempted to truncate article_tags_tag, which does not exist. The upstream ArticleEntity stores tags as a simple-array column. The single correction removed that table from the reset list and checked that all six actual data tables were empty before each test. Application code, requirement texts and golden assertions were unchanged. The failed attempt remains in the initial archive and counts toward resource usage; it is not counted as a failing application test or erased by the correction.

Verification reconstructs all test classifications from raw JUnit, command exit status, reset and HTTP health evidence, registered instrument hashes, and complete source/test input hashes. The correction also verifies six zero table counts before each test. All 106 qualified tests have actual test-process evidence, nonempty unskipped JUnit results and passing process exit codes. No unattempted requirement remains in the qualified baseline.

## Scheduling diagnosis

The minimal echo workflow 43132605142 succeeded, then full unit workflow 43132778538 succeeded. Rerunning old handle 43096414710 still failed before jobs were created. One fresh dispatch, at exactly the original experiment commit b137f849a95b28adf0013c3d0a36458dbb819920 and with the original workflow unchanged, successfully scheduled the three application jobs. This resolves the practical scheduling blockage. It does not prove GitHub's internal root cause or establish that the old handle was permanently invalid.

The corrected NestJS runner was registered at dca9f1c6bd158e43f06a92a84f108dc28b6f29df. Both runs used RESTestBench 4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae. Initial failure, platform failures, correction registration and successful evidence are separately preserved.

## Resources and next scientific gate

Initial application-job elapsed time was 8.0333 minutes; the correction used 4.2333 minutes. Total: 12.2667 minutes across four jobs, below the registered 100-minute ceiling. These are GitHub job wall times, not invoice charges, and exclude unit checks and the three-second echo diagnostic. Paid model calls: zero. The single application correction allowance is exhausted; no further valid-service repeat is registered.

Static applicability of 228 mutants and valid-service behavior of 106 golden tests are now established separately. Mutant compilation, execution and detection remain unverified. Benchmark admission therefore remains incomplete. A method comparison also still needs a specific incremental-value hypothesis and competent baselines fixed before outcomes. Successful infrastructure qualification alone is not a Q1 contribution.

Reconstruct the initial run with `scripts/extension/verify_restestbench_valid_golden_fresh_v1.py` and the correction/combined coverage with `scripts/extension/verify_restestbench_nestjs_correction_v1.py`, using the corresponding raw result directories and manifests. Source and golden tests are already exposed to this study; no blind held-out claim is made.
