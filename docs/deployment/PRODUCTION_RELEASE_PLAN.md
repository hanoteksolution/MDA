# Production Release Plan — Platform Integrations, SMS Reseller, Subscription Auto-Payment (+ School UI)

Prepared: 2026-09-23. Status: **awaiting deployment approval.** Nothing in production was changed while preparing this plan. All production checks were read-only (`docker cp`, `showmigrations`, ORM counts, `docker inspect`).

## 1. What production runs today

| Item | Value |
|---|---|
| Stack | Compose project `mda`, working dir `/home/ubuntu/projects/mda`, files `docker-compose.yml` + `docker-compose.vps.yml` + `docker-compose.volumes.yml` |
| Containers | `mda_api` (gunicorn), `mda_celery`, `mda_celery_beat` (all image `mda-api`), `mda_web` (image `mda-web`), `mda_postgres` (Postgres 16), `mda_redis` |
| Images | `mda-api` built 2026-09-22 16:55 UTC; `mda-web` built 2026-09-22 16:58 UTC. Both were baked from the **uncommitted** working tree. There is no source mount. |
| Settings | `config.settings.production`, `DEBUG=False`, env file `backend/.env.cloud` |
| DB migrations | Every migration inside the running image is applied (0 unapplied). |
| Git | HEAD `3a90c8e` (2026-08-26). All later work is uncommitted: 137 modified and 142 untracked paths. |

The host also runs unrelated stacks (`services-prod`, `cafeteria`, `vms`, `inventory`, …). Every command below names the `mda` project and compose files explicitly. **Never** run a bare `docker compose` or `docker system prune`.

## 2. Release delta (working tree vs the running production image)

The delta was measured with a file-level diff of `/app` in `mda_api` against `backend/`, plus the frontend sources modified after the `mda-web` build.

| Workstream | Backend | Frontend | Already in production? |
|---|---|---|---|
| **Branch Management** (Phases 1–9) | none | none | **Yes.** Production already has organization 0001–0004, inventory 0007, finance 0011, notifications 0004, sales 0012 and integrations 0002, and its code matches the tree. |
| **School** backend (Phases 1–6) | none | — | **Yes.** |
| **School frontend restructure** | none (uses existing APIs) | `modules/school/**`, `navigation/schoolNavigation.ts`, `layouts/Sidebar/SidebarSection.tsx`, `components/data/FilterBar.tsx` (aria-label only) | **No.** |
| **Platform Admin integrations separation** | `api/v1/integrations/{platform_access,platform_urls}.py`, `views.py`, `payment_views.py`, `urls.py`, `api/v1/urls.py` | `modules/platform/pages/PlatformIntegrationsPage.tsx`, `settings/integrations/**`, `components/auth/PermissionGuard.tsx` (`elevatedOnly`), `navigation/businessWorkspaces.ts` | No |
| **SMS Reseller** | `apps/integrations/models/sms_billing.py`, `models/sms.py`, `services/sms_credit_service.py`, `services/sms_service.py`, `tasks.py`, `api/v1/integrations/sms_billing_views.py`, **migration `integrations/0003_sms_billing`**, `config/settings/base.py` (`SMS_CREDITS_ENFORCED`, beat entry), `authentication/bootstrap.py` | `settings/integrations/components/smsBilling.tsx`, `services/api/integrations.ts`, routes | No |
| **Subscription Auto-Payment** | `apps/platform/services/subscription_billing_service.py`, `models/tenant.py`, `services/platform_service.py`, `services/entitlement_service.py` (write-gate exemptions), `api/v1/billing/**`, `api/v1/platform/views.py`, `integrations/services/payment_service.py` (settlement hook), **migration `platform/0019_subscription_checkout`** | `modules/billing/**`, `services/api/billing.ts`, `PlatformSubscriptionsPage.tsx`, `services/api/platform.ts`, `SettingsPage.tsx`, `app/router.tsx` | No |
| Tests and docs | `tests/**` (new and updated), `config/settings/test.py` | `*.test.ts(x)` | n/a (not runtime) |
| Pre-existing / other | none | `pages/auth/OnboardingPage.tsx`: modified 2026-09-22 16:56, inside the web build window, so **most likely already shipped**. Verify it in the smoke test. | likely |

Every hunk in the shared backend files (`bootstrap.py`, `base.py`, `platform_service.py`, `entitlement_service.py`, `api/v1/urls.py`, `platform/views.py`) was checked. All of them belong to the three billing/platform workstreams. No existing migration file differs from production.

## 3. Dependency map

