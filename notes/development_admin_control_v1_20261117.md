# Ordinary native workflow control v1

Run 44105021413 at freeze 464e501 completed once per arm. The API arm created the fixed ordinary user (201), read back its ID and fields, loaded the original native editor, changed firstName, saved through PUT (200), and read back the same ID with the intended value. It establishes one operable API-to-UI workflow on the exposed application; it demonstrates no incompatibility.

The UI arm never reached browser execution. H2 startup failed with UnknownHostException for the isolated runner hostname. Its UI outcome is not-run, not rejected or incompatible. Both artifact ZIP digests were checked before extraction. The pair does not qualify because its UI control is missing. Version 2 prospectively corrects hostname resolution for both arms while retaining this run.

No independent evaluation cases, natural defects or method advantage were added. The manuscript remains prospective and Q1 readiness is unestablished.
