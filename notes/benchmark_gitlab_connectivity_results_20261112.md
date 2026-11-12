# GitLab connectivity diagnosis

Run 43170995499 at 490c0f03e00addc839d4d673093a50190cf496f8 completed six diagnostic rounds in 524 job-seconds (8.7333 infrastructure minutes). In-container port 8023 returned 502 initially and 200 in the five subsequent rounds for both /-/health and /users/sign_in. Port 80 never connected. Every host port-8023 request was connection-refused (errno 111), with and without proxies. Docker reported an empty published-port map on the internal bridge network. The final container state was running and healthy without OOM.

The evidence establishes working in-container HTTP service and absent effective host port publication in this configuration. It does not establish a general Docker defect, nor authenticate an actor. The scientific inputs are untouched. Correct the test connection by running the client in the container's network namespace while retaining the host filesystem/toolchain and internal network. This avoids changing the application or opening external routing. The correction requires a separately frozen qualification run; the old authentication v1 gate remains unsatisfied and that workflow is not dispatched.

No scientific cases or paid model calls ran. Startup v1 plus this diagnostic consumed 1757 job-seconds (29.2833 minutes), separate from previous image inspection and capacity checks. These durations are not a billing statement.
