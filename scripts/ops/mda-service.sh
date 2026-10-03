#!/usr/bin/env bash
# systemd ExecStart/ExecStop helper: start or stop ONE existing Compose service container.
#   mda-service.sh start|stop|status <api|web|celery|celery-beat>
# start never builds, never recreates and never starts dependencies; it refuses when the
# container does not exist (creating containers is the job of deploy/rollback in mda-ops.sh).
set -euo pipefail
# shellcheck source=scripts/ops/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"

action="${1:-}"; svc="${2:-}"
require_service "$svc"
name="${MDA_CONTAINER[$svc]}"

case "$action" in
  start)
    [[ -n "$(container_id "$svc")" ]] || die "$name does not exist; create it with a deploy/rollback, not a start"
    compose up -d --no-deps --no-build --no-recreate "$svc"
    wait_running "$svc" 60 || die "$name did not reach running state"
    # systemd reports success only once the worker answers, so Beat (ordered after) and any
    # health check that follows see a ready worker, not just a running container.
    if [[ "$svc" == celery ]]; then wait_celery_ready || die "$name running but the worker never answered ping"; fi
    log "$name running image=$(container_image_id "$svc") started=$(container_started "$svc")"
    ;;
  stop)
    [[ -n "$(container_id "$svc")" ]] || { log "$name does not exist; nothing to stop"; exit 0; }
    compose stop "$svc"
    log "$name stopped"
    ;;
  status)
    printf '%-16s %-8s image=%s started=%s\n' "$name" "$(container_state "$svc")" \
      "$(container_image_id "$svc" | cut -c8-19)" "$(container_started "$svc")"
    ;;
  *) die "usage: $0 start|stop|status <api|web|celery|celery-beat>" ;;
esac
