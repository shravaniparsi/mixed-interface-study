# SeatSurfing second and final ordinary qualification attempt

Attempt 1 (run 44347763330, study commit
617cbb27b5d8cb389f8fc382216815a05f07c386) failed before application build or
startup. Its archive authenticated successfully. The source revision, all
recursive tree entries and all 56 retained source blobs passed comparison.
The next assertion incorrectly treated the retained tree-response locator,
which equals the commit identifier, as the root-tree object identifier.

Attempt 2 corrects only this identity check. The corrected builder reconstructs
the Git root-tree hash from the frozen recursive entries, verifies every nested
tree against its recorded object identifier, and compares the reconstructed root
with HEAD^{tree}. The response locator is recorded separately. No metadata,
application source, selection, payload, schema, baseline, state-comparison rule,
image pin, build recipe, dependency version or deadline is changed.

The corrected builder and parent have new v2 paths. The parent differs only in
selecting that builder and recording/requiring attempt 2. The workflow and
registration name this second attempt. Attempt 1 remains retained and counts
against the two-attempt ceiling despite failing before application startup.
The existing v1 ordinary cycle and all runtime components are unchanged.

Synthetic Git tests cover directory ordering, nested object identities, symlink
encoding, missing parent entries and tampered child identities. The complete
retained SeatSurfing recursive tree is internally consistent under this check.
These tests do not establish application runtime correctness.

Both frozen ordinary edit cycles remain mandatory, with no scientific cases in
this job. A successful run still requires retained-evidence audit. Any failure
closes SeatSurfing qualification within this cohort: no third attempt, alternate
workflow, deadline extension or outcome-driven rerun is authorized.
