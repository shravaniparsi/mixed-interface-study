# Fresh v9 legacy diagnostic verified

Run 42708069641 executed seven fresh jobs and twelve independently reset branches using source commit bd2f36c447bf95c1416335f3fa192b4a98fe174a after unit run 42707887979 passed. Hosted and local reconstruction verified the full bounded sweep. This run did not resume or complete the stopped v8 attempt.

| Case | Branch observations | Retained classification |
| --- | --- | --- |
| Article-create reference | Both producers returned 201; edits completed | Clean pair |
| Unique-update reference | Both producers returned 200; comments completed | Clean pair |
| Whitespace title | Both producers returned 201 with an empty slug; neither continuation ran | Incomparable pair; shared empty-reference observation |
| Duplicate partial update | Both producers returned 200; each returned reference gave 404; neither comment write ran | Incomparable pair; shared unresolved-reference observation |
| Duplicate full update | Both producers returned 200; each reference resolved and its comment completed | Individually clean branches; pair incomparable under current exact-reference gates |
| Native comment control | Native creation returned 201 and deletion returned 204 | Clean singleton; no paired contrast |
| Native profile control | Both native profile writes returned 200 | Clean singleton; no paired contrast |

The duplicate full-update branches generated different slug suffixes. The current pair reducer compares the literal prefix-state slug and the literal consumer-command path, so both gates fail despite successful branch-local bindings. This is an engineering normalization gap, not evidence that one interface detects a failure missed by the other. A separately versioned comparison can normalize generated references only after preserving each branch's source, actor, reset, command and local-reference integrity checks. The frozen v8/v9 classification and raw evidence must remain unchanged.

The whitespace and duplicate-partial cases also lack submitted consumer-write commands. Removing the generated-slug difference alone cannot establish those missing actions. Their recorded producer/reference failures remain distinct from successful continuation evidence and cannot be relabeled as clean or channel-exclusive outcomes. No automatic repeats were dispatched in this bounded engineering sweep.

Next: implement and adversarially test a versioned, branch-binding-aware generated-reference comparison, then replay the immutable v9 archive offline and reconcile corpus readiness. Preserve singleton accounting, unknown policies, earlier halted attempts and the provisional shared mechanism grouping. No primary samples or independent defect counts were added.