```
integrations/0003_sms_billing ── depends on ─ integrations/0002_payments (prod), platform/0018 (prod)
platform/0019_subscription_checkout ── depends on ─ integrations/0003, platform/0018 (prod), sales/0012 (prod)

Platform separation (platform_access.IsPlatformIntegrationsAdmin, PLATFORM perms)
   └─ used by SMS Reseller platform views (sms_billing_views imports PLATFORM, target_tenant)
        └─ SmsPurchaseService.apply_event hooked into PaymentService.process_event
Subscription Auto-Payment
   ├─ PaymentService._settle hook (same file as SMS hook) → integrations code
   ├─ SubscriptionPayment.intent FK → integrations.PaymentIntent (0002, prod) — graph also orders after 0003
   ├─ sales Invoice/DocumentSequence, finance posting (prod)
   └─ bootstrap.py + base.py + api/v1/urls.py shared with SMS Reseller
Frontend: one bundle (mda-web). navigation/businessWorkspaces.ts + Sidebar carry BOTH the School nav
   and the Platform→Integrations nav; router.tsx carries billing + platform routes.
```

The three backend workstreams cannot be shipped separately. They share `payment_service.py`, `bootstrap.py`, `base.py` and `api/v1/urls.py`, and `0019` depends on `0003`. The School UI and the Platform UI share `businessWorkspaces.ts`, `Sidebar.tsx` and the router, so the frontend bundle cannot be split without editing code.

## 4. Strategy

**Recommended: A. Deploy all completed, compatible work together.**

- The real delta is small and well-bounded: Platform separation + SMS Reseller + Subscription Auto-Payment on the backend, plus the School UI restructure on the frontend. Branch and the School backend are already live.
- **B (a clean release branch) is riskier here.** Production's baseline was itself built from an *uncommitted* tree, so git cannot reproduce it. A branch cut from HEAD (2026-08-26) would *remove* Branch and School code that production runs today. Rebuilding that baseline by hand invites mistakes.
- Before building, **freeze the exact tree** (user action; I have not done this): create a release commit or tag on a release branch, or at minimum `git stash create` plus a tarball. That makes the image reproducible and diffable later.

## 5. Production migration order

These are the only two unapplied migrations. Both are additive, and neither contains RunPython or RunSQL.

1. `integrations.0003_sms_billing`: 6 new tables (`sms_packages`, `sms_billing_settings`, `sms_credit_accounts`, `sms_package_purchases`, `sms_credit_lots`, `sms_credit_entries`), 2 new `sms_logs` columns (`credit_units` default 0, `credit_state` default ''), 8 constraints.
2. `platform.0019_subscription_checkout`: 7 new `subscription_payments` columns (`currency`, `failure_reason`, `idempotency_key`, `kind` as NOT NULL ''; `intent`, `invoice`, `plan` as nullable FKs), status choices widened (no DB change), and the partial unique index `uniq_subscription_payment_key` on `(subscription, idempotency_key) WHERE idempotency_key <> ''`.

`python manage.py migrate --plan` must list **exactly these two** and nothing else; stop if it lists anything more. The production volumes are tiny (`sms_logs` 0 rows, `subscription_payments` 14, `tenant_subscriptions` 13), so the locks are sub-second.

## 6. Risk classification

| Migration / change | Classification | Notes |
|---|---|---|
| `0003` / `0019` forward | Additive and non-destructive | No backfill; existing rows get empty defaults; the partial unique index excludes the 14 existing rows (their key is ''). |
| **New NOT NULL columns without a DB default** | **Ordering-sensitive** | Django drops the temporary default after adding the column. Once migrated, the **old** image cannot insert `SubscriptionPayment` rows (it creates them when rendering expiry alerts) or `SmsLog` rows. So migrate only while the new image is going live, with the old API/workers stopped. |
| `0003` / `0019` reverse | **Destructive** | Drops the SMS billing tables and the checkout columns. Safe only while no packages, purchases or ledger rows exist. Take a dump first, always. |
| Waafi callback retired (410) | Behavior change | It was unsigned and public. Production has **0** callback confirmations and 0 hits in 30 days of logs, so nothing depends on it. |
| Manual subscription confirm now requires a reason and refuses online checkouts | Behavior change | The platform console prompts for the reason; the 10 legacy pending rows can still be confirmed manually. |
| Provider configuration moved to Platform Admin | Behavior change | Production has **0** SMS and **0** payment providers, so no tenant loses a working configuration. |
| `SMS_CREDITS_ENFORCED` (code default **True**) | Policy change | Production has 0 active SMS providers, so there is no immediate effect. Set it **explicitly** in `.env.cloud` (see step 7). |
| New permissions | Needs bootstrap | `integrations.sms.billing.view|purchase`, `billing.subscription.view|pay`, added to the system **admin** role. Tenant-custom roles do not get them automatically. |
| Write-gate exemptions (`/api/v1/billing/`, provider webhooks) | Intended | Lets an expired tenant pay, and a webhook always settle. |

