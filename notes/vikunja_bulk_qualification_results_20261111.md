# Vikunja bulk calibration: authorization qualification failed

The two registered attempts did not produce scientific bulk-update evidence. The completed observation workflow is green because it retained all responses, including rejected operations. The independent reconstruction correctly refused to classify the bulk cases as qualified.

Initial run [43086390320](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43086390320) failed both jobs at Go package setup because frontend/dist was absent. No test body ran. The single allowed correction added a marked static placeholder for the unused frontend bundle.

Corrected run [43086867599](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/43086867599), study commit a064e22ad6f46109848766039fd3b0a5e8600528, completed 24 observations. The upstream synthetic token selected by the study supports single-task updates but not the bulk action. All 20 bulk attempts were authorization-denied: REST returned 401, MCP reported that tasks_bulk_update was unauthorized and omitted it from action discovery. Independent database snapshots verify unchanged target state on those denials. They are not clean preservation results and cannot evaluate the reported defect or repair.

All four single-task controls succeeded, changed priority to 3 and retained the assignee/reminder/favorite rows. Those controls verify a narrower path only; they do not qualify the bulk workflow. The failure is in the study's fixture authorization choice, not evidence that Vikunja lacks the reported bug.

The registered correction allowance is exhausted. No further Vikunja attempt is dispatched in this finite expansion, and no replacement project is added. A separately justified future experiment could use an appropriately scoped fixture, but it would not be a continuation of this frozen calibration.

[Exclusion reconstruction](../manifests/vikunja-bulk-exclusion-v1.json) retains both attempts, zero scientific bulk executions and zero new confirmed mechanisms. [Accounting](../manifests/vikunja-bulk-cost-v1.json) includes all four jobs. No paid model calls occurred. The historical corpus still contains only the two qualified Tiller and Iris mechanisms.

The next finite lead is Fast Dash. Its cascade contract and cross-call state observability must be admitted before runtime registration; the final lead is TestPlanIt. Neither has been run by this study.
