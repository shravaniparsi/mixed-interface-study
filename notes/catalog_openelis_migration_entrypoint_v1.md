# OpenELIS migration entrypoint and database wrapper

Wave 45 acquired the five scheduled original files at freeze
16638a400d0e3f2589b8943198d3a36d3d421d8f. No SQL, database or application ran.
The oversized OpenELIS-Global.sql seed was neither fetched nor split.

LiquibaseConfig obtains the original DataSource, selects
classpath:liquibase/base-changelog.xml, and uses spring.liquibase.contexts with
a default of "default". DatabaseConfig obtains jdbc/LimsDS through JNDI; the
commented retry implementation is inactive. application.properties contains no
active Liquibase context override in its inspected profile section.

The base changelog first includes upgrade/000-resync-id-sequences.xml, followed
by the versioned 2.0.x.x/base.xml and later upgrade sets. It does not itself
establish an empty-schema creation path. The first guard and earliest version
set still need inspection before deciding whether a seed-free initialization is
supported. No later migration or custom empty schema has been substituted.

The original database wrapper delegates to docker-entrypoint.sh. For an existing
cluster it may start background collation reindexing after readiness; it skips
that check for a fresh data directory, and declares an explicit skip setting.
The wrapper does not replace the Dockerfile's initdb scripts or prove that
restart state is unchanged. Any admitted restoration must account for its
background work rather than infer quiescence from server readiness.

The seed's fixture scope, executable provenance, full-state/session restoration
and native ordinary controls remain unqualified. No claim is made about actual
clinical rows or real data in the uninspected seed. Original source comments
about collation upgrades and migration ordering are retained exposure, not new
runtime defects or independent scientific cases.
