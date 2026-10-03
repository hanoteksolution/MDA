# shellcheck shell=bash
# Shared helpers for MDA production operations. Sourced by mda-service.sh and mda-ops.sh.
# Controls the EXISTING Compose project "mda"; never runs Django/Celery/nginx on the host.

MDA_ROOT="${MDA_ROOT:-/home/ubuntu/projects/mda}"
MDA_PROJECT="mda"
MDA_COMPOSE_FILES=(docker-compose.yml docker-compose.vps.yml docker-compose.volumes.yml)
MDA_STATE_DIR="${MDA_STATE_DIR:-/var/lib/mda/releases}"
MDA_LOCK_FILE="${MDA_LOCK_FILE:-/run/lock/mda-ops.lock}"
MDA_WEB_URL="${MDA_WEB_URL:-http://127.0.0.1:8010}"

# compose service -> container name / systemd unit
declare -A MDA_CONTAINER=([api]=mda_api [web]=mda_web [celery]=mda_celery [celery-beat]=mda_celery_beat)
# shellcheck disable=SC2034  # used by mda-ops.sh
declare -A MDA_UNIT=([api]=mda-backend.service [web]=mda-frontend.service [celery]=mda-celery.service [celery-beat]=mda-celery-beat.service)

log()  { printf '%s [mda-ops] %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

compose() {
  local args=(-p "$MDA_PROJECT") f
  for f in "${MDA_COMPOSE_FILES[@]}"; do args+=(-f "$MDA_ROOT/$f"); done
  (cd "$MDA_ROOT" && docker compose "${args[@]}" "$@")
}

require_service() {
  [[ -n "${MDA_CONTAINER[$1]:-}" ]] || die "unknown service '$1' (expected: api web celery celery-beat)"
}

# Container ID of the compose-managed container for a service (empty if none exists).
container_id() {
  docker ps -aq --filter "label=com.docker.compose.project=$MDA_PROJECT" \
    --filter "label=com.docker.compose.service=$1"
}

container_image_id() { docker inspect -f '{{.Image}}' "${MDA_CONTAINER[$1]}" 2>/dev/null; }
container_started()  { docker inspect -f '{{.State.StartedAt}}' "${MDA_CONTAINER[$1]}" 2>/dev/null; }
container_state()    { docker inspect -f '{{.State.Status}}' "${MDA_CONTAINER[$1]}" 2>/dev/null || echo missing; }
image_id()           { docker image inspect -f '{{.Id}}' "$1" 2>/dev/null; }

wait_running() {
  local svc="$1" timeout="${2:-60}" i
  for ((i = 0; i < timeout; i++)); do
    [[ "$(container_state "$svc")" == running ]] && return 0
    sleep 1
  done
  return 1
}

# Host-wide lock: two build/deploy/rollback/restart operations never run concurrently.
acquire_lock() {
  mkdir -p "$(dirname "$MDA_LOCK_FILE")"
  exec 9>"$MDA_LOCK_FILE"
  flock -n 9 || die "another MDA operation holds $MDA_LOCK_FILE — wait for it to finish"
}

http_code() { curl -s -o /dev/null -m 15 -w '%{http_code}' "$1" || true; }

api_ready() {
  local body
  body="$(curl -sf -m 15 "$MDA_WEB_URL/api/v1/health/ready/" 2>/dev/null)" || return 1
  [[ "$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))' <<<"$body")" == ok ]]
}

wait_for() { # wait_for <seconds> <command...>
  local timeout="$1" i; shift
  for ((i = 0; i < timeout; i += 3)); do "$@" && return 0; sleep 3; done
  return 1
}

# One Celery ping against the worker in mda_celery (bounded by --timeout and timeout(1)).
celery_ping() {
  # shellcheck disable=SC2016  # $(hostname) must expand inside the container
  timeout 20 docker exec mda_celery sh -c \
    "celery -A config.celery inspect ping --timeout ${CELERY_PING_TIMEOUT:-5} -d celery@\$(hostname)" 2>&1
}

# Poll until the Celery worker answers ping. A running container is not a ready worker: it still
# has to boot, connect to the broker and finish mingle (~5-10 s). Returns as soon as it answers;
# fails (non-zero) after the bounded total, printing the last error and recent worker logs.
wait_celery_ready() { # [total_seconds]
  local total="${1:-${CELERY_READY_TIMEOUT:-90}}" interval="${CELERY_READY_INTERVAL:-2}"
  local start now attempt=0 out state
  start=$(date +%s)
  while :; do
    attempt=$((attempt + 1))
    state=$(docker inspect -f '{{.State.Status}}' mda_celery 2>/dev/null || echo missing)
    if [[ "$state" != running ]]; then
      log "celery: container is $state — not ready"
      return 1
    fi
    if out=$(celery_ping); then
      log "celery: ready (pong) after $(( $(date +%s) - start ))s, attempt $attempt"
      return 0
    fi
    now=$(date +%s)
    if (( now - start >= total )); then
      log "celery: NOT ready after ${total}s ($attempt attempts); last reply: $(tail -1 <<<"$out")"
      docker logs --tail 5 mda_celery 2>&1 | sed 's/^/    celery log: /' >&2
      return 1
    fi
    log "celery: waiting for worker (attempt $attempt, $(( now - start ))s/${total}s): $(tail -1 <<<"$out")"
    sleep "$interval"
  done
}
