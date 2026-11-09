# Paired identity measurement loader, version 2

Status: offline integration with the source-qualified version 6 paired archive. This loader adds measurement sidecars; it does not replace the frozen terminal classifier or authorize a new campaign.

## Evidence boundary

`realworld_identity_measurement_loader_v2.py` first invokes the existing identity loader, which verifies the registered job and selection, pinned application revisions, captured adapter sources, branch order, fixture references, timing and process evidence. It then requires each branch's successful runtime, confirmed backend cleanup and exact fixture reset hash before constructing a measurement sidecar. Source and archive inventories remain governed by the existing halted-archive verifier. The new replay checks that every legacy result equals the original stored result.

The sidecar extractor independently binds the actor, login, baseline user, complete pre-write fixture projection, producer command and response to the trace. Direct request/response ordering must be complete. The immediate readback plan contains nine probes: current user, author-filtered article list, tags, and detail/comments for each of the three fixture articles. Every response must match its captured request, path, position, status and body. Missing, duplicate or reordered probes fail measurement qualification. Failed producer responses cannot be followed by a continuation or an unregistered write.

A qualified sidecar means that these specific measurements have trace support. It does not mean that the legacy branch has complete semantic evidence, a resolved requirement or a successful continuation. A paired terminal marked missing evidence stays missing evidence even when its HTTP observations qualify. Shared producer/readback errors do not establish a channel discrepancy.

## Persistence and continuation

No paired version 6 branch captured an independent committed-state snapshot. All three database snapshot slots are therefore not planned, and persistence/change/restart comparisons remain unknown. API response bodies, readback status codes and the separately executed database diagnostic cannot fill those slots. A future database-enabled runner must capture snapshots for the exact job and branch, before readbacks, with its own versioned evidence contract.

For producer failures, continuation is explicitly not executed. For a fully reconstructed successful-prefix branch, the continuation interface and independently reconstructed checks are retained. If the legacy extractor cannot qualify that continuation, its state remains unqualified. An API continuation is never labelled a native UI continuation. Unknown username policy is copied unchanged from the registered specification.

The new output contains the full legacy result and a separate measurements mapping. It has `dispatch_authorized: false` and is not accepted as a terminal record by the campaign driver. This prevents an offline interpretation from resuming or replacing the halted campaign.

## Qualification and next step

Synthetic negative fixtures test unreadable post-write snapshots, missing/reordered probes, changed actor or command, unregistered writes, unfinished capture, false continuation claims, fixture substitution, and attempts to infer database persistence from an unbound raw field. The retained-archive replay verifies five pairs and ten branches and checks unchanged legacy classifications. CI retains the derived JSON alongside its source-qualified archive checks.

The next integration step is a versioned runner contract for branch-local database capture and its temporal ordering relative to API and UI actions. Qualify that runner on already exposed controls before dispatching any fresh paired campaign. Review the remaining identity/corpus bindings and P2–P5 readiness gates separately. This offline work adds no application executions or primary samples.
