#!/usr/bin/env bash
set -euo pipefail
ip link set lo up
ip -json address > "$ORDINARY_BASE/evidence/network-interfaces.json"
ip -json route > "$ORDINARY_BASE/evidence/network-routes.json"
export PG_BIN=/usr/lib/postgresql/16/bin
"$PG_BIN/postgres" --version | tee "$ORDINARY_BASE/evidence/pg-versions.txt" | grep -E '^postgres \(PostgreSQL\) 16\.'
for tool in initdb pg_ctl pg_dump pg_restore psql createdb dropdb; do
  "$PG_BIN/$tool" --version >> "$ORDINARY_BASE/evidence/pg-versions.txt"
  sha256sum "$PG_BIN/$tool" >> "$ORDINARY_BASE/evidence/pg-binaries.sha256"
done
id postgres >/dev/null
install -d -o postgres -g postgres -m 700 "$ORDINARY_BASE/pgdata"
runuser -u postgres -- "$PG_BIN/initdb" -D "$ORDINARY_BASE/pgdata" -U research -A trust --no-locale --encoding=UTF8 > "$ORDINARY_BASE/pg-bootstrap.log" 2>&1
runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$ORDINARY_BASE/pgdata" -l "$ORDINARY_BASE/pgdata/server.log" -o "-h 127.0.0.1 -p 55432 -k $ORDINARY_BASE/pgdata" -w start >> "$ORDINARY_BASE/pg-bootstrap.log" 2>&1
cleanup() { status=$?; trap - EXIT; runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$ORDINARY_BASE/pgdata" -m fast -w stop >> "$ORDINARY_BASE/pg-bootstrap.log" 2>&1 || status=1; exit "$status"; }
trap cleanup EXIT
"$PG_BIN/createdb" -h 127.0.0.1 -p 55432 -U research zipline
"$NODE_BIN" "$RUN_SCRIPT"
