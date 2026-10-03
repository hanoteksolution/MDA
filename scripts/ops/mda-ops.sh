#!/usr/bin/env bash
# MDA ERP production operations. Called by the root Makefile; see docs/deployment/SYSTEMD_OPERATIONS.md.
#
#   RESTART = restart the existing deployed container/image. No build, no recreate.
#   BUILD   = create a new image only. Running production is untouched.
#   REBUILD = preserve current image -> build -> recreate. No migrations (refuses if any are pending).
#   DEPLOY  = preflight -> preserve -> build -> [backend: stop workers+API, migrate, bootstrap]
#             -> recreate -> health/smoke -> automatic image rollback on failure when safe.
#
# Every mutating command takes a host-wide flock. Rollback uses only image IDs recorded in
# release manifests under $MDA_STATE_DIR; it never guesses and never reverses migrations.
set -euo pipefail
# shellcheck source=scripts/ops/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"

SYSTEMCTL=(systemctl)
[[ $EUID -eq 0 ]] || SYSTEMCTL=(sudo systemctl)

# ---------------------------------------------------------------- components
component_services() {
  case "$1" in
    frontend) echo "web" ;;
    backend)  echo "api celery celery-beat" ;;
    workers)  echo "celery celery-beat" ;;
    *) die "unknown component '$1' (frontend|backend|workers)" ;;
  esac
}
component_image()   { [[ "$1" == frontend ]] && echo mda-web || echo mda-api; }
component_primary() { [[ "$1" == frontend ]] && echo web || echo api; }

# ---------------------------------------------------------------- manifests
manifest_new() { # component action -> path
  mkdir -p "$MDA_STATE_DIR"
  local path
  path="$MDA_STATE_DIR/$(date -u +%Y%m%dT%H%M%SZ)-$1-$2.env"
  {
    echo "COMPONENT=$1"
    echo "ACTION=$2"
    echo "CREATED_AT=$(date -u +%FT%TZ)"
    echo "OPERATOR=${SUDO_USER:-$USER}"
    echo "GIT_HEAD=$(git -C "$MDA_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "GIT_DIRTY_PATHS=$(git -C "$MDA_ROOT" status --porcelain 2>/dev/null | wc -l)"
    echo "STATUS=started"
  } >"$path"
  echo "$path"
}
manifest_set() { # path key value
  if grep -q "^$2=" "$1"; then sed -i "s|^$2=.*|$2=$3|" "$1"; else echo "$2=$3" >>"$1"; fi
}
manifest_get() { { grep "^$2=" "$1" 2>/dev/null || true; } | tail -1 | cut -d= -f2-; }

# ---------------------------------------------------------------- preflight / preserve
preflight() { # component
  local svc
  log "preflight: compose config"
  compose config -q || die "compose config invalid"
  for svc in db redis; do
    [[ "$(docker inspect -f '{{.State.Health.Status}}' "mda_${svc/db/postgres}" 2>/dev/null)" == healthy ]] \
      || die "infrastructure container for '$svc' is not healthy — refusing to deploy"
  done
  for svc in $(component_services "$1"); do
    [[ "$(container_state "$svc")" == running ]] || die "${MDA_CONTAINER[$svc]} is not running — resolve before deploying"
  done
  local free_gb
  free_gb=$(df -BG --output=avail /var/lib/docker 2>/dev/null | tail -1 | tr -dc 0-9)
  [[ "${free_gb:-0}" -ge 5 ]] || die "less than 5 GB free for Docker"
  log "preflight: OK (component=$1, git=$(git -C "$MDA_ROOT" rev-parse --short HEAD), dirty paths=$(git -C "$MDA_ROOT" status --porcelain | wc -l))"
}

