#!/bin/sh
set -eu
PORT="${FOCUS_API_PORT:-18000}"
export FOCUS_API_PORT="$PORT"
cleanup() { docker compose down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker compose up -d --build
curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 1 "http://127.0.0.1:${PORT}/health" >/dev/null
response=$(curl --fail --silent --show-error -F 'file=@fixtures/sample.csv' "http://127.0.0.1:${PORT}/api/v1/imports")
id=$(printf '%s' "$response" | sed -n 's/.*"import_id":"\([^"]*\)".*/\1/p')
[ -n "$id" ]
for attempt in $(seq 1 30); do
  status=$(curl --fail --silent "http://127.0.0.1:${PORT}/api/v1/imports/$id")
  printf '%s\n' "$status" | grep -q '"status":"completed"' && break
  sleep 1
done
curl --fail --silent "http://127.0.0.1:${PORT}/api/v1/costs" | grep -q 'Storage'
docker compose restart api
curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 1 "http://127.0.0.1:${PORT}/health" >/dev/null
curl --fail --silent "http://127.0.0.1:${PORT}/api/v1/costs" | grep -q 'Storage'
PYTHONPATH=src .venv/bin/pytest -q tests/test_importer.py
(cd web && npm run test:e2e)
printf '%s\n' 'compose persistence and retry/DLQ drill passed'
