#!/usr/bin/env bash
# Exit 0 when MDA ERP readiness check passes (for cron / uptime monitors)
set -euo pipefail

BASE="${1:-http://127.0.0.1:8010}"
BASE="${BASE%/}"

body="$(curl -sf --max-time 15 "$BASE/api/v1/health/ready/")"
status="$(echo "$body" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")"

if [[ "$status" != "ok" ]]; then
  echo "NOT READY: $body" >&2
  exit 1
fi

echo "ready: $body"