# Tag the image the component is RUNNING right now; refuse if its containers disagree
# (except for a rollback, which puts every container of the component back on one image).
preserve_running_image() { # component manifest [allow-mixed]
  local primary prev svc repo tag
  primary=$(component_primary "$1"); repo=$(component_image "$1")
  prev=$(container_image_id "$primary")
  [[ -n "$prev" ]] || die "cannot read running image of ${MDA_CONTAINER[$primary]}"
  for svc in $(component_services "$1"); do
    [[ "$(container_image_id "$svc")" == "$prev" || "${3:-}" == allow-mixed ]] \
      || die "${MDA_CONTAINER[$svc]} runs a different image than ${MDA_CONTAINER[$primary]} — mixed state, resolve manually"
  done
  tag="$repo:rollback-$(date -u +%Y%m%dT%H%M%SZ)"
  docker tag "$prev" "$tag"
  [[ "$(image_id "$tag")" == "$prev" ]] || die "rollback tag $tag does not resolve to $prev"
  manifest_set "$2" PREVIOUS_IMAGE_ID "$prev"
  manifest_set "$2" PREVIOUS_TAG "$tag"
  log "preserved running image $prev as $tag"
}

build_image() { # component manifest
  local svc repo new
  svc=$(component_primary "$1"); repo=$(component_image "$1")
  log "building $repo (running containers are not touched)"
  if ! compose build "$svc"; then
    manifest_set "$2" STATUS build_failed
    die "build failed — production untouched"
  fi
  new=$(image_id "$repo:latest")
  manifest_set "$2" NEW_IMAGE_ID "$new"
  log "built $repo:latest = $new"
}

# Pending migrations as seen by the NEW image (read-only; one-off container, no deps).
pending_migrations() {
  compose run --rm --no-deps -T api python manage.py showmigrations --plan 2>/dev/null \
    | awk '/^\[ \]/ {print $NF}' | paste -sd, -
}

recreate() { # service
  compose up -d --no-deps --no-build --force-recreate "$1"
  wait_running "$1" 90 || return 1
}

units_start() { local s; for s in "$@"; do "${SYSTEMCTL[@]}" start "${MDA_UNIT[$s]}"; done; }
units_stop()  { local s; for s in "$@"; do "${SYSTEMCTL[@]}" stop "${MDA_UNIT[$s]}"; done; }

web_ok() { [[ "$(http_code "$MDA_WEB_URL/")" == 200 && "$(http_code "$MDA_WEB_URL/login")" == 200 ]]; }
beat_ok() {
  [[ "$(container_state celery-beat)" == running \
    && "$(docker inspect -f '{{.State.Restarting}}' mda_celery_beat)" == false ]]
}

# Point :latest back at a recorded image and recreate the component on it.
# Returns non-zero (without aborting) when the image is back but a service is not healthy.
restore_image() { # component image_id
  local svc repo healthy=0
  repo=$(component_image "$1")
  [[ -n "$(image_id "$2")" ]] || die "recorded image $2 no longer exists — manual recovery required"
  docker tag "$2" "$repo:latest"
  if [[ "$1" == backend ]]; then
    units_stop celery-beat celery
    recreate api || healthy=1
    recreate celery || healthy=1
    wait_celery_ready || { log "WARNING: celery not ready after restore — check 'make logs-celery'"; healthy=1; }
    recreate celery-beat || healthy=1
    units_start api celery celery-beat || healthy=1
  else
    recreate web || healthy=1
    units_start web || healthy=1
  fi
  for svc in $(component_services "$1"); do
    [[ "$(container_image_id "$svc")" == "$2" ]] || die "${MDA_CONTAINER[$svc]} is not on $2 after restore"
  done
  return $healthy
}

# ---------------------------------------------------------------- commands
cmd_status() {
  local svc unit
  printf '%-24s %-10s %s\n' UNIT ACTIVE CONTAINER
  for svc in api web celery celery-beat; do
    unit=${MDA_UNIT[$svc]}
    printf '%-24s %-10s ' "$unit" "$(systemctl is-active "$unit" 2>/dev/null || true)"
    "$MDA_ROOT/scripts/ops/mda-service.sh" status "$svc"
  done
  printf '%-24s %-10s\n' mda-workers.target "$(systemctl is-active mda-workers.target 2>/dev/null || true)"
  echo "infra: postgres=$(docker inspect -f '{{.State.Health.Status}}' mda_postgres 2>/dev/null) redis=$(docker inspect -f '{{.State.Health.Status}}' mda_redis 2>/dev/null)"
  echo "images: mda-api:latest=$(image_id mda-api:latest | cut -c8-19) mda-web:latest=$(image_id mda-web:latest | cut -c8-19)"
}

