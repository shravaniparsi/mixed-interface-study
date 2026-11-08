# Quartz lifecycle qualification v1

This Linux hosted qualification uses the unchanged pair dispatcher, campaign driver, adapter and cleanup helpers. It selects ordinary controls only. No mutation branches execute.

Three stages run sequentially in new evidence directories. First, send SIGTERM to the campaign process after its first control has a live owned adapter, marked browser and listening JVM. The campaign must retain its first attempted job, stop before a second branch/job or follow-up is launched, and exit unsuccessfully. The outer pair runner must confirm exit without its own timeout or hard kill. The post-signal bound is 120 seconds, covering its existing 110-second shutdown grace and five-second kill-confirmation allowance.

Second, launch a new campaign and identify the same live-browser checkpoint. Send SIGSTOP only to the observed adapter PID after rechecking its process start identity; confirm the stopped state. Do not stop the browser, JVM or supervising runner. This forces the unchanged runner's ordinary 75-second case timer to send SIGTERM and its seven-second grace to expire before SIGKILL. No validation-pause flag or special timeout code path is used. The branch must record a timeout, unsuccessful SIGKILL adapter exit, incomplete result, successful cleanup and no subsequent branch. The branch lifecycle bound is 105 seconds including teardown, and the overall stage bound is 130 seconds.

After each failed attempt, confirm no observed live descendants remain and port 19965 is closed. Track identities using PID and process start ticks, including known reparented descendants. A rescue action fails qualification even if it removes the remaining process. Observations establish cleanup for observed identities, not unseen processes or every lifecycle phase.

Third, run a fresh complete ordinary-control campaign and independently regenerate its plan, raw component extraction and outcome ledger. Both pairs/four branches must pass and schedule no follow-ups. Preserve both unsuccessful attempts separately; do not resume, merge or replace their results. SIGSTOP is a harness fault injection, not an application mutation or empirical application defect.

Archive source hashes, commands, checkpoint identities, injection records, runner results, branch cleanup and the subsequent fresh controls. These records qualify two specific lifecycle paths. They do not establish broad deadline performance, selector calibration, fault prevalence, independent replication or primary-freeze completion.
