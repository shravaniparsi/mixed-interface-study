# State-scope findings for the ordinary development workflow

The eight-file inspection frozen at bdb6c0c completed once: all eight original Git blobs verified and all 1,055 source lines were reviewed. No application request, runtime job, reserved-system source or scientific input was added. The collection manifest records exact identities, sizes and elapsed acquisition time. The two previously retained application configuration files were also checked against their published SHA-256 values.

## What must survive a comparison

UserService.createUser writes a relational user and search document, generates a password and reset key, records reset time, resolves authorities, and evicts login/email caches. These values and relationships extend beyond the earlier eight-field readback. Independent creation in two jobs is therefore not a full-state clone, even when IDs and projected fields happen to agree. Do not publish generated credential values as ordinary evidence; compare private state or hashes in isolated synthetic environments.

The admin PUT uses UserService.updateUser, which loads by ID, updates the user and authorities, saves to Elasticsearch and clears caches. The GET readback uses the cached relational lookup with an authorities entity graph; it is not an independent search-index check. UserResource calls asynchronous creation mail after user creation. The inspected mail service sends/logs mail and has no repository dependency; this bounds the visible method behavior but does not prove all library/template side effects absent. AsyncConfiguration enables both scheduling and async work without an explicit wait-for-completion shutdown setting in that file. Process termination alone must not be treated as proof that queued work completed.

UserService also schedules daily deletion of old, unactivated accounts with activation keys. The ordinary created user is activated, so it is outside that method's stated predicate. This does not license ignoring other rows or all scheduled work.

## Restart is an intervention

CacheConfiguration allocates heap caches and clears existing caches during customization. ElasticsearchIndexService handles context refresh; with the original reindex-on-startup=true setting, it deletes/recreates indexes and repopulates them from relational entities. The previously retained API-control log shows both reindex start and completion. Restart changes cache/search state and can normalize divergence. Comparing only restarted continuations could erase the phenomenon under investigation.

The original development configuration uses a file-backed H2 database. That makes a stopped relational checkpoint a candidate, but does not itself qualify consistent backup/restore. In particular, do not implement Elasticsearch checkpointing by copying its data directory, even after shutdown: the original-version vendor documentation explicitly excludes this method and requires its snapshot functionality. Snapshots also omit node configuration and transient settings and span a time interval rather than one precise instant. See [Elasticsearch 7.17 snapshot and restore](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshot-restore.html), accessed 2026-11-18. A quiescent writer interval and separate configuration capture are required for the proposed comparison.

## Implementation decision

Reject a simple stop/copy/restart harness as proof of unchanged continuation state. The next runtime qualification must distinguish preservation of persisted state from equivalence of the continuation itself. Use a supported Elasticsearch snapshot/restore procedure and a qualified relational checkpoint, retain complete relevant state evidence, and account for startup reindex and cold caches. Include an ordinary continuation without restart as a reference before treating restarted branches as representative. A failed equivalence check is an engineering failure, not evidence of a defect or a null scientific effect.

No validation rule is transferred from these newly exposed implementation files into a specification-only baseline. No altered-input cases are selected from their contents. A runtime registration remains required: exact checkpoint operations, full-state observations, browser/authentication handling, bounds and failure stops are not yet implemented. The public-source acquisition schedule is closed; it does not authorize recursive acquisition. The Q1 objective remains incomplete.
