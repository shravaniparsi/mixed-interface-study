# SeatSurfing ordinary parent component

This component does not authorize execution. No SeatSurfing application job has
been dispatched. A published registration and hosted workflow remain required.

The parent builds once, then runs two fresh fixtures in frozen order:
announcement = "Edit notice", description = "Edit description". Each cycle
runs the unchanged original request schema on the ordinary payload, compares
native and API creation, captures the original warm checkpoint, and executes
warm native, restored native, and independently loaded API continuations.
Actor, complete database state, writes, observed headers and rate budgets must
pass the existing coordinator gates. A failure ends the sequence without retry.

Build and both cycles share 1,380 seconds. Cleanup has an absolute boundary at
1,560 seconds from parent start; the hosted job must have a hard 30-minute
limit, leaving four minutes for evidence encryption and artifact upload. A
cycle failure stops its process group before parent cleanup. No runtime image
or dependency installation is permitted locally.

Inventory snapshots bracket all ten coordinator stages on the dedicated
runner. Unknown study-labelled resources, foreign ownership of fixed names,
and unknown direct or transitive clients in the isolated database namespace
fail inventory. These are boundary observations, not continuous monitoring.
Cleanup operates on inspected owned IDs and the labelled database volume;
container configurations and logs stay inside private evidence. Paused writers
are resumed only to terminate them during teardown, after comparisons end.

The final public summary contains status and ciphertext hash, not credentials,
raw logs or container environment. Private evidence is sealed using the
existing public recipient certificate. Success remains pending retained-evidence
audit and is not a scientific case or a qualification claim by itself.

Local tests cover inventory ownership and namespace closure, fixed stage order,
fail-stop sequencing, original shared deadlines and descendant termination.
These synthetic tests do not establish application runtime correctness.
