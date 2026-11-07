# PetClinic interruption supervision

The CI wrapper previously used Python's default SIGTERM behavior. A timeout signal could terminate the wrapper without entering its `finally` block, leaving its separately launched processes without wrapper cleanup. SIGTERM and SIGINT now raise an exit exception so the cleanup block runs. Repeated stop signals are deferred while bounded cleanup runs.

The wrapper attempts runner and frontend cleanup independently and writes the cleanup report even if an attempt fails. The helper checks that a running child leads its own process group before signalling that group, waits five seconds after SIGTERM, then allows two seconds after SIGKILL. A process that has already exited is not signalled. Cleanup errors and unconfirmed direct-child exit make an otherwise successful wrapper fail. Source snapshots now include the supervision helper.

Nine tests cover graceful exit, a child ignoring SIGTERM, an already-exited child, refusal to signal a non-owned group, signal-handler restoration, repeated stop signals during cleanup, invalid deadlines, external interruption of a launcher and external interruption through the actual PetClinic wrapper. The last test substitutes two sleeping Python children for applications. These tests exercise real operating-system signals but do not execute PetClinic or Chromium.

`exit_confirmed` refers to the direct child. The new `descendant_cleanup: not_established` field prevents that observation from being read as complete browser or process-tree cleanup. If a leader exits before its descendants, or Chromium uses a separate process group, separate identity-qualified descendant evidence is still needed. Full application interruption, confirmation that owned descendants are gone, and a subsequent successful fresh-reset control remain open before timed evaluation.

The earlier hosted application observations and unified control reports remain unchanged. This step does not execute the forty Quartz mutation branches or complete the primary freeze.
