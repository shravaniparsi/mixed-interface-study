# Fast Dash: bounded related-report check

This source check follows the unexpected fixed-revision observation from run 43088065630. It adds no application executions and does not change the frozen eight-case experiment or its labels. Four issue bodies were read in full, following the previously recorded three targeted searches. This is not an exhaustive search or evidence that a defect is unreported.

| Report | Reported behavior | Relationship to our observation |
|---|---|---|
| [116](https://github.com/dkedar7/fast_dash/issues/116), 2026-06-28 | A dependent input's advertised default contains an internal object representation; its options are missing. | Object leakage is already reported. Our observation concerns the value passed to the callback after a parent mutation, not merely the advertised default. That distinction does not establish a new defect. |
| [204](https://github.com/dkedar7/fast_dash/issues/204), 2026-08-13 | Unselected dropdowns pass null at initial invocation; includes the README cascade example. | Related default handling, but initial load differs from our valid child followed by a parent change. |
| [246](https://github.com/dkedar7/fast_dash/issues/246), 2026-09-23 | Scalar dependency resolvers work in the browser but are absent from MCP state and invocation. | Same broad cross-surface contract problem. Our frozen callback uses a list/options resolver. |
| [279](https://github.com/dkedar7/fast_dash/issues/279), 2026-10-07 | A scalar resolver is seeded on load but remains stale after a parent change; follow-up to 246. | Incomplete repair validation is already an explicit concern in the tracker. The report separately claims the list/options path works in 0.7.2. We have not independently tested that release, and its report is not a measurement of our pinned historical repair. |

All four issues were closed at inspection. Closure does not prove a particular release passes our experiment. Their author reports are not our runtime evidence. Keep the result wording as an unexpected discrepancy at the pinned repair: describe/readback reports null, the state key is absent, and invocation uses the Python dependency-object default. Do not claim a newly discovered or current-release defect, a previously unstudied bug class, or novelty merely from using downstream invocation to validate a repair.

The reusable research question remains whether an executable corpus improves repair validation over competent existing tests, with explicit controls for intended clears and cascades. These reports make the novelty bar higher, not lower.
