# RealWorld identity campaign: verified halt

The corrected hosted run [42581601478](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42581601478) executed source `7f5ab46e3122dbebaa840a30987ac35eda16642b`, after unit run 42581364666 passed 621 tests. All five initial pairs ran, with ten independently reset branches. The final pair triggered the registered evidence-completeness halt; the GitHub application workflow therefore failed. There were no followup jobs and no completed-campaign qualification.

| Case | Observed outcome |
| --- | --- |
| Ordinary bio control | Both continuations passed the registered checks. |
| Null username | Matched HTTP 422 responses, readable unchanged state, no continuation. |
| Empty username | Matched HTTP 422 responses, readable unchanged state, no continuation. |
| 60-character username | HTTP 200 and both continuations passed; acceptance policy remains unresolved. |
| 61-character username | Both prefix requests returned HTTP 500. Subsequent current-user and three fixture-article detail reads returned 500. Post-write state could not be projected; neither continuation ran. |

The retained backend logs report response-schema validation errors for usernames exceeding 60 characters, including the nested article author. This supports a diagnosis of response serialization failure. The traces establish post-write API unreadability; the archive does not contain a post-write database snapshot and therefore does not independently establish the exact stored database state or transaction boundary. This is a previously exposed engineering case, not a new primary-study discovery or an adjudicated defect count. A 500 response must not be interpreted as proof of an unchanged state.

The first run, 42580690627, stopped before any candidate write because the initial snapshot incorrectly expected article bodies in list responses. Its 56 retained files remain under `manifests/realworld-identity-setup-failure.json`. The corrected helper reads each pinned article detail and binds it to the corresponding list summary. The second attempt is retained separately, including all campaign logs and source snapshots (176 files). Neither attempt is overwritten, resumed, or pooled as independent statistical samples.

The halt-specific archive verifier reconstructs dispatch, sources, fixture/reset bindings, response-backed observations and the exact terminal sequence, then independently binds the incomplete case's diagnostic reads to captured responses. Verification of a halted ledger does not make it a completed campaign. The previously executed ordinary validator remains unchanged. Unit CI checks both retained attempts and rejects relabeling the halt as completed.

Next: design an isolated diagnostic replay that captures post-write database state and response serialization evidence for the 61-character case, without rewriting this campaign's classification. Then define the failed-write observation contract and review identity-specific coverage bindings. The current corpus map and primary P2-P5 gates remain open; no coverage promotion or untouched-boundary execution is claimed here.
