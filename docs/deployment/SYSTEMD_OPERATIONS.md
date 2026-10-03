# Systemd + Makefile production operations

Installed and verified on the production VPS on 2026-09-24. Tests restarted the current production containers only. **No application release was built or deployed.**

## 1. The four verbs

| Verb | What it does | Builds? | Recreates containers? | Migrations? |
|---|---|---|---|---|
| **RESTART** | Stops and starts the existing container on its existing image. | No | No | No |
| **BUILD** | Creates a new image (`mda-api:latest` / `mda-web:latest`). Nothing running changes. | Yes | No | No |
| **REBUILD** | Preserves the running image under a rollback tag, builds, then recreates the containers on the new image. Refuses if the new backend image has pending migrations. | Yes | Yes | No (refuses) |
| **DEPLOY** | Controlled release: preflight, preserve, build, (backend) stop Beat→Celery→API, migrate, optional bootstrap, start API→Celery→Beat, health/smoke checks, automatic image rollback on failure when that is safe. | Yes | Yes | Backend only |

The pending application release is deployed with `make deploy*` **only after separate approval.**

## 2. Architecture

- The Compose project is `mda`, with files `docker-compose.yml` + `docker-compose.vps.yml` + `docker-compose.volumes.yml` in `/home/ubuntu/projects/mda`. The env file `backend/.env.cloud` is read by Compose only; no script reads or prints it.
- The app services and their containers are `api`→`mda_api`, `web`→`mda_web`, `celery`→`mda_celery` and `celery-beat`→`mda_celery_beat`. `api`, `celery` and `celery-beat` run the image `mda-api`; `web` runs `mda-web`.
- `db` (`mda_postgres`) and `redis` (`mda_redis`) are **independent infrastructure**. No unit, and no make target except `make status`/`health`, touches them.
- Every service keeps `restart: unless-stopped`. Docker itself restarts crashed containers and brings them back at boot.

### Systemd units (source: `deploy/systemd/`, installed in `/etc/systemd/system/`, enabled)

| Unit | Controls | Order |
|---|---|---|
| `mda-backend.service` | `api` | after `docker.service` |
| `mda-frontend.service` | `web` | after `mda-backend` (boot ordering only; no dependency) |
| `mda-celery.service` | `celery` | after `mda-backend`; `PartOf=mda-workers.target` |
| `mda-celery-beat.service` | `celery-beat` | after `mda-celery`; `PartOf=mda-workers.target` |
| `mda-workers.target` | worker + beat together | `restart` stops Beat→Celery and starts Celery→Beat |

Each service is `Type=oneshot` + `RemainAfterExit=yes`, calling `scripts/ops/mda-service.sh`:

- **start:** `docker compose up -d --no-deps --no-build --no-recreate <svc>`. It never builds, never recreates, never starts dependencies, and **refuses if the container does not exist**. Creating containers is the job of deploy/rollback. A second copy of a container therefore cannot be created, and `start` on a running container does nothing.
- **start, Celery only:** after the container is running, start also waits for the worker to answer `celery inspect ping` (see §2.1). So `systemctl start/restart mda-celery` returns success only once the worker is ready, and Beat (ordered after it) starts after that.
- **stop:** `docker compose stop <svc>`, which stops only that service (dependants are not stopped).
- **Why not `Type=simple` with `Restart=`:** Docker's restart policy already supervises the containers. A second supervisor in systemd would fight it. Systemd here is the operator interface and boot ordering. `systemctl status` shows `active (exited)` plus the last start log line (container, image ID, start time). For live container state use `make status`.
- **Boot:** Docker starts the containers itself, and the enabled units then run `start`, which does nothing on a running container. A unit stopped with `systemctl stop` stays stopped until it is started again. `systemctl disable` also keeps it stopped across reboots.
- `systemctl restart mda-backend` does **not** restart Celery/Beat. Celery has no `Requires=`/`BindsTo=`/`PartOf=` on the backend.

### 2.1 Celery readiness

A running `mda_celery` container is not yet a ready worker. It still has to boot, connect to Redis and finish mingle. Measured on the current image, the first ping fails ("No nodes replied") for about 6–9 s after a restart and succeeds at about 9–11 s. A single ping right after a restart therefore gave a false FAIL.

`wait_celery_ready` (`scripts/ops/lib.sh`) polls instead of sleeping blindly:

