# SeatSurfing ordinary fixture lifecycle component v1

This component prepares the prospective coordinator; it does not dispatch or qualify an application. The fixed application revision and source-build preparation remain unchanged. No additional runtime attempt or scientific case is authorized here.

The helper requires the study CI repository and a source-build report bound to the executing study commit. Before every transition it checks the application, database and browser container IDs, image identities, ownership labels, restart policies, isolated network namespace and actual running/paused states. Warm transitions also require unchanged positive process IDs and start timestamps, with zero restarts. The database remains running and unpaused.

After the owning coordinator observes browser network settlement, pause freezes the browser first and application second. The original checkpoint guard then rejects any active or unrecognized database connection. Network quiet does not establish database settlement. This helper does not itself prove completion of background application work; the bracketed full-state capture and ordinary warm comparison remain required.

Resume unpauses the same application process before the same browser process. To stop for restoration, the coordinator explicitly resumes first, closes the existing browser bridge so the worker retains its final network trace and exits, and stops the application with a ten-second grace period. Actual stopped states and absence of other database connections are checked before restoration can proceed. The retained containers are not removed or replaced by this helper.

Each Docker command has a twenty-second deadline. A partly executed or failed transition permanently invalidates the helper. There is no automatic rollback, repeat command, or reinterpretation of a failed transition as successful. The owner retains transition records and performs bounded cleanup of its labelled resources. These records include pre/post observations and action timestamps; they do not establish actor continuity, checkpoint integrity, request equality or scientific success.

Nine synthetic tests cover ordering, unchanged process/container identity, partial failure, active transactions, actual worker exit, stopped-state verification and CI commit binding. No Docker or application execution occurs in those tests. End-to-end integration, API production and transport comparison, ordinary coverage of both frozen edits, evidence sealing and a registered qualification workflow remain outstanding.
