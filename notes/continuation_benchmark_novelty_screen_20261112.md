# Novelty screen before any benchmark extension

This is a preliminary source-scope screen from primary abstract/project pages, not a systematic literature review, full-paper verification or a claim that any paper covers every continuation mechanism. No benchmark task/evaluator outcomes were inspected for selection.

| Source inspected | Scope directly stated by the source | Consequence for our next study |
| --- | --- | --- |
| Beyond Browsing: API-Based Web Agents, author project page | API-only, browser-only and hybrid approaches evaluated on WebArena | Moving an API/browser comparison to WebArena is not a new contribution by itself. |
| AgentRewardBench, arXiv 2504.08942v2, abstract | Expert trajectory assessments include task success, side effects and repetition; evaluates automatic judges | Do not claim web-agent side effects have generally been ignored or that evaluator auditing is new. |
| ST-WebAgentBench, arXiv 2410.06703v7, abstract | Task completion is evaluated jointly with explicit policies through Completion Under Policy and Risk Ratio | Adding ordinary constraints to task-success scoring is not sufficient differentiation. |
| Task Success Is Not Enough / SABench, arXiv 2610.34167v1, abstract | Goal satisfaction and authorization compliance are checked using deterministic trace oracles on email, calendar and ticket tasks | A generic goal-plus-side-effect oracle or collateral-damage benchmark claim is occupied. |
| When Agent Evaluation Becomes Unreliable, arXiv 2610.16067v2, abstract | Oracle state-integrity invariants and known-answer controls are evaluated, including an observed reward-function state reset and a reported transfer limitation | Generic state-integrity checks on benchmark evaluators are also established public prior work. |

Sources:
- https://yueqis.github.io/API-Based-Agent/
- https://arxiv.org/abs/2504.08942v2
- https://arxiv.org/abs/2410.06703v7
- https://arxiv.org/abs/2610.34167v1
- https://arxiv.org/abs/2610.16067v2

Abstracts establish the stated scopes, not reproducibility or empirical correctness. Venue comments on arXiv are author-supplied; acceptance and peer review were not independently verified here. No reported performance numbers from these papers are imported into our results.

Decision: no runtime benchmark expansion on the broad premise that task success misses side effects. The candidate narrower question is whether an API-created state prevents a later preserving native edit despite adequate shared-constraint and API-semantic baselines. That is the original continuation question; its distinctness from these papers and earlier GUI/API semantic testing still needs full-method verification. Absence of that exact phrase from an abstract does not establish a gap.

Before allocating new application runs, produce a claim-to-method comparison using full texts and determine whether the external tasks actually supply independently defined post-task edits. If they do not, their task counts cannot repair the original selection limitation. Neither the new frame nor the null results justify a Q1-readiness claim.
