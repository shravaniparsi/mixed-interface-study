# Pinned GitLab source inspection result

Run 43166622248 completed in 278 job seconds on frozen commit d8d84fcb24269f1d16ec0e522e7c1b4838a5bc03. The digest-pinned benchmark image was downloaded and a stopped, network-disabled container created solely for file copying. Its recorded state is created, PID zero, with no start timestamp. GitLab services and scientific cases were never started. There were zero model calls. This is infrastructure elapsed time, not a verified billing statement.

The bundled VERSION identifies GitLab 15.7.5 and REVISION identifies 358d690d91c. GITLAB_REVISION was absent; that extraction failure is preserved rather than replaced by a guess. The package version manifest and seven API documents were copied successfully: projects, issues, merge_requests, members, repository_files, commits and the API index. Their hashes are reconstructed from the retained artifacts. Disk availability after extraction was 59,438,645,248 bytes on that runner; the next job starts on a different disposable runner and must recheck before pulling.

The copied documentation is now the primary input-source candidate because it came from the same pinned image, rather than a current documentation website. Documentation can still differ from runtime behavior; no API contract has yet been empirically qualified.

Static capability anchors in the extracted files:
- projects.md line 1183: Create project.
- issues.md line 994: New issue; line 1147: Edit issue.
- merge_requests.md line 1263: Create MR.
- members.md line 511: Add a member to a group or project.
- repository_files.md line 226: Create new file in repository.
- commits.md line 81: Create a commit with multiple files and actions.

These support continuing source-contract construction for repository/README, issue assignment, merge-request reviewer and project-member candidate families. They do not prove native controls, benchmark fixtures, reset fidelity, preservation semantics or authorization equivalence. The directory/file family still needs evidence of a legitimate independently persistable producer; do not simulate a directory with an invented placeholder file. Reddit API identity remains unresolved in its separate screen.

The documentation search incidentally exposed source-document references to historical membership-role changes. No issue page or implementation body was opened, and the six-family selection remains unchanged. No source-valid input inventory is frozen yet; frontend validation and task evaluators remain uninspected. Next: derive the initial input inventory and complete API continuation projections from these version-matched API documents before native UI inspection, recording unsupported semantics rather than guessing them.
