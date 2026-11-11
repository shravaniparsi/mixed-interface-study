# Vikunja bulk-write calibration v1

Registered historical development experiment, not unseen evaluation. Source lead 4 of the bounded expansion; issue 4109 / merged PR 4166 were read before construction. Vikunja was used in earlier studies, so this is not a new unexposed project.

## Question and source

Does the explicit bulk update field list protect task relations and per-user favorite state, and do intentional clears remain possible after repair? The historical BulkTask.Fields description explicitly limits writes to named fields. This differs from Superset's ambiguous full-replacement wording.

Historical commit bbe3dbe0f7cf97e646f3001c380f59ef5c1cda0a is the parent of the first repair, fb115c37c06f66289fd644f2c618b27048b23037. Fixed ad018d4e16e8c82ed254376f49d097559524e649 includes the assignee, reminder, favorite and missing-field repairs plus regenerated API documentation. The PR's later base 7e991c4 is divergent and is not used as the historical parent. Both chosen versions have identical go.mod and go.sum blobs. Use Go 1.27.0 and readonly module resolution. No production source is changed.

## Executions

Six cases, two channels, two versions: 24 executions. Each starts with a fresh upstream fixture reset. Synthetic user 1 and the same upstream scoped test token are used in REST and MCP. Record all responses even when rejected; transport errors or fixture failure do not count as clean scientific outcomes.

| Case | Tasks | Operation |
|---|---|---|
| priority_relations | 1, 27, 30 | Bulk fields=[priority], values.priority=3 |
| priority_clean | 3 | Same operation, fixture has no tested relations/favorite |
| clear_assignees | 30 | Bulk fields=[assignees], values.assignees=[] |
| clear_reminders | 27 | Bulk fields=[reminders], values.reminders=[] |
| clear_favorite | 1 | Bulk fields=[is_favorite], values.is_favorite=false |
| single_priority | 30 | Single-task PATCH priority=3 / MCP tasks_update |

REST uses the actual Echo/Huma route, MCP uses initialized JSON-RPC HTTP requests to the real MCP endpoint, do_action/tasks_bulk_update or tasks_update. HTTP is in-process httptest; no browser, external network transport or LLM. The upstream environment uses real shared-memory SQLite and fakes event delivery. Accordingly notifications and asynchronous downstream effects are out of scope.

Before and after each operation, directly query complete target task rows, task_assignees, task_reminders and task favorites; separately GET the task via the real API. Capture the advertised action schema through find_action and relevant tools/list schemas. No authentication headers are archived.

## Baselines and qualification

Reconstruct input schema validity from captured schemas; do not infer it solely from HTTP success. Report operation success and requested postcondition separately from the state frame. A rejected old-version explicit clear is an unsupported-operation outcome, not a successful clear or state-loss alert.

The manually specified frame allows the named task field, or named relation/favorite change, plus task.updated. Reminder relation comparisons preserve semantic reminder values (task_id, reminder, relative_to, relative_period) while allowing row-id/created changes because production replacement can reinsert rows. Assignees preserve task/user memberships; favorites preserve entity/user/kind memberships. Retain full raw rows so these projections remain inspectable. Do not generalize to unobserved tables.

Expected historical pattern: unrelated relation/favorite loss on bulk priority, fixed preservation, and preserved assignees on the single-task control. This prediction is not enforced by the observer: unexpected scientific results are retained. Fixture qualification requires the specified nonempty relations and user-1 favorite before the operation; ordinary controls and API readbacks must qualify before a causal comparison. The three relation types, multiple tasks and two channels are correlated manifestations of this bulk-update repair family, not independently sampled defects.

## Stop and correction

One initial two-job workflow, 15 minutes per job; at most one separately versioned instrument correction under the parent expansion protocol. Register source hashes before dispatch. Preserve all attempts. No paid model calls. An observation timeout is not grounds to dispatch another run while the original remains active.
