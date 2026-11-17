# Frozen README execution results

Run 44033922143 at frozen head af384bda7491cfc02f40ffa9d2e56825081d2ed3 is terminal. Both workflow jobs concluded success, but scientific completion differs: repetition 1 stopped at a failed starting control; repetition 2 completed its 20 entries with passing starting and ending controls. The original scorer reconstructed the archive without source changes and its verification mode reproduced the manifest.

## Schedule and observed evidence

The schedule contained six specifications, two repetitions, 12 triples, 36 scientific branch entries and four ordinary controls. There are 18 scientific records, 15 scientific producer attempts, three observed controls and 21 distinct containers. Three reached native-description branches stopped before production as planned. The other 18 scientific entries and the first repetition's ending control were unreached. The schedule is therefore closed under its stopping rule but not fully executed. Unreached cases are neither successes nor defects.

The frozen classifications are six incomplete triples, two continuation-or-instrument failures, three native-input-not-representable triples and one lifecycle-control triple. There are zero candidate incremental signals and zero confirmed natural defects. There are no all-paths-preserve triples in this run. Those counts must not be presented as a zero defect rate over 12 valid comparisons.

## Raw-evidence interpretation

Repetition 1's ordinary native/native starting control received HTTP 201 for the Web IDE commit, but the immediate branch-list response was empty. The later read-only failure snapshot contained main, the exact README and one root commit. The control remains failed; its later snapshot does not retroactively qualify the batch.

In repetition 2, ordinary omission and explicit initialize_with_readme=false had matched producer projections. Their API/native branches passed, but API/API failed the immediate branch-list assertion in both. Native/native also failed that assertion for initialize_with_readme=false. Each later failure snapshot showed main. This is inconsistent with interpreting these cases as an API-created state that uniquely breaks native continuation. A readback timing or consistency explanation is plausible, but its internal cause was not established.

All five reached non-lifecycle API/native cases passed. API/API passed the explicit empty and Unicode description cases; the ASCII description case had the same immediate empty-branch-list assertion followed by main in the later snapshot. The three explicit-description native/native entries recorded zero description controls and NativeInputNotRepresentable before any producer write. Their API-arm observations remain descriptive, without a matched native producer.

The initialized-README lifecycle control had an existing README before continuation. API/API returned HTTP 400 with "A file with this name already exists". Both native paths displayed "The name \"README.md\" is already taken in this directory." Their subsequent editor assertion failed because no editor was opened. All three failure repository snapshots exactly matched their producer snapshots. This is an existing-file conflict detected by both interfaces, not an incremental validation defect; the API baseline receives credit.

## Compute and conclusion

The two job intervals were 418 and 896 seconds: 1,314 seconds or 21.9 job-minutes, below the registered 90-minute cap. Adding these unique jobs to the preceding archive-scoped compute snapshot gives 17 runs, 31 jobs and 16,089 seconds (268.15 minutes). This excludes other study stages, unit workflows, local work and unlisted runs; it is not a whole-project total or a billing invoice. This execution used no paid model calls.

The archive and classification support closing this registered schedule without reruns, replacements, normalization changes or repairs. They do not establish an incremental detector benefit or a Q1-ready contribution. Next is the complete selected-cohort accounting and contribution assessment, retaining failed controls, representability exclusions, contract closures and the earlier unresolved issue observation.

Sources: manifests/benchmark-gitlab-readme-results-v1.json; results/benchmark-gitlab-readme-inputs-v1-ci-44033922143/run.json and both repetition artifact directories; manifests/benchmark-archived-compute-v1.json. The frozen execution registration remains unchanged.
