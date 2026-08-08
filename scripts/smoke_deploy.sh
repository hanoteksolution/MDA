#!/usr/bin/env bash
# Staging / production deploy smoke checks (STEP 33)
set -euo pipefail

BASE="${1:-http://127.0.0.1:8010}"
BASE="${BASE%/}"

echo "==> Smoke: $BASE"

check_http() {
  local path="$1"
  local label="$2"
  echo -n "  $label ... "
  code="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$path")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL (HTTP $code)"
    exit 1
  fi
  echo "ok ($code)"
}

check_envelope() {
  local path="$1"
  local label="$2"
  echo -n "  $label ... "
  body="$(curl -sf --max-time 15 "$BASE$path")"
  echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success') is True, d" >/dev/null
  echo "ok"
}

check_health() {
  echo -n "  API health ... "
  body="$(curl -sf --max-time 15 "$BASE/api/v1/health/")"
  echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='ok', d" >/dev/null
  echo "ok"
}

check_dep() {
  local path="$1"
  local label="$2"
  echo -n "  $label ... "
  body="$(curl -sf --max-time 15 "$BASE$path")"
  code="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$path" || echo "000")"
  echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='ok', d" >/dev/null
  echo "ok ($code)"
}

check_health
check_dep "/api/v1/health/database/" "Health database"
# Cache may be absent in minimal dev — warn only
echo -n "  Health cache ... "
cache_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$BASE/api/v1/health/cache/" || echo "000")"
if [[ "$cache_code" == "200" ]]; then
  echo "ok"
else
  echo "skipped (HTTP $cache_code — Redis optional in dev)"
fi
# Celery schedule must be registered; workers required only when REQUIRE_CELERY_WORKERS=1
echo -n "  Health celery ... "
celery_path="/api/v1/health/celery/"
if [[ "${REQUIRE_CELERY_WORKERS:-0}" == "1" ]]; then
  celery_path="/api/v1/health/celery/?require_workers=1"
fi
celery_code="$(curl -s -o /tmp/mda_celery_health.json -w '%{http_code}' --max-time 15 "$BASE$celery_path" || echo "000")"
if [[ "$celery_code" == "200" ]]; then
  python3 -c "import json; d=json.load(open('/tmp/mda_celery_health.json')); assert 'finance.scan_accounting_health' in d.get('scheduled_tasks', []), d" >/dev/null
  echo "ok"
elif [[ "${REQUIRE_CELERY_WORKERS:-0}" == "1" ]]; then
  echo "FAIL (HTTP $celery_code — workers required)"
  exit 1
else
  echo "skipped (HTTP $celery_code — start redis/celery for full stack)"
fi
check_envelope "/api/v1/mobile/meta/" "Mobile meta (public)"
check_http "/" "SPA index"
check_http "/api/v1/schema/" "OpenAPI schema"

echo "==> All smoke checks passed."
echo "    Tip: REQUIRE_CELERY_WORKERS=1 $0 $BASE  # fail if no celery workers"
