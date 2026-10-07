#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
V1_ROOT="${V1_ROOT:-/var/tmp/agentic-runtime-v1}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
V1_PORT="${V1_PORT:-55471}"
PG_BIN="${PG_BIN:-$(pg_config --bindir)}"
V1_TMPDIR="${V1_TMPDIR:-$V1_ROOT/tmp}"
V1_PGDATA="${V1_PGDATA:-$V1_ROOT/postgres-$STAMP}"
V1_SOCKET="$V1_ROOT/socket-$STAMP"
V1_RESULTS_DIR="${V1_RESULTS_DIR:-$REPO_ROOT/results/V1-CONCURRENCY-001/$STAMP}"
PG_LOG="$V1_ROOT/postgres-$STAMP.log"

mkdir -p "$V1_ROOT" "$V1_TMPDIR" "$V1_SOCKET" "$(dirname "$V1_RESULTS_DIR")"
export TMPDIR="$V1_TMPDIR" V1_ROOT V1_DATABASE_URL="postgresql://postgres@127.0.0.1:$V1_PORT/postgres"
export V1_RESULTS_DIR V1_RUNTIME_SHA="$(git -C "${AGENTIC_RUNTIME_CHECKOUT:?set AGENTIC_RUNTIME_CHECKOUT}" rev-parse HEAD)"
export AGENTIC_RUNTIME_SRC="${AGENTIC_RUNTIME_SRC:-$AGENTIC_RUNTIME_CHECKOUT/src}"

cleanup() {
  "$PG_BIN/pg_ctl" -D "$V1_PGDATA" -m fast -w stop >/dev/null 2>&1 || true
  python3 - "$V1_PGDATA" "$V1_SOCKET" <<'PY'
import pathlib, shutil, sys
for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
    if path.exists():
        shutil.rmtree(path)
PY
}
trap cleanup EXIT INT TERM

"$PG_BIN/initdb" -D "$V1_PGDATA" --no-locale --encoding=UTF8 --auth-local=trust --auth-host=trust --username=postgres --no-instructions
"$PG_BIN/pg_ctl" -D "$V1_PGDATA" -l "$PG_LOG" -o "-h 127.0.0.1 -p $V1_PORT -k $V1_SOCKET -c max_connections=160" -w start

cd "$REPO_ROOT"
set +e
uv run python -m harness.concurrency.campaign
STATUS=$?
set -e
if [[ "$STATUS" -ne 0 && -d "$V1_RESULTS_DIR" ]]; then
  pg_dump --dbname="$V1_DATABASE_URL" --format=custom --file="$V1_RESULTS_DIR/database-failure-state.dump" || true
fi
exit "$STATUS"
