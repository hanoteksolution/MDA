# Reports, Dashboards and Alerts by Branch — Phase 6

Companion to `BRANCH_TEST_MATRIX.md` §6 and `BRANCH_POS_FINANCE.md`. Reuses `core/branching.py`
scope resolution, `BranchFinanceService`'s "Unassigned" rule and `NotificationService`.

## 1. Report scope

`apps/reports/services/branch_report_service.py`

* `resolve_report_scope(request)` → `ReportScope(branch_ids, mode, covers_all)`. Input is `branch_id`
  (query) or `X-Branch-Id`: one id (**single**), a comma list (**multi**), or `all`/nothing
  (**consolidated** = every branch the caller holds `reports.view` in). Any id outside that set — another
  branch, another tenant's branch, or one bad id in a list — is a **403**, never an empty success and never
  silently dropped. `all` never widens beyond the caller's branches.
* `BranchReportService.run(report, scope, date_from, date_to)` for `sales`, `stock-value`, `profit-loss`,
  `cash`. Each returns per-branch rows, a `consolidated` block, and `reconciles`.
  **Hard gate B6-2:** `consolidated` comes from an independent aggregate (no GROUP BY), not from summing
  the rows, so `reconciles` compares two real computations. P&L adds an `unassigned` bucket (journal lines
  with no branch, plan §4.6) only for a full consolidated view by a caller who sees every branch;
  consolidated = Σ branches + Unassigned.
* Endpoint: `GET /api/v1/reports/branch/<report>/?branch_id=…&date_from=&date_to=`.
* Figures: sales = gross / refunded / net of non-draft, non-hold, non-cancelled invoices; stock value =
  on-hand × cost price by warehouse branch (in-transit is not included — it is on the transfer, D5); P&L =
  posted revenue/expense lines by `JournalLine.branch`; cash = cash tenders − refunds + paid-in − paid-out,
  plus shift variance.

**Existing single-branch reports and dashboards** (`/reports/data|export|chart|sales-print`, every
`/dashboard/*` view) now go through `resolve_view_branch_id`: no selection keeps today's default (the
user's own branch); a named branch must be accessible (403); `all` is honoured only for callers who can see
every branch (else 403). Those services still take one branch, so a limited user cannot ask for a multi-branch
dashboard — they get a 403 rather than a silently different number.

## 2. Notifications / alert centre

`Notification` gained `branch`, `severity` (INFO/WARNING/CRITICAL), `entity_type`, `entity_id`,
`audience` (USER/BRANCH/BRANCH_MANAGERS/TENANT), `expires_at`, `action_url` (migration
`notifications/0004`, all optional — every existing caller is unchanged). New type `cash_variance`.

* `NotificationService.notify_branch(branch, permission=…, managers_only=…, dedupe_key=…)` — the audience is
  users who really hold the permission **in that branch** (`has_branch_permission`), never a tenant broadcast.
* Feed: `GET /notifications/?branch_id=&severity=` (403 for a branch you cannot access); expired alerts are
  hidden; branch-less alerts stay visible.
* **Once per event (B6-6):** every alert has a `dedupe_key` per recipient — low stock `low_stock:<inventory>`
  (24 h, so a still-low product re-alerts daily, not every scan), transfer `branch_transfer:<request>:<event>`
  and cash variance `cash_variance:<session>` (both effectively permanent, so replays never storm).
* Sources: low-stock scan (per branch, CRITICAL when out of stock), transfer events (severity WARNING for
  rejected/cancelled), cash variance on shift close → that branch's managers only.

## 3. MIG-5

`AuditLog.branch` shipped in M1 and stays **forward-only**: historical rows keep NULL and are never
back-dated (that would falsify the audit trail); new rows take the entity's own branch, or none.

## 4. Known limits

* No frontend work: the matrix has no FE row for Phase 6 and the existing alert/notification screens read the
  unchanged fields.
* `covers_all` compares against the tenant's active branches; a branch added later immediately shrinks
  "everything" for a user who was not granted it.
* Existing vertical report packs (gym, hotel, …) still take one branch; only the four reports above are
  multi-branch.
