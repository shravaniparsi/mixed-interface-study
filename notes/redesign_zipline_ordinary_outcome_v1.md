# Zipline ordinary qualification v1 outcome

Run 44730884399 at freeze 9e836e89ad6dd6a64a9b1a1e31d86ceb8a12a49a failed in native_setup. Artifact 14625513560 (85742 bytes; SHA-256 d24f533215e1dab9f5d60fb2c6f8dfe76e9ee8483e703f3d079e71d7a966e11f) was retained and verified. Original startup, PGlite migrations, native setup and login completed; /api/user returned a user but no top-level token. The harness asserted that optional token existed. No URL creation, URL edit or altered input ran. This is an adapter error, not an application editability failure. GitHub reports 95000 ms duration and zero billable Ubuntu milliseconds. The one v1 attempt is closed, not rerun.

Diagnosis against already acquired original sources: wave-11 file 46 returns req.cookies.zipline_token only when present, whereas file 54 GET /api/user/token explicitly returns an encrypted API token for the session-authenticated user. No token rotation is necessary. A separately published development amendment may use this original read route; it must retain this failure and cannot count a corrected control as an independent replication or evaluation result.

Application logs also show a native UI version endpoint attempting an external request despite the feature setting; the loopback-only namespace blocked it. Do not claim that setting suppresses every call path. No network-isolation exception is introduced.
