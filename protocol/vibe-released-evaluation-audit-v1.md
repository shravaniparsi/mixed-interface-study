# Independent Vibe Testing released-evaluation audit v1

## Scope and exposure

Inspect every per-suite result in the balanced context-axis mutation experiment of Mendeley dataset 10.17632/2xfm6z2p5v.1. The publisher metadata identifies archive SHA-256 d3ba05db5587ce8fcec62cbcb0096d30e10534088ee3012c3f712be84e5a18ec. The advertised design is five models, five context levels and five repetitions (125 suites). Include all files, including degenerate baselines, failed startup, missing outcomes and empty mutation lists. Do not select models, levels or operators using scores.

Before this protocol, the package README, mutation README, mutation definitions, worker code and target requirements were inspected. Released per-suite outcomes and aggregate score values have not been inspected in this phase. The study knows the context-axis design and the baseline-aware aggregate-count kill rule. This is an independent artifact audit and potential replication, not a blind novelty test or a new algorithm.

## Questions and fixed analyses

1. Does the archive match its publisher digest and internal file manifest? Does the released per-suite inventory contain every advertised cell exactly once?
2. How many original-program suites are fully passing, partially failing, degenerate or unavailable? Preserve exact passed/failed/errored counts and statuses.
3. For every mutation record, preserve application state, runtime/error state and recorded kill verdict. When all required counts exist, reconstruct the worker's rule: mutant passed count below original OR failed count above original OR error count above original. Check summary numerator, denominator and percentage against records; enumerate discrepancies without repairing data.
4. Report per-model/context and whole-corpus counts of kills supported by fully passing versus partially failing original suites. A partially failing suite is not automatically an invalid experiment. Aggregate counts cannot identify which individual tests changed outcomes; do not claim an observed false credit or missed defect from missing identities.
5. Report whether per-test identities, exception traces, executed-source hashes, startup/reset proof and return codes are present in the released per-suite records. Absence from those records does not prove such artifacts never existed elsewhere. Do not attribute a failure cause that the retained evidence cannot establish.

No application execution, regeneration, paid calls, rank correction or journal-readiness claim belongs to this phase. Source mutation validity and current portability require separate bounded runtime registration. Keep reported-score reconstruction distinct from semantic fault detection. No API traffic to public production services is permitted or needed.
