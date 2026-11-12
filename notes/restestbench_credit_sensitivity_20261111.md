# Six unsupported credits have limited ranking sensitivity

The post-hoc analysis covers all 180 released zero-shot, valid-generation rows: ten models, three services, two description modes and three repetitions. Scores are exact rational score/max_score values, averaged equally across repetitions within service and description mode. This is our defined sensitivity aggregation, not an assertion about the paper's plotting implementation.

Six model/service/description aggregate cells have uncertain credit. Each affected cell has a range of 1.5152 percentage points when the unsupported credit is removed versus retained, with original denominators held fixed. Among all 270 model-pair comparisons, 264 retain a certified strict ordering and four remain exact point ties. Two intervals touch only at an endpoint:

| TodoApp, vague descriptions | Credit bounds, three-run mean | Consequence |
|---|---|---|
| Sonnet 4.5 vs GPT-5 Mini | Sonnet 84.8485–86.3636%; GPT-5 Mini 84.8485% | Sonnet's reported strict advantage can become a tie |
| Kimi vs Mistral Mid | Kimi 60.6061–62.1212%; Mistral Mid 59.0909–60.6061% | Kimi's reported strict advantage can become a tie |

Neither pair can strictly reverse under these bounds; their intervals only meet at equality. No actual ranking reversal or change to the paper's conclusions is established. These findings weaken, rather than strengthen, a claim that the six identified credits substantially destabilize model ranking.

The bounds do not impute the missing test executions, are not confidence intervals, and do not certify all other benchmark records. Changing mutant eligibility or denominators would be a different analysis. This screen is restricted to the confirmed failed-application credits and all zero-shot valid-generation rows, with the scope fixed in `protocol/restestbench-credit-sensitivity-v1.md` before this calculation. Inputs were previously exposed, so the analysis remains explicitly post-hoc.

Reconstruct with `python3 scripts/extension/build_restestbench_credit_sensitivity_v1.py --verify`. All selected rows, aggregate cells and overlapping pairs are retained in `manifests/restestbench-credit-sensitivity-v1.json`. No new application execution or model call was needed. This is supporting evidence about measurement quality, not a sufficient Q1 contribution by itself.
