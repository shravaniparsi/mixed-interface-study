# Unified retrospective control analysis

The common attribution layer preserves the origin of each observation and separates assigned continuation checks, shared reads, execution guards and unresolved policy. PetClinic target and relationship reads executed before both continuation routes are now shared prefix observations. The historical reducer and raw observations remain unchanged.

| Source catalog | Branches | Declared pairs | Accepted pairs | Rejected-prefix pairs | Singletons |
| --- | ---: | ---: | ---: | ---: | ---: |
| RealWorld legacy controls | 16 | 7 | 4 | 3 | 2 |
| RealWorld generated controls | 6 | 3 | 2 | 1 | 0 |
| PetClinic integrity controls | 12 | 6 | 3 | 3 | 0 |
| Quartz paired controls | 4 | 2 | 2 | 0 | 0 |
| Total | 38 | 18 | 11 | 7 | 2 |

All eleven accepted control pairs show neither an API-assigned nor a native-assigned check mismatch. No pair has a shared-check mismatch. These ordinary controls validate accounting; they do not estimate added diagnostic value or establish defects. Rejected prefixes have no continuation overlap result. Catalog entries are not independent samples and none is primary-evaluation eligible.

The input manifest pins 66 files from previously executed hosted runs. The common rules explicitly classify 140 source-specific check identifiers. Unknown check vocabulary, incomplete evidence and failed comparability guards cannot become clean comparisons. Eight gates cover declared and observed prefix equivalence, initial and pre-candidate states, reset evidence, accepted-prefix state and intended consumer command. Gate applicability differs for rejected prefixes.

Reproduce with `PYTHONPATH=src python scripts/build_control_analysis.py --verify`. CI verifies exact regeneration of both derived JSON reports from tracked evidence. The new PetClinic extractor is restricted to the current integrity-control source; it is not qualified for arbitrary future boundary failures.

Next, qualify browser interruption/cleanup and timing, settle the remaining normalization rules, then freeze the primary campaign. Forty Quartz mutation branches remain unexecuted. No new application or boundary executions were performed for this analysis.