- Each attempt is `celery -A config.celery inspect ping -d celery@<container>` with a 5 s reply timeout (`CELERY_PING_TIMEOUT`), capped by `timeout 20`.
- There is a 2 s pause between attempts (`CELERY_READY_INTERVAL`).
- The total wait is bounded: 90 s by default (`CELERY_READY_TIMEOUT`), and 60 s for `make health` (`CELERY_HEALTH_TIMEOUT`).
- It returns on the first `pong` and logs each waiting attempt with elapsed time and the last reply.
- It fails immediately if the container is not running.
- On timeout it exits non-zero and prints the last reply and the last 5 worker log lines.

It is used by:

- the `mda-celery` unit's start;
- `make health`;
- `make restart-celery`, `make restart-workers` and `make restart`;
- `make deploy-backend` and `make rebuild-backend`, which start Beat only after Celery answers and declare success only after that;
- image restore and rollback.

If the image is restored but a service is still unhealthy, the manifest records `STATUS=failed_restore_unhealthy` (or `restored_unhealthy` for a rollback) and the command exits non-zero with an explicit message. It no longer aborts silently.

## 3. Commands (copy/paste)

```bash
cd /home/ubuntu/projects/mda

# Observe
make status                 # units + container state/image + infra health + :latest IDs
make health                 # frontend / and /login 200, API /health/ready/, celery ping, beat running (exit 1 if degraded)
make logs                   # all app services, follows (FOLLOW=0 to print and exit, TAIL=200)
make logs-frontend | logs-backend | logs-celery | logs-beat

# RESTART — current deployed image, no build
make restart-frontend       # web only
make restart-backend        # API only (workers and frontend untouched)
make restart-celery         # celery worker only
make restart-beat           # beat only
make restart-workers        # celery + beat (mda-workers.target)
make restart                # API, workers, frontend (never db/redis)

sudo systemctl restart mda-frontend        # same as make restart-frontend, without the health check
sudo systemctl restart mda-backend
sudo systemctl restart mda-celery
sudo systemctl restart mda-celery-beat
sudo systemctl restart mda-workers.target
sudo systemctl status  mda-frontend mda-backend mda-celery mda-celery-beat

# BUILD — image only, nothing restarted
make build-frontend | build-backend | build

# REBUILD — preserve + build + recreate (no migrations; backend refuses if any are pending)
make rebuild-frontend | rebuild-backend | rebuild

# DEPLOY — controlled release
make deploy-backend                 # add BOOTSTRAP=1 when the release adds permissions
make deploy-frontend
make deploy                         # backend first, then frontend

# ROLLBACK — to the image recorded in the release manifest
make rollback-frontend
make rollback-backend               # needs CONFIRM=yes if that release applied migrations
make rollback                       # frontend, then backend

# One-off management with the DEPLOYED API image
make migrate                        # prints the plan only
make migrate CONFIRM=yes            # applies it
make bootstrap CONFIRM=yes          # additive roles/permissions

# Units
make install-systemd                # systemd-analyze verify + install + daemon-reload
make verify-systemd                 # repo copy vs installed copy + enabled state
```

The make targets `restart*`, `build*`, `rebuild*`, `deploy*`, `rollback*`, `migrate` and `bootstrap` take the host lock `/run/lock/mda-ops.lock` (`flock -n`). A second one started at the same time exits immediately with an error. Raw `systemctl restart` does not take the lock, so avoid it while a deploy is running.

## 4. Deploy details (`scripts/ops/mda-ops.sh`)

**deploy-backend**

1. Lock.
2. Preflight: `compose config`, Postgres/Redis healthy, API/Celery/Beat running, ≥ 5 GB free. Records git HEAD and dirty-path count.
3. Preserve: reads the image ID that `mda_api` is **running**, requires Celery/Beat to run the same ID, tags it `mda-api:rollback-<UTC timestamp>` and writes the manifest.
4. Build `mda-api`. **A failed build stops here and production is untouched.**
5. Lists pending migrations with the *new* image (read-only one-off container).
6. Stops Beat → Celery → API.
7. Applies migrations with the new image. If migrate fails, `mda-api:latest` is reset to the previous image, the **old** containers are started again (not recreated), and the command stops.
8. `BOOTSTRAP=1` → `bootstrap_system` (additive).
9. Recreates API, waits for `/api/v1/health/ready/`, then recreates Celery and Beat.
10. Smoke checks: Celery ping, Beat running, frontend 200.
11. On failure:
    - **No migrations were applied:** the previous image is restored automatically.
    - **Migrations were applied:** the command stops with `STATUS=failed`, and Celery/Beat may be stopped. Nothing is reversed automatically; the operator decides on `make rollback-backend CONFIRM=yes`.

