# Iris component calibration v1

Registered 2026-11-11 before execution. This is a second, outcome-exposed historical calibration, not an independent-input cohort, prevalence study, new-defect discovery or test of model behavior. Admission follows the already-inspected public issue 314 and fixing commit; this selection bias is explicit.

## Purpose and advancement criterion

Tiller established a shared-backend failure reachable through both channels. Iris tests a different causal question: can either an adapter repair or a backend repair independently prevent an unintended write, while preserving intended clears? A four-cell component intervention supplies attribution that a simple old/new version comparison cannot supply. Component interventions and state-frame checks are established experimental techniques, not claimed methodological novelty.

Upstream: https://github.com/cgbarlow/iris/issues/314. Historical commit a02a45480b8f801f5d5eab8c3da19d131cd3ed7c; fixing commit ebba6c1036e86cac407c2614e41c2039ac56c8f7. Freeze four cells: old/old, old/fixed adapter, fixed backend/old adapter, fixed/fixed. Every cell starts from the historical checkout. The adapter intervention copies only mcp/src/iris_mcp/tools.py from the fixing commit. The backend intervention copies backend/app/sets/models.py, router.py and service.py. Other production source stays historical. Hybrid cells are experimental combinations, not released versions.

## Cases, channels and fixtures

Three cases in each cell, with a fresh SQLite database and actual API-created actor/resources for each channel:

1. Grouped set: change description from `Original description` to `Edited description`, preserving collection membership.
2. Ungrouped set control: the same description edit, preserving NULL membership.
3. Intentional clear: grouped set moved to no collection with explicit collection_id=null, preserving description and all unrelated set fields.

Two channels: public Iris MCP-tool dispatcher with its real IrisClient; and complete-field direct API PUT, constructed from the pre-edit API object and SetUpdate schema fields. The latter provides an explicit preservation-capable control, not an ordinary minimal PUT and not a browser emulation. No claim of frontend execution.

Twenty-four executions total: four cells × three cases × two channels. One reported mechanism, not twenty-four independent defects. The MCP path invokes the actual dispatcher but does not exercise MCP SDK session/wire transport. Both paths use real FastAPI routes via public ASGI transport, real authentication and SQLite. No mocked API responses, production data, LLM calls, external messages or third-party service calls. The actor is a synthetic local administrator, so this is not nonadministrator coverage.

Before/after capture: complete sets table row, API object, and collection-filtered set membership. Record business HTTP requests/responses without Authorization headers or authentication payloads. Schema validation uses each tool's advertised inputSchema; direct API requests use the actual SetUpdate model schema. Plain success, requested postcondition and full-row frame are separate baselines. Description-edit write set is {description}; deliberate move write set is {collection_id}. updated_at is an explicitly allowed derived change, established from the pre-inspected service. All other changed columns remain alerts. Unconditional preservation of collection_id is a deliberately naive comparison that should flag an intended clear; the intent-aware frame must not.

For cross-reset comparisons only, map generated set, collection and actor identifiers to their fixture roles and remove created_at/updated_at. Raw values remain retained, and within-execution frame comparisons use them. Never normalize membership NULL into a collection identifier.

## Environment, limits and failures

One dependency-resolution job installs the pinned historical project's declared dependencies plus jsonschema 4.23.0 on Python 3.12.16/ubuntu-24.04. It freezes exact third-party versions before application execution and passes the same lock to all four cells. Local application packages are excluded from that lock; their imports resolve from the selected source tree. This is same-run dependency freezing, not a claim that all transitive versions were known at protocol registration. Retain pip outputs, lock and runtime/source hashes. No dependency changes between cells.

Environment job maximum 10 minutes; four execution jobs maximum 12 minutes each, max-parallel 3. Each application observer has an eight-minute deadline. At most one independently explained instrumentation correction dispatch is allowed, with all prior failures retained. No outcome-driven case substitution, write-set relaxation or extra repetitions. A second infrastructure/instrument failure stops the calibration for review. Explicitly retain partial observations and unexecuted cases.

## Interpretation and next decision

Predeclared expectation from the published fix: old/old MCP description edit on a grouped set loses membership; either component repair prevents it; direct complete-field controls and explicit-clear controls work in all cells. This is an expectation to test, not a result to force. Any discrepancy remains in the result.

Advance the corpus-feasibility gate only if all cells are observable, controls qualify, raw state and actual outgoing payloads establish the component effects, and the independent reconstruction reproduces the classifications. Passing adds one verified historical mechanism and a causal case; it does not establish Q1 readiness, novelty, unseen detector efficacy, or ecosystem frequency. The prior 44-pair independent-input study and 12-execution Tiller calibration remain separate.
