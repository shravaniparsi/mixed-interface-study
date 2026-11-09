# Live paired database capture verified

Hosted diagnostic [42651908419](https://github.com/shravaniparsi/mixed-interface-study/actions/runs/42651908419) executed source `c38b59bf1058d8af63333ebcfcc244f36df6c121` after unit run 42651696865 passed 678 tests. Four previously exposed cases ran once in each registered consumer branch, with independent SQLite resets. Local reconstruction of the downloaded artifacts matches the hosted verification. Twenty branch-local backups are retained.

| Case | Producer HTTP response in both branches | Immediate database observation | Continuation |
| --- | --- | --- | --- |
| Valid bio control | 200 | Requested bio stored | API and native UI edits passed the registered checks; post-continuation backups retained |
| Null username | 422 | Selected state unchanged | Neither continuation executed |
| 60-character username | 200 | Requested username stored | API and native UI edits passed the registered checks; post-continuation backups retained |
| 61-character username | 500 | Requested username stored | Neither continuation executed; semantic evidence remains incomplete |

The immediate database backups belong to the same branches as the captured producer responses and precede their diagnostic API readbacks. In the 61-character case, current-user and three article-detail reads returned 500 in both branches. The stored username observation therefore no longer relies on attaching a separately executed mechanism diagnostic to these new traces. The previously archived executions remain unchanged.

For the bio and 60-character cases, native UI qualification includes fresh authentication, bound settings fields, captured form submission, response drainage, and a database backup before shared diagnostic reads. Native requests triggered by the save can precede that final backup and remain captured. All registered API/UI continuation checks passed in these two pairs. Before-prefix and after-prefix database projections matched across the two independently restored branches in every pair.

The bounded diagnostic completed its declared measurements. Its semantic terminal sequence is clean observation, matched rejection, unresolved policy, and missing evidence. The last label is retained because database capture does not supply an unexecuted continuation or readable semantic API state. The 61-character failure is shared by the common API producer; it is not evidence of a channel-exclusive discrepancy. Username length policies remain unresolved.

These are four engineering pairs, not four new independent primary samples. No within-branch restart was tested in this run, and the isolated diagnostic's restart result must remain attributed to that separate execution. Projection equality covers the declared user/article fields. Backup subprocess time is included in instrumented branch costs and cannot be compared directly with version 6 timings.

The full archive, source certificate, request traces, backend logs, twenty SQLite backups, bootstrap/dependency/browser evidence and derived measurements are hashed in `manifests/realworld-paired-database-integration.json`. The archive verifier reopens the databases and reconstructs both measurement and terminal records in CI. Next review the identity/corpus bindings against these results, retain unresolved semantics, and finalize the remaining primary batch and common cost requirements. P2–P5 remain open.
