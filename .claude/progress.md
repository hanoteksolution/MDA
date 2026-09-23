# ACTIVE TASK

<!-- Session-resume anchor. Read this FIRST, before anything else in this file.
     Update it after every meaningful step. Keep it short — it is read by every
     new session. One task at a time; append finished work to the sections below. -->

Task: Production deployment — Platform Admin separation + SMS Reseller + Subscription Auto-Payment + School frontend restructure
Status: PASS
Last completed step: Gate 7 — all 7 gates passed; release live and smoke-tested on 20260923T163830Z
Exact next step: None. Release is live. NOT committed/tagged (user has not authorized). Keep rollback assets until the release is accepted. Optional: commit/tag the deployed tree (it is currently only reproducible from the dirty working tree).
Last command/result: `migrate --check` exit 0, 0 unapplied; smoke — superadmin platform 200, ordinary tenant platform 403, School sis/summary 200, inventory/branches 200, sms-billing 200, waafi-callback 410, subscription checkout "not available yet", 0 tracebacks/5xx in 10m
Production changes made: Applied `integrations.0003_sms_billing` + `platform.0019_subscription_checkout`; ran `bootstrap_system` (additive); appended `SMS_CREDITS_ENFORCED=True` to `backend/.env.cloud`; rebuilt and recreated api/celery/celery-beat/web from the working tree
Services restarted: api, celery, celery-beat, web (recreated). PostgreSQL and Redis NOT touched. Nginx NOT touched. TLS/DNS NOT touched.
Migrations applied: integrations.0003_sms_billing, platform.0019_subscription_checkout (exactly the 2 planned)
Blocker: None

Deployed images: mda-api:latest `8156dd21a027`, mda-web:latest `e3c08480d09f` (built from dirty tree at git SHA 3a90c8e, 283 dirty paths — NOT reproducible from git alone).
ROLLBACK ASSETS — DO NOT DELETE: DB dump `backups/mda_erp_pre_release_20260923T163830Z.dump` (3.0M, 5889 TOC entries, pg_restore --list verified); env `backups/env.cloud.20260923T163830Z` (mode 600); images `mda-api:rollback-20260923T163830Z` (c31be14d7211), `mda-web:rollback-20260923T163830Z` (e654b3d08a79). Rollback procedure: PRODUCTION_RELEASE_PLAN.md §9.
Production billing state: 0 payment providers; PAYMENT_ALLOW_MOCK_PROVIDERS=False live; MOCK selection blocked and MOCK runtime resolution -> None; subscription checkout and SMS purchase fail safely. SMS_CREDITS_ENFORCED=True. 0 SMS packages configured.

Previous task (TLS wildcard) — PASS 2026-09-22, untouched by this deploy. Rollback: old SAN cert `/etc/letsencrypt/live/erp.safaritechno.com/`; nginx `/root/nginx-erp-conf.bak.20260922-135754`; crontab `/root/crontab.bak.20260922-135822`.

---

# Current Development State

**2026-09-23 ERP subscription checkout + verified activation — see `docs/branches/SUBSCRIPTION_AUTO_PAYMENT.md`.** Checkout → SubscriptionPayment + house-tenant sales Invoice + PaymentIntent; ONLY the verified webhook settlement (`PaymentService._settle` → `SubscriptionBillingService.on_intent_settled`) activates/renews, once. Unsigned Waafi callback retired (410); manual confirm = reason-required audited recovery, refused for checkout rows. Migration `platform/0019_subscription_checkout`; perms `billing.subscription.view|pay` (re-run bootstrap). Proration/yearly billing = documented gaps. PG 14 concurrency suite `tests/unit/test_billing_postgresql.py` 6/6 (also closes SMS credit-lock PG gap). No real provider adapter (MOCK only).

