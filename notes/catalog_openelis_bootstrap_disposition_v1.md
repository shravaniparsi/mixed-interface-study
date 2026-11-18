# OpenELIS bootstrap unavailable within this study's bounds

Wave 46 acquired all seven scheduled migration blobs once at freeze
f58f93e172d41fb818c41e8bec0c64a76bb89a7d. The original root changelog first
runs the sequence-resynchronization guard, then includes 2.0.x.x/base.xml.
That base includes convert_id_types.xml first. Its first unguarded change set
modifies clinlims.login_user, drops/recreates its primary key and adds a column.
The preceding guard only iterates existing sequences/tables. Other early
changes require gender, site_information, test and reference_tables.
Consequently the inspected original migration chain requires the baseline
schema; it is not an empty-database bootstrap replacement.

The original database Dockerfile loads db/dbInit, including OpenELIS-Global.sql.
The frozen tree declares that seed as 863,876 bytes, exceeding the registered
262,144-byte source-file ceiling. It has not been fetched, split, read through
another source or executed. Its fixture scope therefore remains unverified.
The declared published images also lack qualified correspondence to the frozen
source; their missing revision labels do not prove they contain different code.

The study disposition is bootstrap qualification unavailable under the
registered bounds. It is not a claim of software ineligibility, irreproducibility,
clinical data in the seed, a runtime failure or a scientific null. We do not
spend an application job on a guessed baseline schema, remove original migration
requirements, substitute an unqualified image, or relax the file cap after this
inspection. The project remains in the twelve-project denominator without
replacement. No native producer, ordinary control or scientific case executed.

The disposition is supported by the evaluated original Docker initialization,
image metadata and migration entrypoints; no exhaustive claim about every
possible alternative OpenELIS deployment is made. Source identity records and
the decisive migration dependencies are in the bootstrap-disposition manifest.
Full study totals remain eight qualification jobs and zero scientific cases.
Four projects still require mapping decisions.
