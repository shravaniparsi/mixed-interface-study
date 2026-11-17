# ownCloud ordinary control closeout

Run 44052230460 at frozen head 1ce309f3d174f64ab4ddbf18d439dca0a2d4863b is terminal and closed. Job 133932638605 lasted 141 seconds; its matching GitHub timing record reports zero billable execution milliseconds. This is not a whole-project invoice. No paid research models ran.

All three fresh ownCloud/Collabora pairs reached readiness and cleaned up successfully, with six distinct container identifiers. API→API completed file creation, public read-only share creation and an unauthenticated download matching the 3,673-byte payload. Native→native stopped in production; API→native stopped in consumption. Both waited unsuccessfully for the job_description.md row. The registered scorer therefore rejects qualification. Scientific cases and confirmed defects remain zero.

## Archived evidence and interpretation

Both failure screenshots show the first-login welcome dialog still open. The captured HTML contains only 14 file rows, alphabetically ending at Example.odt, with no job_description.md row. The exposed pinned upstream filelist.js renders a viewport-dependent pageSize and appends rows through _nextPage on scroll. This supports an instrumentation limitation: waiting for a row alone does not navigate a lazily rendered listing. It does not prove the API-created file was absent from the underlying list response, which was not archived as a response body.

The native/native screenshot additionally says “Not enough free space, you are uploading 4 KB but only 0 B is left”. No upload request appears in the saved non-read wire trace. Its terminal HTML contains free_space=89809612800; the API/native HTML contains 89793417216. These later DOM values conflict with the earlier visible zero-space message. The evidence does not establish whether initialization timing, stale client state, fixture configuration or another cause produced that message. Do not label it a backend quota defect, validation bypass or confirmed race.

The API/native branch's producer GET returned exactly the registered hash and text/markdown;charset=UTF-8. It never reached the share dialog. The API/API branch passed all file/share assertions. The missing native comparator prevents incremental-detector or task-equivalence claims.

## Next design boundary

Do not rerun this schedule or alter its scorer. Keep its frozen payload, protocol and failed outcomes unchanged. Further engineering would first need a separately specified browser interaction contract covering first-login dismissal, initial upload readiness and list pagination, plus passive evidence sufficient to distinguish a ready UI from an incomplete one. Any later qualification would be a new, disclosed engineering stage; it would not retrospectively rescue this run or count as an independent natural-defect study. The project still lacks a demonstrated Q1 contribution.

Reconstruct with scripts/extension/verify_agentcompany_owncloud_controls_ci_v1.py --verify. Raw evidence is results/agentcompany-owncloud-ordinary-ci-44052230460 and the outcome is manifests/agentcompany-owncloud-ordinary-outcome-v1.json. Additional upstream instrumentation source is archived under results/agentcompany-owncloud-control-source-v1; those additional files were not included in the earlier three-file packaged-byte equivalence check.
