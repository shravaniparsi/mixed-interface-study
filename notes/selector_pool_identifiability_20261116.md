# Structural limits of the existing selector pools

An outcome-free inspection of the two generated pools explains why simply timing another campaign would not establish the original method claim. This is an analysis of the implementation and declared features, not an application experiment or a new testing algorithm.

| Pool | Candidates | Dependency signatures | Route-obligation signatures | Identical feature-class sizes |
| --- | ---: | ---: | ---: | --- |
| RealWorld article create/body edit | 18 | 1 | 4 | 1, 1, 8, 8 |
| Quartz job create/description edit | 44 | 1 | 4 | 1, 1, 21, 21 |

Every candidate in each pool has estimated cost 1.0. The value is declared input to the selector, not an observed one-second runtime. The selector receives dependencies, route obligations, estimated costs and case IDs, but no payload-semantic distinction within each listed feature class.

## Exact dependency/random equivalence

Let D be the common dependency set in a pool, C the dependencies covered so far and c the common estimated cost. Every remaining candidate receives the same dependency-greedy score |D minus C| / c. Thus every candidate belongs to the best-score tie set at every step, regardless of which subset has been covered. The implementation orders candidates by case ID and uses the same seeded random choice for both strategies. Starting with the same seed and feeding common feedback, dependency-greedy and random therefore choose identical sequences by induction. This holds for these fixed pools, not arbitrary pools or different cost policies.

The audit cross-checks the actual implementation for seeds 0, 1 and 7 under no-coverage and full-declared-coverage synthetic feedback. Those checks corroborate the implementation argument; they are not scientific repetitions or evidence that all declared dependencies were exercised in the applications. No labels, expected outcomes or recorded failures were supplied to selection.

## What route-greedy can distinguish

Route-greedy can prioritize uncovered interface routes, so it is not generally equivalent to random here. However, it cannot rank eight RealWorld or 21 Quartz variants that share the same declared dependency/route/cost features except through its tie-breaking. Once all route obligations have been exercised, their remaining marginal scores are zero. Actual rejected prefixes may leave coverage unachieved, so route coverage saturation must not be assumed from selection alone.

This limits the interpretation of a future comparison on these pools: it could measure route-diversification behavior, but it could not demonstrate payload-aware prioritization or general dependency-selection superiority. No empirical detection advantage or disadvantage has been measured by this audit. It does not justify enriching the pool using observed failing cases.

Any new selector study would need an outcome-independent task frame with genuine dependency and route diversity, plus a clear mechanism by which the proposed ranking differs from a competent generic coverage policy. Manually constructing such diversity to favor the proposed strategy would not solve selection bias. The original closed experiments remain unchanged.

Reconstruct: python3 scripts/extension/audit_selector_pool_structure_v1.py --verify. Inputs and selector implementation hashes: manifests/selector-pool-structure-v1.json.
