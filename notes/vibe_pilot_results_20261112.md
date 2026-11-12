# Completed independent scoring pilot and research decision

Run 43152134972 completed successfully at study commit 2efa3a99c4c33f582d82ab16a5227cc05b91148d. The registered ten archived suites cover five models, contexts L0 and L4, and repetition 1. Selection was outcome-exposed and exploratory.

| Context | Executed suite trials | Qualified mutant comparisons | Aggregate kills | Identified new failures | Disagreements |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0 | 75 | 65 | 20 | 20 | 0 |
| L4 | 75 | 65 | 30 | 30 | 0 |

All 170 registered records are accounted for: 150 executed suite trials, ten nonmatching mutations and ten syntax-invalid mutations. The executions include 20 original controls and 130 mutant trials. Before/after original controls have stable per-test outcome classes; this does not mean every original test passed. Total application-job time was 5.5667 minutes, within the 40-minute bound; paid model calls were zero.

This pilot found no aggregate-count disagreement with individually identified new failures. Neither rule establishes that a failing test detects the intended business fault. Semantic adjudication is incomplete. The ten suites are not independent samples of current model quality, and one exposed repetition does not support model ranking inference. Do not expand this matrix simply to obtain a positive result.

## Reproduction and analysis corrections

Raw evidence is in results/vibe-per-test-pilot-v1-ci-43152134972. The results manifest records hashes for every archived file. Reconstruct with:

```
python scripts/extension/verify_vibe_per_test_pilot_v1.py --archive results/vibe-per-test-pilot-v1-ci-43152134972 --output manifests/vibe-per-test-pilot-results-v1.json --verify
```

The analysis reader initially split JSONL on all Unicode line separators. Binary HTTP content can legally contain such characters inside JSON strings. The corrected reader splits only on ASCII LF and explicitly reports malformed records. A regression test covers this distinction. No raw evidence or registered experiment code changed.

Unit run 43152120492 failed because Python 3.9 and 3.12 phrase the same SyntaxError differently. The source audit now compares the mutation bytes, classification, failing line and text while excluding interpreter-specific diagnostic wording. The original manifest retains its original diagnostic. This is a verifier portability correction, not a scientific rerun.

## Feasibility decision

Generic assertion removal and separation of assertion failures from crashes are established prior work; see evaluation_validity_skeptic_20261112.md. The independent Vibe release audit reconstructs its reported scores without discrepancy. Our fresh pilot supplies a null result for the narrower aggregate-count concern. RESTestBench installation-credit findings remain separate and do not establish a general ranking reversal.

The next candidate question is whether synthetic mutation performance predicts detection of historical API defects when test-generation information and execution resources are controlled. Novelty and feasibility remain unconfirmed. A comparison across unrelated applications is not sufficient: mutation scores and historical defect detection must be measured on aligned test suites and application versions. The Defects4REST metadata census contains 108 case directories, 107 nonempty guides and zero runtime-qualified cases. The advertised 110 count and our observed directory count must remain distinct.

Before spending model budget, qualify a small deterministic sample of historical buggy/fixed pairs, demonstrate independent fault oracles, establish a common generator-input policy, and verify relevant prior work. Exclude requirements available only from the bug report from generator inputs. Preserve bug reports and patches for evaluation only. Reject cases requiring live third-party accounts or unreproducible infrastructure. Do not interpret an excluded case as a missed defect.

A defensible next-stage study needs enough distinct projects and defects for project-aware uncertainty estimates, matched resources, simple schema/status and existing-tool baselines, raw fault-level outcomes, and a held-out evaluation after development. Numerical sample targets should follow runtime qualification and a sensitivity analysis, not an invented guarantee of statistical power. If these conditions cannot be met within the remaining budget, stop this candidate rather than present another small demonstration as Q1-ready.
