# Generated mutation runtime qualification

Source commit `9cc573fbb1372b37068b3e905bc38e30f4dcdfc9` passed unit workflow 42760772921. Application workflow 42761024624 dispatched the fixed eight pairs once, producing sixteen independently reset branches. The execution step exited nonzero at the final registered missing-evidence halt; independent hosted reconstruction passed. Local reconstruction of the downloaded artifact also passed. All 281 artifact files are preserved byte-for-byte in `results/realworld-generated-mutations-ci-20261110`, including seventeen SQLite fixture/reset files.

| Pair | Input | Retained result |
| --- | --- | --- |
| generated-001 | API-producer reference | Clean observation |
| generated-002 | Empty body | Matched rejection, HTTP 422 |
| generated-003 | Null body | Matched rejection, HTTP 422 |
| generated-004 | Omitted body | Matched rejection, HTTP 422 |
| generated-005 | Whitespace body | Clean observation |
| generated-006 | Omitted tags | Clean observation |
| generated-007 | Title length 150 | Accepted; unresolved policy |
| generated-008 | Title length 151 | HTTP 500; unreadable rejection follow-up; missing-evidence halt |

Both branches use API creation; their assigned continuation channel differs. Rejected prefixes never reach that continuation, so matched rejection is not a comparison of two exercised continuation interfaces. Accepted whitespace-body and omitted-tags cases complete both API and native UI continuations. This qualification found no channel-exclusive mismatch. The final title case cannot establish write atomicity from HTTP status; the separate retained database diagnostic supplies its own evidence and is not backfilled into these branch records.

All eight planned jobs were attempted, but the campaign status remains `halted_terminal_outcome`, not completed. There was no retry, resume or extra attempt. Cleanup, independent reset hashes, raw hashes, source bytes, branch intervals and terminal decisions were reconstructed. Recorded timings are single-attempt engineering measurements, not comparative performance estimates.

This closes the bounded exposed generated-mutation runtime qualification. It adds no primary sample, stable defect count or independently adjudicated mechanism. The primary freeze remains open. Next reconcile this source-qualified evidence into the readiness map, then address remaining prospective campaign bindings and cost calibration before any untouched primary boundary runs.