**deploy-frontend**

Preflight → preserve `mda-web` → build → recreate `web` → `/` and `/login` 200 and API still ready. If the checks fail, the previous image is restored automatically. The backend, the database and the workers are never touched.

**deploy:** backend first, then frontend. If the backend fails, the frontend is not deployed.

If the newly built image is identical to the running one, the manifest records `STATUS=noop` and nothing is recreated.

## 5. Rollback and manifests

- **Location:** manifests are written to `/var/lib/mda/releases/<UTC>-<component>-<action>.env`. Fields: `PREVIOUS_IMAGE_ID`, `PREVIOUS_TAG`, `NEW_IMAGE_ID`, `PENDING_MIGRATIONS`, `MIGRATIONS_APPLIED`, `BOOTSTRAP_RUN`, `GIT_HEAD`, `GIT_DIRTY_PATHS`, `STATUS`, `OPERATOR`.
- **Choosing the target:** `make rollback-*` picks the newest deploy/rebuild manifest whose `NEW_IMAGE_ID` is the image **currently running**, and restores its `PREVIOUS_IMAGE_ID`. It retags `:latest` to that ID and recreates the component's containers. If no manifest matches, it **refuses** ("refusing to guess").
- **Repeated rollback:** after a rollback the source manifest is marked `rolled_back`, so running rollback again also refuses. Rollback never chains backwards on its own.
- **Migrations:** they are never reversed. Rolling back a release that applied migrations requires `CONFIRM=yes`.
- **Image cleanup:** nothing deletes rollback images. Prune them manually, and never with `docker image prune -a` while a rollback might still be needed.
- **Current baseline:** there are no manifests yet. The running release (`production-2026-09-23`) is preserved as:
  - `mda-api:rollback-pre-20260924` → `sha256:8156dd21a027…`
  - `mda-web:rollback-pre-20260924` → `sha256:e3c08480d09f…`

  The first `make deploy*` records these IDs as `PREVIOUS_IMAGE_ID` automatically.

## 6. Safety rules built in

- No target runs `docker compose down`, `prune`, `rmi` or `volume rm`. The old dev targets `docker-up`, `docker-down` and `docker-build` were **removed**: without `-p` they used project `mda` (production) and fixed container names.
- Local dev targets that clashed with the production names were renamed: `local-migrate`, `local-bootstrap` and `local-build` (the old dev `migrate`, `bootstrap` and `build`).
- Django, Celery and nginx never run on the host. Everything runs inside the existing Compose containers.
- No secrets live in the units or scripts.

## 7. Verification record (2026-09-24, current production images only)

| Check | Result |
|---|---|
| Static validation | `bash -n`; shellcheck clean; `systemd-analyze verify` on all 5 units; `make -n` for every target; `compose config -q`; secret/`down` scan |
| Simulated build/deploy/rollback logic | 17 scenarios against fake `docker`/`systemctl`/`curl` (scratchpad, no real containers): deploy OK, bad frontend auto-restore, build failure untouched, backend with migration, rollback with/without `CONFIRM`, failure before/after migrate, rebuild refusing pending migrations, deploy all + rollback all, no-manifest refusal, lock contention |
| Unit install/start | Containers unchanged (same IDs and start times); still 6 containers, no duplicates |
| `systemctl restart mda-frontend` | Only `mda_web` restarted (same image); HTTP 200 locally and publicly |
| `systemctl restart mda-backend` | Only `mda_api` restarted; health 200; frontend and workers untouched |
| `systemctl restart mda-workers.target` | Only Celery/Beat restarted; Beat stopped first; ping OK |
| `make restart-frontend/-backend/-celery/-beat/-workers`, `make restart` | Each restarted only its own containers on the same image |
| Lock contention | `make restart-frontend` refused while the lock was held; nothing restarted |
| Celery readiness race (2026-09-24) | Reproduced: ping failed about 7 s after restart and succeeded at about 10 s. After the fix, `make health` → `make restart-workers` → `make health` and a raw `systemctl restart mda-celery` + immediate `make health` all pass. The unit journal shows the bounded wait absorbing the startup gap. |
| Not executed (by design) | `make build*`, `rebuild*`, `deploy*`, `rollback*`, `migrate CONFIRM=yes`, `bootstrap CONFIRM=yes` |