**2026-09-23 SMS reseller packages & credits — see `docs/branches/SMS_RESELLER_BILLING.md`.** Platform packages + billing provider; tenant purchase (idempotent) credited ONLY via the verified payment webhook (hook in `PaymentService.process_event`), exactly once (DB-unique lot/entry); immutable `SmsCreditEntry` ledger with expiring lots; SMS reserve-on-accept / charge-on-SENT / release-on-FAILED; never negative; audited platform adjustments. Migration `integrations/0003_sms_billing`; new perms `integrations.sms.billing.view|purchase` (re-run bootstrap on deployed DBs); `SMS_CREDITS_ENFORCED` (default True, False in test settings). Subscription auto-payment NOT started.

**2026-09-23 Platform Integrations separation — COMPLETE.** SMS/payment provider config, credentials, webhook events and reconciliation are now Platform Admin only (`/api/v1/platform/integrations/*`, guard `api/v1/integrations/platform_access.py`, explicit `tenant_id`); old tenant management routes removed; tenant keeps templates/logs/send/intents + public signed webhook. UI: `/platform/integrations` (elevated-only) reusing existing integrations views; tenant Settings → Integrations is operations-only. Architecture/encryption unchanged. Doc: `docs/branches/PLATFORM_INTEGRATIONS.md`. Reseller packages NOT started.

**2026-09-23 School frontend restructure — COMPLETE (frontend only, no backend changes, no new phase).** Grouped, permission-filtered School sidebar (`frontend/src/navigation/schoolNavigation.ts`, collapsible groups via `layouts/Sidebar/SidebarSection.tsx`); SIS list/detail/form rebuilt on PageLayout + DataTable + status badges + row menus + appDialog; real-data School dashboard and Admissions overview; foundation pages moved filters into the DataTable toolbar; `sis/Nav.tsx` and `SchoolAcademicNav.tsx` removed. Vitest 176/176 (31 new), `npm run build` PASS, mocked-API Chromium smoke PASS. Backend gaps and remaining work: `docs/school/SCHOOL_FRONTEND_RESTRUCTURE.md` §5/§9 (Phase 3/4 Playwright scripts need updating for in-app confirm dialogs).

