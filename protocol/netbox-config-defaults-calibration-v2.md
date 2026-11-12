# NetBox calibration: sole infrastructure correction

Run 43156734009 failed on both pins while compiling psycopg-c 3.2.6, before migration or any application observation. Compiler diagnostics include missing integer macro definitions and nonconstant initializers. This establishes an environment build failure, not an application defect. Raw installation logs and run metadata remain in the v1 archive.

The one permitted correction changes the installation extra from psycopg[c,pool]==3.2.6 to psycopg[binary,pool]==3.2.6 in a separately recorded replay requirements file. Upstream requirements and application source remain unchanged. The driver package version is identical, but its packaged implementation and bundled libraries can differ; record resolved packages and apply the same environment to both application pins. Do not describe this as an exact original environment reproduction.

Use the unchanged v1 probe and all 24 prescribed cases. Preserve both attempts. Two sequential jobs, at most 15 minutes each, zero model calls. This adds a 30-minute ceiling to the first attempt's registered 30-minute ceiling. No further infrastructure retry is authorized by this calibration protocol. A second failure ends runtime qualification of this case in this phase. Both null and positive scientific results remain reportable.
