# Article creation committed despite an HTTP 500 response

Hosted run 42704951705 completed three independently reset, exposed API-only cases using source commit e26c23486e7436eb1cb01f23974248f920db80bd after unit run 42704839709 passed. Hosted and local validators reopened thirteen SQLite backups and independently reconstructed the HTTP and selected-state measurements.

| Case | Creation HTTP | Requested new row observed | State survives restart | Readbacks before and after restart |
| --- | --- | --- | --- | --- |
| Ordinary article control | 201 | Yes | Yes | All seven probes return 200 |
| Title length 150 | 201 | Yes | Yes | All seven probes return 200 |
| Title length 151 | 500 | Yes | Yes | User and three fixture details return 200; both article lists and the new article detail return 500 |

For title-151, the independent immediate backup, taken after the response and before readback, contains four articles instead of three. The added row matches the requested title, description, body and owner. The same selected user/article state is present after shutdown and restart. The three fixture article rows and public user fields remain unchanged. Tag relations and unrelated database state are outside this comparison.

The executed backend source explains this result. In `apps/articles/api.py`, creation and tag assignment occur inside `transaction.atomic()` at lines 76–88, followed by output serialization at line 90 outside that block. `ArticleInCreateSchema` declares a nonempty string title without a maximum length, while `ArticleOutSchema` derives its title field from the model's 150-character field. Backend logs identify output-schema validation failures during creation and list serialization. Thus, for this pinned SQLite deployment, the creation request commits a row that subsequently fails output validation. This conclusion combines observed backups with the executed source; it is not inferred from HTTP status alone.

This is an exposed, single-attempt mechanistic diagnostic, not a defect prevalence estimate, UI-continuation result or primary sample. The title requirement policies remain unknown. The failure resembles the previously observed username output-validation problem; the two operations should be assessed as a possible shared failure mechanism before counting distinct defects. The v8 missing-evidence halt remains unchanged and its five unstarted jobs remain unexecuted.

Next: incorporate this evidence into the failure-mechanism inventory and prepare a fresh bounded plan for the remaining exposed legacy cases. Do not resume or retroactively complete v8. No further immediate repeats of this already verified diagnostic are required.
