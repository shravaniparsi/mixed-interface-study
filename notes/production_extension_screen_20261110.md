# Production extension deployment screen

The fixed six-subject first screen ran as GitHub Actions 42874085809 at source 9262a9c2462579400dd63548c6a59573004c7166, after source CI 42873741785 passed. All six attempts were retained and all task-owned containers/networks were cleaned up. Three subjects reached HTTP: linkding, Memos, and Gitea. Three had engineering setup failures. No scientific boundary case executed.

The three second attempts are registered in `manifests/production-extension-screen-v2.json` and are the remaining attempts allowed by the two-attempt screening limit:

- Grocy: `version-4.7.1` was not a published image tag. Public registry metadata identifies `version-v4.7.1`; the second attempt uses the immutable digest corresponding to that release. The tag response is retained in `manifests/grocy-image-resolution-v1.json`.
- Vikunja: its uid 1000 could not create the default `/app/vikunja/files` directory. The pinned source declares `files.basepath`; the second configuration points that option at an ephemeral writable directory. Image revision metadata matches the registered source commit.
- Paperless: startup rejected a missing/default secret key. The second screen generates a process-only key and redacts it from command logs, inspection output, and retained response text. The application and broker images are pinned to the digests from the first attempt. Application revision metadata matches the registered source commit.

These corrections do not change application code or select subjects based on boundary results. First-attempt artifacts remain immutable. Second-attempt success, if observed, establishes only HTTP reachability, not a qualified native/API workflow.

Linkding ordinary controls are separately registered for bookmarks and bundles, twice each with API/UI order alternated, using the resolved image digest. Every branch starts a fresh container and creates a transient ordinary actor. Authentication output is not retained. API and native branches perform the same declared edit, preserve unrelated fields, and compare post-prefix and final business state. These are engineering controls, not additional independent samples. The control workflow is 42876144558 at source bf4a60337d48a229303d83b5f052b122e716039b, following successful source CI 42875673588.

A proposed push containing fixed synthetic passwords was rejected by automatic approval review before execution. The published screening registry contains no account passwords; the first screen does not provision accounts. Later controls generate transient credentials at runtime and exclude them from retained artifacts.