**2026-09-22 Superadmin subscription-bypass fix — COMPLETE.** Continued Codex's interrupted work in-place (no revert/restart). Codex's real fix, preserved as-is: `EntitlementService.write_blocked_for_request` (`backend/apps/platform/services/entitlement_service.py`) now calls `is_platform_unscoped_actor(user)` unconditionally after resolving the user (whether from `request.user` or JWT), closing a gap where a JWT-only-authenticated Superadmin could be write-blocked; `api/v1/sync/views.py::SubscriptionStatusView` exempts `is_platform_unscoped_actor` before touching `ShopSyncService`; frontend `SubscriptionAlertDialog`/`SubscriptionPaywallBanner` skip loading/rendering when `isElevatedUser(user)` (`frontend/src/navigation/postLogin.ts`, pre-existing helper). Verified — separately from subscription bypass — that Platform Administration authorization (`api/v1/platform/views.py::_platform_user`/`_subscriptions_user`, checked via `is_platform_admin` / `platform.view` / `subscriptions.manage` permissions) and tenant-scoped integration permissions (`integrations.manage` etc., via `HasPermission`) are permission-gated, never subscription-gated — an active or expired tenant subscription cannot change platform-API or provider-config access either way. Added 6 backend tests to `backend/tests/unit/test_superadmin_subscription.py` (18/18 pass, incl. Codex's original 12) proving: Superadmin with zero tenant/subscription reaches `/api/v1/platform/tenants/` (200); tenant admin with active or expired subscription gets 403 on both `/api/v1/platform/tenants/` and the platform billing/subscription-update endpoint; ordinary write-lock enforcement (`/api/v1/pos/checkout/` → `SUBSCRIPTION_EXPIRED`) still works. Added 2 frontend tests to `frontend/src/navigation/postLogin.test.ts` for `isElevatedUser` (11/11 pass). Related pre-existing suites unaffected: `test_entitlements_step24/41.py` + `test_elevated_admin_access.py` 15/15 pass. Pre-existing, unrelated: `frontend/src/pages/auth/OnboardingPage.tsx` has a `tsc` unused-import error (`workspaceHttpsUrl`) — not touched, out of scope.

**2026-09-21 School update:** Phase 4 remains **SIGNED OFF / PASS with 0 new regressions**. **School Phase 5 PASS**: assignments/submissions, weighted assessments, moderated publication, immutable report versions, promotion preview/commit. Targeted SQLite **22 passed**; PostgreSQL **24 passed** (concurrency/migration included); frontend **128 passed**; Chromium/production build/security/isolation/migrations **PASS**. Single final backend regression: **889 passed, 43 skipped, 7 failed, 9 errors**; exact failure/error names match the Phase 4 final baseline, **0 new regressions**. Evidence: [Phase 5 report](../docs/school/SCHOOL_PHASE_5_IMPLEMENTATION.md), [exact regression comparison](../docs/school/verification/phase5-regression-comparison.json). Preserve School Phases 1–4 and completed Branch/Integrations. **STOP at Phase 5; Phase 6 NOT STARTED and requires separate authorization.** **2026-09-22: Phase 6 subsequently authorized and in progress; fee/shared-billing implementation complete; targeted financial regression 69 passed, final School 21 passed, PostgreSQL 23 passed, frontend 133 passed plus 5 route checks, production build and Chromium PASS. Complete backend regression/exact baseline comparison pending. Stop at Phase 6; do not start Phase 7.**

Last updated: 2026-09-21 (Phase 9 complete; reservation gap fixed)

## Current Task

ERP-wide Multi-Branch foundation, 9 phases, gated. **All 9 phases are done; Phase 9 (regression/concurrency/browser/security) is verified and awaiting the user's review.** Do not resume School work (`apps/school`) — paused indefinitely per the original brief.

## Completed Work (by phase)

- **Phase 1** — audit + architecture. Docs: `MULTI_BRANCH_ARCHITECTURE.md`, `BRANCH_MIGRATION_PLAN.md`, `BRANCH_TEST_MATRIX.md`. Decisions D1–D9 confirmed by user.
- **Phase 2** — branch core, RBAC, warehouses/locations. `core/branching.py`, `apps/organization` app, `Branch` extended in place, `AuditLog.branch`. Doc: `BRANCH_AUTHORIZATION.md`.
- **Phase 3** — branch-aware inventory, stock ledger. `StockMovement`/`InventoryTransaction` gained branch/location; `apps/inventory/services/branch_stock_service.py` (aggregation, cross-branch availability); `inventory.cross_branch_view` permission. Doc: `BRANCH_INVENTORY.md`.
- **Phase 4** — inter-branch transfer workflow. `apps/inventory/models/transfer.py` (`BranchTransferRequest`/`Line`, `ReplenishmentRule`); `apps/inventory/services/branch_transfer_service.py` (REQUESTED→APPROVED→RESERVED→(DISPATCHED)→IN_TRANSIT→RECEIVED→COMPLETED, plus REJECTED/CANCELLED); `StockTransferService.confirm` now rejects cross-branch pairs (D4). Doc: `STOCK_TRANSFER_WORKFLOW.md`.

- **Phase 5** — POS terminals/registers/shifts + finance branch dimension. `CashierSession` = the shift (terminal/register/warehouse/location/cash_in/out/variance approval); `Invoice.terminal/warehouse`; `CashierSessionService.{open_session,close_session,record_cash_movement,approve_variance,checkout_context}`; a branch with an active terminal cannot sell without an open terminal shift (branches with none keep legacy behaviour). `JournalLine.branch` stamped in `JournalService.create_entry` (per-branch balance + tenant validation); `BranchFinanceService` (per-branch/Unassigned/consolidated TB + equation, `reconciles` flag); transfers post balance-sheet-only entries (1210 Inventory in Transit, unit cost fixed on `BranchTransferLine.unit_cost`); receiving warehouse must match PO branch; `DocumentSequenceService.allocate` savepoint fix (PG). Migrations `sales/0009-0010`, `finance/0010-0011`, `inventory/0007`. FE: `modules/pos/utils/checkoutGuard.ts` + `hooks/usePosShift.ts`. Doc: `BRANCH_POS_FINANCE.md`.

- **Phase 6** — reports/dashboards/alerts by branch. `apps/reports/services/branch_report_service.py` (`resolve_report_scope`, `resolve_view_branch_id`, `BranchReportService` for sales/stock-value/profit-loss/cash with independent consolidated + `reconciles`); `GET /reports/branch/<report>/`; classic report + all dashboard views now validate branch (403). `Notification` gained branch/severity/entity/audience/expires_at/action_url (`notifications/0004`), `NotificationService.notify_branch`, low-stock scan/transfer/cash-variance alerts branch-scoped and deduped. Doc: `BRANCH_REPORTS_NOTIFICATIONS.md`.

- **Phase 7** — SMS framework, new app `apps/integrations` (migration `0001`). Fernet credential store (`crypto.py`, `INTEGRATION_ENCRYPTION_KEY`, comma-separated for rotation, no key = refuses to work), `SmsProvider/Template/Log`, adapters `MOCK` + `CUSTOM_HTTP` only (https, SSRF guard, no redirects), `SmsService.{send,enqueue,dispatch,retry_due}` (enqueue/dispatch_safe never raise; bounded retry 4 attempts, 1/5/30 min; terminal SENT/FAILED; secrets scrubbed), API `/integrations/*`, perms `integrations.view|manage|sms.send`, Celery tasks + 5-min beat. Doc: `BRANCH_SMS_FRAMEWORK.md`. Phase 8 payments should reuse the credential store and the failure-isolation contract.

- **Phase 8** — payment framework in `apps/integrations` (migration `0002_payments`). `PaymentProviderConfig/Intent/WebhookEvent/ReconciliationRecord`, adapters `providers/payment_{base,mock}.py` (MOCK only, D7), `services/payment_service.py` (`PaymentService`, `ReconciliationService`), API in `api/v1/integrations/payment_views.py`, perms `integrations.payments.view|collect|reconcile`, beat `integrations.expire_payment_intents`. Invoice settles only in `PaymentService._settle`, from an HMAC(timestamp.body)-verified webhook (±5 min); intents idempotent on `(tenant,key)`; events on `event_id` + intent state under row lock; unverified events stored raw, inert; discrepancies become `ReconciliationRecord`s, never auto-fixed. Helper `tests/helpers/payment_factory.py`. Doc: `BRANCH_PAYMENT_FRAMEWORK.md`; matrix §8 all PASS.

- **Phase 9** — verification only, plus SEC-5 fixes. Full regression SQLite and PG 14: 890 collected, 12 failed / 9 errors identical to baseline, PG 0 skipped. New tests: `tests/integration/test_branch_isolation_sweep.py` (8) and `test_branch_walkthrough_api.py` (1). The sweep found 4 horizontal leaks, fixed: branch transfers list/detail/actions (`branch_transfer_service._visible_to`), `CashierSessionService.list`, SMS/payment provider list + patch (`api/v1/integrations/views.py: visible_providers/provider_or_404`). SEC-4 clean. Matrix §9 has per-row status and findings.

Each phase's completion report was delivered to the user in the PASS/FAIL format they specified and is not repeated here — see conversation history if needed.

## Important Decisions / Known Limitations

- D1–D9 (Phase 1) govern all later phases — see `MULTI_BRANCH_ARCHITECTURE.md` §4.
- Inventory balance stays `(product, warehouse)` only — never re-key to include location or branch.
- **Reservation invariant gap — FIXED 2026-09-21 (see section below; text kept for history):** `InventoryService.apply_sale_delta` (the direct, no-hold sale path used by sales/restaurant/pharmacy) never reads `reserved_quantity`. A direct sale can reduce on-hand under an active transfer's reservation. `dispatch_reserved` fails safely (raises) rather than oversells, but the business invariant isn't 100% guaranteed. Do not fix by modifying Sales/POS without explicit instruction — documented in `STOCK_TRANSFER_WORKFLOW.md`.
- `StockTransfer` same-branch guard (D4) is code-level only (branch equality check in `confirm()`), not a DB constraint — cheaper, sufficient, deliberate.
- PostgreSQL 14 is available in this environment: `DJANGO_SETTINGS_MODULE=config.settings.branch_verification`. All required PG concurrency tests must actually pass on PG, never just skip on SQLite — a skip is a gate failure per D9.

## Files Currently Relevant

- Docs: `docs/branches/{MULTI_BRANCH_ARCHITECTURE,BRANCH_MIGRATION_PLAN,BRANCH_TEST_MATRIX,BRANCH_AUTHORIZATION,BRANCH_INVENTORY,STOCK_TRANSFER_WORKFLOW}.md` — read the relevant one(s) before touching related code; do not rewrite unless instructed.
- Backend: `apps/inventory/{models,services}/*`, `apps/organization/*`, `core/branching.py`, `apps/notifications/*`, `apps/sales/services/{cashier_session_service,pos_service,sales_service}.py`, `apps/finance/services/{journal_service,branch_finance_service,posting_service}.py`.
- Tests: `tests/unit/test_branch_{scope,rbac,core,locations,audit,ledger,stock_views,transfer,notifications,postgresql,pos,purchases,finance}.py`, `tests/integration/test_branch_isolation_api.py`, `tests/verification/test_branch_migration.py`, `tests/helpers/branch_factory.py`.

## Tests / Results

- Full backend regression after Phase 8: **12 failed, 9 errors**, identical names to Phases 5–7 (all pre-existing). Phase 8 new tests: 63 on SQLite (`test_payment_framework` 52, `test_integration_secrets` +3 SEC-3, existing 8) and 3 B8-4/B8-3 threaded tests in `test_branch_postgresql.py`; 82 passed, 0 skipped on PostgreSQL 14 for those three files.
- (Earlier) full backend regression after Phase 7: **12 failed, 9 errors** — identical names to Phases 5/6 (School SIS ×5, pharmacy FEFO ×3, tenant slug, `accounting_alerts_step35`, `backfill_health_step35`, `demo_tenant_step39`; tenant isolation ×3 + performance step31 ×6 errors). All pre-existing. (`-q` prints no pass totals.)
- Phase 7 new tests: 42 (`test_sms_framework`, `test_integration_secrets`), green on SQLite and PostgreSQL 14 (`config.settings.branch_verification`). The PG run found and fixed a `select_for_update` outer-join error in `SmsService.dispatch`; the two files were re-run on both DBs after the fix, the full regression ran just before that one-line fix.
- Frontend untouched in Phase 7. Test runs are slow (~4 min DB setup each) — batch them.

## Unresolved Issues

- Pre-existing baseline failures (see above) — never touch these; they predate this project and are out of scope.
- Phase 7: no business event sends SMS yet (only the framework + API); `INTEGRATION_ENCRYPTION_KEY` must be set in every environment that stores credentials; `CUSTOM_HTTP` SSRF check has no DNS pinning; delivery is at-least-once.
- **Behaviour change to flag:** the M4 backfill creates `POS-1`/`REG-1` for every branch with POS history, which switches on terminal enforcement there — cashiers must open a shift before selling after migrating. Branches with no terminal are unchanged.
- Hold→checkout across different warehouses is now covered by `test_hold_checkout_on_terminal_touches_only_the_terminal_warehouse` (PASS): default-warehouse reservation released, deduction and refund only in the terminal warehouse.
- A short transfer receipt leaves the shortfall in 1210 Inventory in Transit; no write-off posting exists (business decision).
- `frontend/src/modules/school/sis/config.ts` has a pre-existing TS error that fails `npm run build`'s `tsc` step; unrelated, not fixed.

- Phase 8 limits: only MOCK provider; no real-provider adapter; no refund/chargeback modelling; no frontend for payments (frontend must poll the intent, never trust a callback); idempotency keys are per tenant; `expires_at` late-success is flagged for reconciliation, not auto-settled. Running `makemigrations integrations` also emitted an unrelated `sales/0011` (pre-existing model drift: `created_at`/`id`/`tenant` alterations) — it was not kept; the drift remains.

## Reservation gap — FIXED 2026-09-21

`InventoryService.apply_sale_delta` (`inventory_service.py`) clamps deductions at `min(reserved_quantity, on_hand)`; returns (delta>0) are never clamped and an already-under-reserved row is never raised (earlier working-tree clamp could have added stock — corrected). `consume_reserved` unreserves first, so it still sells its own reservation. Tests: `test_inventory_reserve.py` +3 (SQLite), `test_branch_postgresql.py::test_direct_sale_cannot_consume_transfer_reserved_stock` strengthened (asserts qty 0, no sale movement); PG14 run of postgresql+transfer files (-k reserv/sale/transfer/dispatch) green, 0 skipped. No full regression re-run (single-function change). Supersedes the "Reservation invariant" notes above.

## Integrations UI + provider handoff docs — DONE 2026-09-21

Frontend is React/Vite (not Next.js). Route `/settings/integrations` (+ `/<ws>/settings/integrations`), gated `integrations.view` or `integrations.payments.view`; entry button on SettingsPage. Code: `frontend/src/modules/settings/integrations/` (`lib.ts` pure logic, `credentialFlow.ts`, `useLoad.ts`, `components/{primitives,views,forms}.tsx`, `IntegrationsPage.tsx`), API client `services/api/integrations.ts`. Tests `integrations/__tests__/` (70; vitest include widened to `*.test.{ts,tsx}`, SSR `renderToStaticMarkup`, no new deps). Full frontend `vitest` 117/117 and `npm run build` pass. Not viewed in a real browser. Docs in `docs/integrations/` (SMS + payment requirements, provider handoff = external; adapter guide = internal, lists framework gaps in §7). No backend changes.

Backend gaps found (documented, not built): no provider delete/template edit endpoints; no test-connection or provider-targeted test SMS; no transactions endpoint (UI derives from succeeded intents); lists capped at 200 with only `status` filter; no provider-type/config-schema discovery; intents show invoice id only (no number); SMS delivery receipts not ingested; payment webhook signature scheme fixed; payment `validate_config` not called by API; one secret string per credential; no real provider adapters.

## Exact Next Step

Branch Phases 1–9 closed out 2026-09-21 (final review done). Await user sign-off; no further phase. Open gaps: BR-1/BR-2 real-browser walkthrough not performed (no browser runner; API-level walkthrough only); `npm run build` blocked by the pre-existing School `tsc` error; M8 constraint tightening not written (later release). Do not resume School work.

## School Phase 4 gate — SIGNED OFF 2026-09-21

PASS (`docs/school/SCHOOL_PHASE_4_IMPLEMENTATION.md`). The first full regression found two Phase 4 regressions in `test_school_sis.py` (over-broad cross-campus check in `ops_integrity.validate_ops`), fixed by limiting it to Phase 4 models. The final full SQLite regression (`docs/school/verification/phase4-final-regression.txt`) has 7 failed / 9 errors, identical by exact node ID to the known baseline debt (accounting alerts, backfill health, demo tenant, pharmacy FEFO x3, tenant slug; tenant isolation x3, performance step31 x6): 0 new regressions. PostgreSQL/browser/frontend not re-run (the fix only narrows a check to the Phase 4 models those runs already exercised). Ready for Phase 5 but NOT started; it needs separate authorization.
