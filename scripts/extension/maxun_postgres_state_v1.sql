\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
-- Retain every ordinary user table, including session/worker tables. Row order
-- is immaterial for a relation; JSON arrays inside each row are not reordered.
SELECT format(
  'SELECT jsonb_build_object(''schema'', %L, ''table'', %L, ''rows'', COALESCE((SELECT jsonb_agg(v ORDER BY v::text) FROM (SELECT to_jsonb(t) AS v FROM %I.%I t) q), ''[]''::jsonb));',
  n.nspname, c.relname, n.nspname, c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','p')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
  AND n.nspname NOT LIKE 'pg_temp%'
ORDER BY n.nspname,c.relname
\gexec
COMMIT;
