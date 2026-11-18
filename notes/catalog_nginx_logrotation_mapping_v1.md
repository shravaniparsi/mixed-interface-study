# Original startup log rotation mapping

Wave 25 acquired one 668-byte original configuration after publication at 53cee4ade5372adc4ab7e6fd330265eae0264e3f. The request succeeded once; no retry. Nginx Proxy Manager now consumes 97 source slots and 624,757 decoded bytes. No application or scientific input ran.

The original configuration selects /data/logs/*_access.log and /data/logs/*/access.log (weekly, four rotations), matching error logs (weekly, ten rotations), and /data/logs/backend.log (10M, five rotations, copytruncate). All groups use missingok, notifempty and compress. Access/error groups create files with mode 0644 under npm and send USR1 to the original nginx PID after rotation. Empty logs do not require rotation, but this does not establish that startup leaves the logrotate state database unchanged. The configuration supplies no explicit state-file location. The existing /var/lib/logrotate observation must therefore be reconciled with actual image behavior during the bounded qualification, rather than assuming a status filename from this file.

The build verifier now checks this acquired blob as the 97th source file. The live observer verifies its installed bytes. These are integrity checks, not permission to disregard log files, rotation state or metadata. The complete comparison/orchestration is still pending; the application job has not been dispatched.

CI 44302899864 completed successfully for the prior runtime-observer commit 63924aa14612cea00ca9c054512f5ce84ab1dbf3. It is a component check, not an application qualification or scientific case.
