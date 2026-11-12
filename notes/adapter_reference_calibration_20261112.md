# Reference backend calibration

The frozen synthetic source contract now has a real loopback HTTP implementation backed by SQLite. Its iterative update implementation is separate from the recursive input-inventory oracle. Every write is followed by an HTTP read and a separate SQLite connection reading the entire record set, including the unaffected sibling.

The 48 unchanged inputs passed. Three deliberate request transformations supplied sensitivity controls: removing null-valued members produced 14 state mismatches, removing falsy-valued members produced 30, and reversing arrays produced four. Each transformation was applied to all 48 inputs. These are 192 harness executions, not converter executions, natural defects, independent faults, or evidence of agent behavior.

The archive verifier reconstructs every reset/write/read triplet from 576 HTTP events, checks the recorded database snapshots against the frozen expected states, and checks the final SQLite file against the last snapshot. Intermediate SQLite snapshots were recorded by the calibrator; the archive cannot independently re-query historical database states. Type-sensitive JSON comparisons distinguish false from zero. All source and raw-file hashes are retained in the manifest.

The first local attempt failed before requests because the sandbox prohibited socket binding. The same unchanged scripts then succeeded with permission to bind loopback. Both attempts are preserved. No converter runs or paid model calls occurred. Local elapsed time was not instrumented as an experimental runtime measure.

After the input freeze, nine public documentation/package/license files were retrieved from the three frozen converter commits. Each downloaded file was checked against its Git blob hash. This establishes interface-source provenance, not converter correctness. Selection-time exposure statements remain historical and must not be interpreted as current blindness. Generated schemas and converter behavior have not yet been observed.

Next: freeze the public-interface bindings, dependency environments, execution schedule and classifications before converter comparisons. Preserve all 48 cases per converter, including unrepresentable or rejected inputs. Report the complete request comparator alongside state checks and do not present state checks as automatically adding detection power.
