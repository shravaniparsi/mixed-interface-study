# RealWorld v8 exposed diagnostic: retained halt

Hosted run 42702655033 used source commit 8bb1351bb7d42d748f7c72fe015f691c11b93233 after full unit run 42702497159 passed. It stopped under the registered policy after four jobs and eight independently reset branches. Hosted and local reconstruction both verified the halt. The archive contains 175 files, including raw traces, branch logs, copied sources, runtime/bootstrap records and dispatch checkpoints.

| Job | Observed result |
| --- | --- |
| Article-create reference | Both branches returned 201 and completed their continuations; clean observation. |
| Unique article-update reference | Both branches returned 200 and completed their continuations; clean observation. |
| Title length 150 | Both branches returned 201 and completed their continuations; policy remains unresolved. |
| Title length 151 | Both API producers returned 500, follow-up reads returned 500, neither continuation ran, and the post-failure observable-state snapshot was unreadable. The pair is missing evidence and halts the sweep. |

The branch reducer retains the HTTP failures as observations. The rejection-completeness layer assigns `missing_evidence` because it cannot establish readable post-failure state. This is not evidence of rollback, database persistence or a native-UI-specific discrepancy. No database snapshots were collected in this version. Title policies remain unknown.

The whitespace-title pair, two duplicate-update pairs and two native-only controls were not started. Their prepared adapters and synthetic tests remain available, but this run does not qualify their live paths. The failed execution step and successful verification step are consistent: verification certifies the recorded stop, not completion of all nine jobs. No retries, resumed jobs, replacements or primary samples were added.

Next: investigate the 151-character producer/readback failure with a separately versioned, bounded diagnostic on this exposed input. Preserve this archive and its terminal outcome. Any later execution of unstarted v8 cases requires a fresh explicit plan; it must not be presented as resuming or completing this attempt. P2–P5 remain open.
