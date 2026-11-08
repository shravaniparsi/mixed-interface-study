# Boundary repeat policy preparation

The [policy](../protocol/boundary-repeat-policy-v1.md) now has a pure executable planner and deterministic [Quartz schedule](../results/quartz-repeat-policy-20261108/analysis.json). It binds the two ordinary controls to the matching workflow and producer interface before outcomes exist. The initial schedule contains 22 pairs and 44 independently reset branch slots.

A flagged pair receives two more candidate attempts, each followed by its reference control. Missing outcomes, unconfirmed cleanup, altered schedules, variable observations and failed controls remain explicit. All three candidate attempts are retained; no preferred attempt replaces a failure. Nineteen unit tests cover these rules, including mixed-prefix outcomes that remain unresolved even when repeated consistently.

All scenario outcomes in this report are synthetic. No application ran, and the forty Quartz mutation branches remain unexecuted. This implements scheduling and accounting, not boundary-capable execution. The next integration must translate source-qualified negative observations into the planner contract and enforce its stop/reset/evidence rules in the actual launcher before primary freeze.