## 7. MOCK / billing provider

- **The release configures no provider.** No migration, bootstrap, seed or demo code creates a `MOCK` payment or SMS provider, or sets `payment_provider_id` / `SmsBillingSettings.payment_provider`. Production currently has 0 payment providers.
- With no billing provider, SMS package purchases and subscription checkout **fail safely** ("…not available yet. Contact support."). There is no manual online-payment path, and the legacy manual confirm refuses online checkouts.
- **Server-side guard (now in this release, was a recommended follow-up):** MOCK is refused as a billing provider in production — the control is enforced in code, not by operator discipline. `apps/integrations/billing_guard.py` is enforced at **two** layers:
  1. **Selection** — a Platform Admin choosing a billing provider is rejected with `MOCK payment providers cannot be used as the billing provider in production.` (`api/v1/platform/views.py`, `api/v1/integrations/sms_billing_views.py`).
  2. **Runtime resolution** — `usable_billing_provider()` returns `None` for a MOCK row *however it got there*, so a provider configured before this release, or inserted directly in the DB, still cannot collect money. Inactive and soft-deleted rows resolve to `None` too.
- **No MOCK fallback exists.** When no usable provider is configured, `SubscriptionBillingService.billing_provider()` and `SmsPurchaseService.billing_provider()` both return `None`; neither substitutes MOCK.
- **Switch:** `PAYMENT_ALLOW_MOCK_PROVIDERS` is the literal `False` in `config/settings/production.py` — **not** read from the environment, so no `.env` value or typo can open it. It defaults to `DEBUG` in `base.py` and is explicitly `True` in `development.py` and `test.py`, so MOCK remains fully usable for development and tests.
- **Verified 2026-09-23** (`tests/unit/test_billing_guard.py`, 10 tests, markers `unit`/`critical`): production blocks selection and runtime resolution of MOCK; development/test still allow it; absent/inactive/deleted providers resolve to `None`; both money paths (subscription checkout, SMS package purchase) resolve to no provider rather than falling back. A guard test parses `production.py` with `ast` and fails if the literal `False` is ever replaced by `config(...)`.
- `INTEGRATION_ENCRYPTION_KEY` is **unset** in production, so the credential store refuses to save secrets (by design). It must be set, and backed up securely, before onboarding the real provider, but it is not needed for this release.
- Safari billing provider status: **WAITING FOR REAL PROVIDER API.**
- **Production state verified read-only 2026-09-23** (no writes, no restart): settings module `config.settings.production`, `DEBUG=False`, **0 payment providers** (`PaymentProviderConfig.objects.count() == 0`, no rows of any type). The running image predates this release, so `PAYMENT_ALLOW_MOCK_PROVIDERS` is not yet present there; it takes effect on deploy, hardcoded `False`. Until a real provider is onboarded, subscription checkout and SMS package purchasing continue to fail safely as "not available".

## 8. Runbook

Run from `/home/ubuntu/projects/mda`. Define these first:

```bash
C="docker compose -p mda -f docker-compose.yml -f docker-compose.vps.yml -f docker-compose.volumes.yml"
TS=$(date -u +%Y%m%dT%H%M%SZ)
```

**0. Approval and freeze.** Get deployment approval, pick a low-traffic window, and freeze the tree (release commit or tag; see §4). Confirm nobody is editing the tree.

**1. Backup (mandatory).**

```bash
mkdir -p backups
docker exec mda_postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/mda_erp_pre_release_$TS.dump
docker exec -i mda_postgres pg_restore --list < backups/mda_erp_pre_release_$TS.dump | head   # must list the TOC, not fail
cp backend/.env.cloud backups/env.cloud.$TS                                                  # store securely; contains secrets
```

See `docs/deployment/RESTORE_DRILL.md` for the restore procedure.

**2. Preserve the current images for rollback.**

```bash
docker tag mda-api mda-api:rollback-$TS
docker tag mda-web mda-web:rollback-$TS
```

**3. Preflight** (read-only; production keeps running).

```bash
$C exec -T api python manage.py showmigrations | grep -c '\[ \]'   # expect 0
$C exec -T api python manage.py check --deploy --settings=config.settings.production
```

Then confirm `backend/.env.cloud` holds the intended values (next step).