cmd_health() {
  local fail=0
  if web_ok; then echo "frontend  OK   / and /login 200"; else echo "frontend  FAIL"; fail=1; fi
  if api_ready; then echo "api       OK   /api/v1/health/ready/ status=ok"; else echo "api       FAIL"; fail=1; fi
  if wait_celery_ready "${CELERY_HEALTH_TIMEOUT:-60}"; then echo "celery    OK   ping"; else echo "celery    FAIL"; fail=1; fi
  if beat_ok; then echo "beat      OK   running"; else echo "beat      FAIL"; fail=1; fi
  return $fail
}

cmd_logs() {
  local follow=()
  [[ "${FOLLOW:-0}" == 1 ]] && follow=(-f)
  compose logs --tail="${TAIL:-200}" "${follow[@]}" "$@"
}

cmd_restart() { # frontend|backend|workers|all
  acquire_lock
  local target="$1" svc
  case "$target" in
    frontend) set -- web ;;
    backend)  set -- api ;;
    celery)   set -- celery ;;
    beat)     set -- celery-beat ;;
    workers)  set -- celery celery-beat ;;
    all)      set -- api celery celery-beat web ;;
    *) die "restart: frontend|backend|celery|beat|workers|all" ;;
  esac
  declare -A before_img
  for svc in "$@"; do
    before_img[$svc]=$(container_image_id "$svc")
    [[ -n "${before_img[$svc]}" ]] || die "${MDA_CONTAINER[$svc]} does not exist"
    log "restart ${MDA_UNIT[$svc]} (current image ${before_img[$svc]:7:12}, no build)"
  done
  if [[ "$target" == workers ]]; then
    "${SYSTEMCTL[@]}" restart mda-workers.target
  else
    for svc in "$@"; do "${SYSTEMCTL[@]}" restart "${MDA_UNIT[$svc]}"; done
  fi
  for svc in "$@"; do
    [[ "$(container_image_id "$svc")" == "${before_img[$svc]}" ]] || die "${MDA_CONTAINER[$svc]} image changed during restart"
  done
  case "$target" in
    frontend) wait_for 60 web_ok || die "frontend unhealthy after restart" ;;
    backend)  wait_for 90 api_ready || die "API not ready after restart" ;;
    celery)   wait_celery_ready || die "celery not answering after restart" ;;
    beat)     wait_for 30 beat_ok || die "beat not running after restart" ;;
    workers)  wait_celery_ready || die "celery not answering after restart"; wait_for 30 beat_ok || die "beat not running" ;;
    all)      { wait_for 90 api_ready && wait_for 60 web_ok && wait_celery_ready && wait_for 30 beat_ok; } \
                || die "unhealthy after restart" ;;
  esac
  log "restart $target: OK"
}

cmd_build() { # frontend|backend|all
  acquire_lock
  local c m
  for c in $( [[ "$1" == all ]] && echo "backend frontend" || echo "$1" ); do
    m=$(manifest_new "$c" build)
    build_image "$c" "$m"
    manifest_set "$m" STATUS built
    log "build $c: image built, NOT deployed (manifest $m)"
  done
}

cmd_rebuild() { # frontend|backend
  acquire_lock
  local c="$1" m svc pending
  m=$(manifest_new "$c" rebuild)
  preserve_running_image "$c" "$m"
  build_image "$c" "$m"
  if [[ "$c" == backend ]]; then
    pending=$(pending_migrations)
    if [[ -n "$pending" ]]; then
      manifest_set "$m" STATUS refused_pending_migrations
      die "new backend image has pending migrations ($pending) — use 'make deploy-backend'; nothing was recreated"
    fi
    units_stop celery-beat celery
    recreate api || die "API failed to start — run 'make rollback-backend'"
    recreate celery
    wait_celery_ready || die "celery not ready on the new image — run 'make rollback-backend'"
    recreate celery-beat
    units_start api celery celery-beat
  else
    recreate web || die "frontend failed to start — run 'make rollback-frontend'"
    units_start web
  fi
  manifest_set "$m" STATUS deployed
  log "rebuild $c: recreated on $(manifest_get "$m" NEW_IMAGE_ID) (manifest $m)"
}

