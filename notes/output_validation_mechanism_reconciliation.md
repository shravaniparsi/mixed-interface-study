# Reconciliation of output-validation observations

The username-61 and article-title-151 diagnostics are two observed operations in the same pinned backend, grouped provisionally under one mechanism: a database write completes before output-schema validation fails. They are not counted as two independent defects or independent samples.

| Observation | Evidence | Database and restart result | Readback reach |
| --- | --- | --- | --- |
| Username update, length 61 | `manifests/realworld-identity-database-integration.json` | Requested username committed despite HTTP 500 and remained after restart | Current-user and three article-detail probes returned 500 |
| Article creation, title length 151 | `manifests/realworld-article-database-integration.json` | Requested article inserted despite HTTP 500 and remained after restart | Both article lists and the new detail returned 500; current-user and three existing article details remained readable |

The executed source locations differ: account update saves before constructing its output schema, while article creation exits its atomic block before constructing the article output schema. Both failures surface model-derived output length constraints absent from the corresponding request schema. These source and state observations support a shared mechanism family; they do not establish a single shared faulty function or the number of independently actionable fixes.

The observational scope remains the pinned SQLite deployment, synthetic actor and selected state/readbacks. Neither isolated diagnostic executed a native UI continuation. The paired identity and article campaigns retain their original incomplete outcomes, and no API/UI-exclusive detection credit is added from these separate backups. Unknown requirement policies remain unknown. Repeated observations, branch resets and same-backend variants must not inflate sample size or defect counts.

No additional immediate replication of these diagnostics is required for engineering readiness. Proceed to the fresh exposed-case v9 qualification, then reconcile corpus bindings and the outstanding batching, timing and freeze gates. Distinct-defect adjudication belongs to the later evidence review and must include shared-cause assessment and prior-report checks.