**4. Set SMS policy explicitly.** Add **one** of these lines to `backend/.env.cloud`; this is a product-owner decision:

- `SMS_CREDITS_ENFORCED=True`: the reseller model; SMS sends need purchased credits. Recommended, because no tenant sends SMS today.
- `SMS_CREDITS_ENFORCED=False`: legacy unmetered sending.

**5. Build the new images.** Production keeps running on the old images during the build.

```bash
$C build api web        # celery and celery-beat reuse the mda-api image
```

To check the image before switching over, run the new image's migration plan against production's DB:

```bash
$C run --rm --no-deps api python manage.py migrate --plan
```

It must list exactly `integrations.0003_sms_billing` and `platform.0019_subscription_checkout`. Stop if it lists anything else.

**6. Stop writers** so the old code cannot hit the migrated schema. This is a short maintenance window.

```bash
$C stop celery-beat celery api
```

**7. Migrate** with the new image:

```bash
$C run --rm --no-deps api python manage.py migrate integrations 0003_sms_billing
$C run --rm --no-deps api python manage.py migrate platform 0019_subscription_checkout
$C run --rm --no-deps api python manage.py migrate --check    # exits non-zero if anything is left
```

**8. Bootstrap permissions.** It is additive; **never** pass `--reset-role-permissions`.

```bash
$C run --rm --no-deps api python manage.py bootstrap_system
```

**9. Start the new API, then the workers, then Beat.** Beat picks up the new `integrations-sms-credit-expiry` schedule.

```bash
$C up -d --no-deps api
./scripts/check_health.sh http://127.0.0.1:8010          # readiness must be ok before continuing
$C up -d --no-deps celery
$C up -d --no-deps celery-beat
$C up -d --no-deps web
```

**10. Health checks.**

- `scripts/check_health.sh` passes.
- `$C ps` shows the `mda` containers healthy.
- `docker logs --since 10m mda_api` shows no tracebacks.
- `mda_celery` logs `ready`.
- `mda_celery_beat` logs the expiry and retry schedules.

**11. Smoke tests.** Run `scripts/smoke_deploy.sh` and these checks.

| Check | Expected |
|---|---|
| Super Admin: Platform → Integrations loads; tenant selector and SMS billing tabs render | Billing provider shows "Not configured" |
| Tenant admin: Settings → Integrations | Shows only templates, logs, test SMS, payments and "Packages & billing"; **no** providers or credentials |
| Tenant admin: `/billing` | Shows the plan, expiry and history; Pay/Renew is disabled with "Online payment is not available yet" |
| `GET /api/v1/platform/integrations/sms-providers/?tenant_id=<any>` as a tenant admin | 403 |
| `POST /api/v1/platform/payments/waafi-callback/` | 410 |
| School module (web) | Grouped sidebar, dashboard, a student list and a detail page load |
| Onboarding page | Renders (confirms the pre-existing `OnboardingPage.tsx` state) |
| Superadmin with no tenant | Still reaches the platform pages (bypass intact) |

**12. Record.** Note the deployed image IDs, the dump file name, the result of `showmigrations`, and the smoke-test results.

## 9. Rollback

Pick the path by symptom.

**R1. Frontend-only issue.**

```bash
docker tag mda-web:rollback-$TS mda-web && $C up -d --no-deps web
```

The database is unaffected.

**R2. Backend issue, and no new-feature data has been written** (no SMS packages, purchases, ledger rows or checkouts). This is expected while the billing provider is unconfigured.

1. `$C stop celery-beat celery api`
2. Reverse the migrations with the **new** image (it knows the reverse operations), in reverse order:
   ```bash
   $C run --rm --no-deps api python manage.py migrate platform 0018_alter_agreementacceptance_created_by_and_more
   $C run --rm --no-deps api python manage.py migrate integrations 0002_payments
   ```
3. `docker tag mda-api:rollback-$TS mda-api && $C up -d --no-deps api celery celery-beat` (and roll back `web` as in R1).
4. `$C exec -T api python manage.py showmigrations integrations platform` should show `0002` and `0018` as the heads.
5. Remove the added `SMS_CREDITS_ENFORCED` line from `.env.cloud`; the old code ignores it anyway.

**R3. Anything else, or new-feature data exists.**

1. Stop `api`, `celery` and `celery-beat`.
2. Restore the pre-release dump with `pg_restore --clean --if-exists` into `mda_postgres` (per `RESTORE_DRILL.md`).
3. Retag the rollback images and start the old containers.

Any payment activity recorded after the backup must be reconciled by hand. A backup restored this soon should contain none.

