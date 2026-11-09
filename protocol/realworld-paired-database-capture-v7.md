# Branch-local database capture for paired identity jobs, runner version 7

Status: implemented capture path with actual API-adapter/mock-HTTP/real-SQLite qualification. Live application, native-browser execution, a version 7 source-qualified paired loader and fresh hosted dispatch remain open. No new application evidence or primary samples are supplied by these fixtures.

## Scope and checkpoints

The runner keeps the exact previously exposed identity job selection and independent reset mechanism of version 6. It invokes the separate version 2 identity adapter with the active SQLite path, the backend Python executable and a fresh branch-specific output directory. The runner snapshots the adapter, capture helper and independent database reader sources alongside its existing source inventory. Frozen versions remain unchanged.

The adapter captures three checkpoints where applicable:

1. `before_prefix`: after the baseline API fixture checks and immediately before the producer request.
2. `after_prefix`: immediately after the producer response, regardless of its HTTP status, before diagnostic readbacks or launching the UI continuation.
3. `after_continuation`: after the assigned continuation returns, before shared diagnostic API reads. No continuation checkpoint is fabricated when the continuation did not execute.

For a UI continuation, the adapter drains and closes its captured browser context before taking the final checkpoint. Native browser requests triggered by the save may precede that checkpoint and remain in the trace. The checkpoint therefore precedes shared diagnostic API reads, not necessarily every browser-generated read. Browser qualification must verify this ordering with real captured traffic.

Each checkpoint invokes a separate Python process and the previously qualified independent read-only SQLite backup routine. The caller awaits completion before proceeding. Snapshot begin/end events bind the stage, file and SHA-256 to the branch trace. Output directories and backups cannot be reused or overwritten. A failed capture stops the adapter through its existing error path; partial evidence remains on disk. The runner retains each branch's raw trace, backups and backend logs.

Backups contain the synthetic fixture's full SQLite database, including synthetic credential material; projections exclude credentials. Projection scope remains the single fixture user's selected fields and three articles' identity, content and ownership. No restart persistence observation is added by this runner. Failure to observe a column or related table does not establish that it stayed unchanged.

## Independent verification

`validate_identity_database_capture_v2.py` reopens each retained backup, verifies bytes and projected fields, binds fixture identity/content, and checks the declared checkpoint inventory and trace ordering. It rejects changed sources, changed backup bytes, forged projections, missing checkpoints, trace events during a checkpoint, readbacks preceding producer capture, and incomplete UI response drainage. Its caller must separately qualify the exact job, source inventory, runtime, reset, request command and semantic trace. Passing this database validator alone does not qualify a full paired job.

The three API-adapter fixtures model accepted writes, validation rejection and a committed write with a failed response. They exercise the actual Node adapter and Python capture subprocess against a real SQLite fixture with mocked HTTP. The server-error fixture also retains unreadable API responses, so the frozen semantic extractor still reports missing evidence despite the new database observations. The UI ordering test is a source-shaped fixture, not a native-browser experiment.

## Dispatch and cost

The version 7 runner does not run a campaign by itself and no hosted workflow is enabled in this change. Before a fresh bounded run, implement the version 7 source-qualified loader, bind capture directories to exact branch identities, combine database measurements with the existing paired trace checks, and qualify the new runner on already exposed controls. Retain the original halted campaign and its classifications. Primary P2–P5 gates remain open.

Backup subprocess time is included within the adapter's existing timing phases and enclosing branch total. Do not add it again or directly compare these instrumented timings to version 6 costs. A common instrumented cost scope must be frozen before primary comparisons.
