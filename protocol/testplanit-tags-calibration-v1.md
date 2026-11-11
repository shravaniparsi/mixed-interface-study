# TestPlanIt historical tag-write calibration v1

Registered 2026-11-11 before application dispatch. Final lead in the finite six-lead expansion. Issue 668 and its repair were inspected before design; this is outcome-exposed development evidence, not discovery or held-out accuracy.

## Source and execution boundary

Host and historical adapter: 294b646af84ca8a7543fa37366e0b84437cd5c4a. Adapter repair: 8b10df16fd4d6d629ed5c18882d9bbdc1a67a066. The only production file changed by the repair is packages/mcp-server/src/tools/cases/update.ts; the other changes are tests and a changeset. Run the historical host with each adapter in a separate observer process, replacing only that file. The shared lock blob is 49a753c7e410f6530742e891bf1e6f27139b045b. Install frozen dependencies, pnpm 11.25.0, Node 24 (record resolved patch), PostgreSQL 15 Alpine, Valkey 8 Alpine and Elasticsearch 9.0.3. Service image digests are recorded by Actions service logs. Root source license is AGPL-3.0-or-later under its dual-license notice; retain the notice and make instrumentation public.

Use the actual MCP SDK in-memory transport, registered production tool, production HTTP helpers, local Next development server, authenticated model and version routes, actual ZenStack ORM/policies/plugins and PostgreSQL. No browser, remote TestPlanIt instance, model calls, paid services, fake mutation handler or mocked ordering. In-memory MCP transport is not a network MCP measurement. Warm only read routes before scientific operations. Database snapshots use separate raw SQL reads, including complete case rows, tag joins and version rows. Never infer successful persistence from a tool message.

## Fixture and eight executions

Use a disposable database named tpi_test, upstream migrations/triggers/seed, a seeded admin with API access explicitly enabled and a local generated full-write token. Select the lowest-ID live seeded case only to obtain valid foreign-key IDs. Every execution creates a new synthetic case with tag A, version 1, an original name and no steps or custom-field values. Create distinct synthetic tags A and B. No reporter identifiers are reused.

Each adapter executes four cases once: (1) replace A with B; (2) omit tags and edit name; (3) explicitly clear tags with []; (4) request the same tag A. The desired tag sets are respectively B, A, empty and A. The omission control must preserve tags; clearing is intentional. Each operation should increment currentVersion once and produce a matching version snapshot through the actual host endpoint. Other case fields should remain unchanged except the requested name, version increment and documented database-maintained fields. Capture whole rows so unexpected changes remain visible; do not erase them by projection.

Baselines: advertised tool input schema; operation success; requested postcondition; manually specified preservation/cascade contract. For replace/same/clear, the requested-state baseline checks persisted tag IDs, not the response alone. For omit, it checks the requested name and the frame separately checks tag preservation. Version rows are a separate downstream agreement check. A naive preserve-all tag rule would incorrectly reject a legitimate clear and replacement; no automated-method efficacy is claimed.

Expected historical behavior from the report: newly requested tags can disappear when nested creates precede blanket deletion. Same-set writes could also encounter uniqueness constraints; retain any such result without relabeling it as the reported loss. Fixed behavior is a hypothesis to test, never a success assertion. A failed control or route/setup/authentication error is qualification evidence, not a confirmed defect execution. Record partial observations if the attempt stops. Do not count eight variants as eight independent defects.

## Limits and analysis

One initial job, at most one instrument correction, each at most 15 minutes; shared expansion ceiling remains 100 elapsed application-job minutes (6.5833333333 already consumed). Setup step limits preserve time for failure artifacts. A correction may repair fixture/runtime compatibility only; it may not alter requests, remove controls or weaken state checks. No reruns for significance. If the host cannot qualify within the allowance, retain an infrastructure exclusion. After this lead, close the finite expansion and assess benchmark utility against competent baselines and prior corpora. A reproduction alone cannot establish Q1 readiness.

Sources: https://github.com/TestPlanIt/testplanit/issues/668 ; https://github.com/TestPlanIt/testplanit/commit/8b10df16fd4d6d629ed5c18882d9bbdc1a67a066 . Upstream DB integration and E2E workflows at the historical pin supplied the real-service setup; their configured 30/45-minute limits are longer than this study's allowance, so feasibility is uncertain.
