# Terminal contract implementation progress

The common version 2 terminal policy, repeat planner and sequential driver are implemented. One decision function now controls continue/repeat/halt behavior. Completed mismatches trigger two candidate repeats with reference controls; partial application response observations remain unresolved; missing evidence and runtime failures halt. The version 1 source-pinned paths and their archived evidence are unchanged.

Sixteen targeted tests passed locally, including a bounded six-subprocess synthetic campaign with three nonzero exits. These tests establish contract and dispatch behavior, not application extraction or research findings. The normal hosted unit workflow discovers the new tests automatically.

P1 is partially implemented and remains open. The next change is a versioned Quartz runner and source-qualified negative-outcome bridge. Inspection found an additional required change below the campaign wrapper: `run_quartz_pair_job.mjs` rewrites the adapter's nonzero application-read failure to `child_exit_error`, then stops the pair. The bridge cannot recover an unexecuted second branch by changing only the campaign driver's policy. New runner behavior needs source-shaped negative fixtures and an ordinary-control integration check. No primary boundary cases were executed for this implementation.

P2 (full corpus bindings), P3 (immutable bounded batches), P4 (timing scope), and P5 (final enforced freeze) remain open. This work does not change the registered corpus, observed defect count, independent sample size, or publication-readiness assessment.