**Never** start the old `mda-api` image against a migrated database. It cannot insert `SubscriptionPayment` or `SmsLog` rows (see §6).

## 10. Evidence (pre-release)

- **SQLite:** 134 focused tests passed, covering subscription checkout, superadmin bypass, the payment framework, SMS reseller, integration secrets, platform integrations and entitlements.
- **PostgreSQL 14:** `test_billing_postgresql.py` 6/6 and the payment-race tests in `test_branch_postgresql.py` 3/3.
- **Frontend:** vitest 192/192, and `tsc` plus the production build pass.
- **Migration chain:** applied cleanly on a *copy* of the local dev DB (the full chain, with 0 left pending), followed by `bootstrap_system`. All new permission codes were registered and the admin role holds them.
- **Production (read-only):** 0 unapplied migrations in the running image; exactly 2 new migrations in the release; 0 SMS providers; 0 payment providers; 0 Waafi-callback confirmations.

## 11. Open items (not blockers for this release)

- The real Safari payment provider needs its API and webhook-signing documentation, `INTEGRATION_ENCRYPTION_KEY`, and a platform decision to go live.
- Recommended guard: refuse MOCK as a billing provider in production.
- Not built: proration, yearly pricing and refunds (see `SUBSCRIPTION_AUTO_PAYMENT.md`).
- Tenant-custom roles need `billing.subscription.*` and `integrations.sms.billing.*` granted manually if those users need billing.

## 12. Deployed — 2026-09-23 (release tag `production-2026-09-23`)

**Status: DEPLOYED AND VERIFIED.** All seven deployment gates passed; no rollback required.

| Item | Value |
|---|---|
| Deployed API image | `mda-api:latest` — `8156dd21a027` |
| Deployed web image | `mda-web:latest` — `e3c08480d09f` |
| Migrations applied | `integrations.0003_sms_billing`, `platform.0019_subscription_checkout` (exactly the two planned; `migrate --check` exit 0) |
| Permission bootstrap | `bootstrap_system`, additive; `integrations.sms.billing.view/purchase` and `billing.subscription.view/pay` present |
| SMS policy | `SMS_CREDITS_ENFORCED=True` (reseller model, §8 step 4 recommendation) |
| DB backup | `backups/mda_erp_pre_release_20260923T163830Z.dump` — 3.0 MB, 5889 TOC entries, `pg_restore --list` verified |
| Rollback images | `mda-api:rollback-20260923T163830Z` (`c31be14d7211`), `mda-web:rollback-20260923T163830Z` (`e654b3d08a79`) |
| Services restarted | api, celery, celery-beat, web only. PostgreSQL, Redis, nginx, TLS and DNS untouched |

**Rollback assets must be retained** until the release is formally accepted.

### 12.1 Post-deployment observations (behaviour unchanged; recorded for future sessions)

- **`shop_group_manager` legitimately holds `platform.view`.** During smoke testing a tenant-scoped user returned `200` on `/api/v1/platform/tenants/`. This is **correct, not a leak**: the multi-shop manager role is granted `platform.view` by design. Re-testing with an ordinary tenant admin (role `admin`, no `platform.view`) correctly returned `403` on `/api/v1/platform/tenants/`, `/api/v1/platform/subscriptions/` and `/api/v1/platform/integrations/sms-providers/`. Any future tenant-isolation check must pick a user **without** `platform.view`, or it will report a false positive.
- **The SMS purchase fail-safe was verified at service level, not end to end.** Production has **0 SMS packages**, so `SmsPurchaseService.create()` short-circuits at "Package not available." before reaching the provider check. The guard itself was therefore verified directly: `SmsPurchaseService.billing_provider()` returns `None` under the production settings. Re-run the end-to-end path once a package exists.
- **Real provider (Hormuud) onboarding remains deferred.** No real payment adapter exists; MOCK is the only registered type and is blocked in production. Subscription checkout and SMS package purchasing continue to fail safely as "not available". `INTEGRATION_ENCRYPTION_KEY` is still unset in production and must be set — and backed up securely — before any real provider is configured.

### 12.2 Reproducibility

The deployed images were built from a working tree with 283 dirty paths on top of `3a90c8e`. That exact tree is captured by the release commit tagged `production-2026-09-23`. Intentionally excluded from that commit: `frontend/tsconfig.tsbuildinfo` (generated build cache) and `docs/school/verification/` (1.5 MB of test evidence — screenshots, regression logs, JSON). Neither affects the built images. Secrets (`backend/.env.cloud`) and `backups/` are gitignored and were never staged.