deploy_frontend() {
  local m prev
  preflight frontend
  m=$(manifest_new frontend deploy)
  preserve_running_image frontend "$m"
  prev=$(manifest_get "$m" PREVIOUS_IMAGE_ID)
  build_image frontend "$m"
  if [[ "$(manifest_get "$m" NEW_IMAGE_ID)" == "$prev" ]]; then
    manifest_set "$m" STATUS noop; log "frontend image unchanged — nothing to deploy"; return 0
  fi
  if recreate web && wait_for 60 web_ok && api_ready; then
    units_start web
    manifest_set "$m" STATUS deployed
    log "deploy-frontend: OK (manifest $m)"
  else
    log "frontend health failed — restoring $prev"
    if ! restore_image frontend "$prev"; then
      manifest_set "$m" STATUS failed_restore_unhealthy
      die "deploy-frontend failed; previous image restored but frontend is NOT healthy — check 'make status'"
    fi
    manifest_set "$m" STATUS failed_rolled_back
    die "deploy-frontend failed; previous frontend restored"
  fi
}

deploy_backend() {
  local m prev pending
  preflight backend
  m=$(manifest_new backend deploy)
  preserve_running_image backend "$m"
  prev=$(manifest_get "$m" PREVIOUS_IMAGE_ID)
  build_image backend "$m"
  if [[ "$(manifest_get "$m" NEW_IMAGE_ID)" == "$prev" ]]; then
    manifest_set "$m" STATUS noop; log "backend image unchanged — nothing to deploy"; return 0
  fi
  pending=$(pending_migrations)
  manifest_set "$m" PENDING_MIGRATIONS "${pending:-none}"
  log "pending migrations in new image: ${pending:-none}"

  log "stopping beat -> celery -> API"
  units_stop celery-beat celery api

  if [[ -n "$pending" ]]; then
    if ! compose run --rm --no-deps -T api python manage.py migrate --noinput; then
      manifest_set "$m" STATUS migrate_failed
      log "migration failed — restarting previous containers (old image, not recreated)"
      docker tag "$prev" mda-api:latest
      units_start api celery celery-beat
      die "deploy-backend failed at migrate; previous backend running again. Check the DB migration state before retrying."
    fi
    manifest_set "$m" MIGRATIONS_APPLIED "$pending"
  fi
  if [[ "${BOOTSTRAP:-0}" == 1 ]]; then
    log "bootstrap_system (additive)"
    compose run --rm --no-deps -T api python manage.py bootstrap_system
    manifest_set "$m" BOOTSTRAP_RUN yes
  fi

  log "starting API -> celery -> beat on the new image"
  if recreate api && wait_for 120 api_ready; then
    if recreate celery && wait_celery_ready && recreate celery-beat; then
      units_start api celery celery-beat
    fi
    if wait_celery_ready && beat_ok && web_ok; then
      manifest_set "$m" STATUS deployed
      log "deploy-backend: OK (manifest $m)"
      return 0
    fi
  fi
  if [[ -z "$pending" ]]; then
    log "backend health failed and no migrations were applied — restoring $prev"
    if ! restore_image backend "$prev"; then
      manifest_set "$m" STATUS failed_restore_unhealthy
      die "deploy-backend failed; previous image restored but backend is NOT healthy — check 'make status' / 'make logs-celery'"
    fi
    manifest_set "$m" STATUS failed_rolled_back
    die "deploy-backend failed; previous backend restored"
  fi
  manifest_set "$m" STATUS failed
  die "deploy-backend failed AFTER applying migrations ($pending); celery/beat may be stopped. Not rolled back automatically: inspect with 'make status', then decide on 'make rollback-backend CONFIRM=yes' (migrations are never reversed)."
}

