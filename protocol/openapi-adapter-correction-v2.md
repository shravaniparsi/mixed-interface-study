# Single infrastructure correction for Punkpeye

Initial run 43163040718 used frozen commit b64f898aae93cc384919da08f5218ee3e86f66b3. Punkpeye stopped at npm ci, before converter initialization or scientific cases. Its npm-8-generated lock omitted the openapi-types peer required by swagger-parser. npm ci on Node 22 rejected the lock as incomplete.

The correction explicitly adds openapi-types 12.1.3, the missing version named in the installation error. Every existing package version and integrity hash remains identical. No converter source, wrapper, input, binding rule, scorer or expected state changes. The corrective job copies only the registered replacement package.json and lock into the original environment path after checking the initial and corrective freezes.

Dispatch only Punkpeye, once, after this commit's unit checks pass. Timeout 15 minutes; this consumes that subject's sole permitted infrastructure correction. No further attempt regardless of outcome. Do not repeat Prefect's completed 96 pairs. Ivo's zero-write binding failure remains unqualified under the original rule; no discovery-based name repair is made.

Initial run job durations were 26 seconds for Ivo, 23 seconds for Punkpeye, and 54 seconds for Prefect: 103 seconds (1.7167 job minutes), including installation and reference controls. This is runner elapsed accounting, not a billing statement. No paid models or paid infrastructure have been used. Original 90-minute ceiling remains binding.