cmd_deploy() { # frontend|backend|all
  acquire_lock
  case "$1" in
    frontend) deploy_frontend ;;
    backend)  deploy_backend ;;
    all)      deploy_backend; deploy_frontend ;;
    *) die "deploy: frontend|backend|all" ;;
  esac
}

cmd_rollback() { # frontend|backend|all
  acquire_lock
  local c m src target running applied
  for c in $( [[ "$1" == all ]] && echo "frontend backend" || echo "$1" ); do
    # Newest deploy/rebuild manifest that put the CURRENTLY running image in place (whatever
    # step it stopped at). Its PREVIOUS_IMAGE_ID is the only acceptable rollback target.
    running=$(container_image_id "$(component_primary "$c")")
    src=""
    while read -r f; do
      [[ "$(manifest_get "$f" NEW_IMAGE_ID)" == "$running" ]] || continue
      case "$(manifest_get "$f" STATUS)" in rolled_back|failed_rolled_back|noop) continue ;; esac
      src="$f"; break
    done < <(find "$MDA_STATE_DIR" -maxdepth 1 \( -name "*-$c-deploy.env" -o -name "*-$c-rebuild.env" \) 2>/dev/null | sort -r)
    [[ -n "$src" ]] || die "no recorded $c release put the running image $running in place — refusing to guess"
    target=$(manifest_get "$src" PREVIOUS_IMAGE_ID)
    [[ -n "$target" ]] || die "$src has no PREVIOUS_IMAGE_ID — refusing to guess"
    applied=$(manifest_get "$src" MIGRATIONS_APPLIED)
    if [[ -n "$applied" && "${CONFIRM:-}" != yes ]]; then
      die "$src applied migrations ($applied); they will NOT be reversed. Re-run with CONFIRM=yes if the old code is compatible."
    fi
    m=$(manifest_new "$c" rollback)
    manifest_set "$m" SOURCE_MANIFEST "$src"
    preserve_running_image "$c" "$m" allow-mixed
    log "rolling $c back to recorded image $target"
    manifest_set "$m" NEW_IMAGE_ID "$target"
    if ! restore_image "$c" "$target"; then
      manifest_set "$m" STATUS restored_unhealthy
      manifest_set "$src" STATUS rolled_back
      die "rollback $c: image $target restored but not healthy — check 'make status'"
    fi
    if [[ "$c" == backend ]]; then wait_for 120 api_ready || die "API not ready after rollback"
    else wait_for 60 web_ok || die "frontend unhealthy after rollback"; fi
    manifest_set "$m" STATUS deployed
    manifest_set "$src" STATUS rolled_back
    log "rollback $c: OK (manifest $m)"
  done
}

cmd_manage() { # migrate|bootstrap — against the CURRENTLY deployed API container
  acquire_lock
  [[ "$(container_state api)" == running ]] || die "mda_api is not running"
  if [[ "$1" == migrate ]]; then
    compose exec -T api python manage.py migrate --plan
    [[ "${CONFIRM:-}" == yes ]] || die "review the plan above; apply with: make migrate CONFIRM=yes"
    compose exec -T api python manage.py migrate --noinput
  else
    [[ "${CONFIRM:-}" == yes ]] || die "bootstrap_system is additive; run with: make bootstrap CONFIRM=yes"
    compose exec -T api python manage.py bootstrap_system
  fi
}

case "${1:-}" in
  status)   cmd_status ;;
  health)   cmd_health ;;
  logs)     shift; cmd_logs "$@" ;;
  preflight) shift; preflight "${1:-backend}" ;;
  restart)  cmd_restart "${2:?restart what?}" ;;
  build)    cmd_build "${2:?build what?}" ;;
  rebuild)  cmd_rebuild "${2:?rebuild what?}" ;;
  deploy)   cmd_deploy "${2:?deploy what?}" ;;
  rollback) cmd_rollback "${2:?rollback what?}" ;;
  migrate|bootstrap) cmd_manage "$1" ;;
  *) die "usage: $0 status|health|logs|preflight|restart|build|rebuild|deploy|rollback|migrate|bootstrap ..." ;;
esac
