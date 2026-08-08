# Migration Strategy

**Status:** Phase 0 — approved path before large refactoring  
**Date:** 2026-08-07  
**Rule:** Never risk existing shop data for architectural purity.

---

## 1. Goals

1. Move from hybrid branch-centric ERP → secure multi-tenant SaaS foundation
2. Preserve POS, sales, inventory adjustments, platform billing, desktop sync, futsal
3. Prefer additive migrations; avoid destructive renames
4. Every high-risk step has backup + rollback

---

## 2. Current state (migration baseline)

| Aspect | Today |
|--------|-------|
| Cloud DB | Shared PostgreSQL; incomplete tenancy |
| Desktop | Per-shop SQLite + sync_secret |
| Tenant model | Exists (`tenants`, subscriptions) |
| Operational data | Mostly **not** tenant-scoped |
| Unique keys | Global SKU/barcode/codes |
| Payments | Encoded in `Invoice.notes` |
| Isolation | Physical (desktop DB) or social (single shop cloud) |

---

## 3. Tenant isolation decision

### Preferred long-term (master prompt)

PostgreSQL **schema-per-tenant**.

### Immediate recommendation

**Do not migrate production to schema-per-tenant in the first transform wave.**

Reasons:

- Existing cloud data and desktop sync assume shared tables
- Platform KPIs/snapshots query shared schema
- Schema-per-tenant requires migration runners, per-tenant migrate orchestration, and restore drills we do not have yet
- Shared-schema + `tenant_id` delivers security faster with lower cutover risk

### Staged isolation plan

| Stage | Approach | Exit criteria |
|-------|----------|---------------|
| **A0** | Inventory & backup all environments | Documented restore test |
| **A1** | Add nullable `tenant` FKs; backfill | **done** (unit DB); verify 100% on staging Postgres |
| **A2** | Service `apply_tenant_scope` + API `user=` wiring (manager enforcement still opt-in) | **done** — `test_tenant_isolation.py` green |
| **A3** | Make `tenant` non-null; composite uniques | Partial: composite uniques added; NOT NULL deferred |
| **B** | Optional schema-per-tenant pilot | One pilot tenant only |
| **C** | Broader schema-per-tenant | Only if ops ready |

---

## 4. Backup & rollback strategy

### Before any migration wave

1. PostgreSQL logical dump (`pg_dump`) + retain checksum
2. For VPS: follow `docs/deployment/HOSTINGER_VPS.md` backup scripts if present
3. Snapshot desktop sync secrets / connection configs (ops runbook)
4. Tag git release: `pre-tenant-isolation-YYYYMMDD`

### Validate backup

A backup is invalid until **restore into a scratch database** and smoke-test:

- login
- product list
- POS checkout (staging)
- platform tenant list

### Rollback patterns

| Change type | Rollback |
|-------------|----------|
| Additive nullable columns | Deploy previous app; columns unused |
| Backfill scripts | Re-run corrected backfill; avoid destructive UPDATE without WHERE tenant |
| NOT NULL / new uniques | Restore DB snapshot if deploy fails |
| Middleware | Feature-flag middleware; disable to last-known-good |
| Schema-per-tenant | Keep shared schema until dual-write verified |

Prefer **expand → migrate → contract** over big-bang drops.

---

## 5. Data backfill strategy (Stage A1–A3)

### Ownership rules

1. Prefer `Company.tenant` → all branches → warehouses → inventory/docs under that company
2. Users with `User.tenant` already set — verify consistency with company
3. Orphan rows (no company/branch path): assign to a dedicated `legacy-unassigned` tenant and flag for ops review — **do not delete**
4. Products/categories/brands/suppliers with no branch: attach to tenant of the only company if single-tenant DB; else `legacy-unassigned`

### Unique constraint migration

Example product SKU:

1. Add `tenant` FK nullable
2. Backfill
3. Add unique `(tenant_id, sku)` **concurrently** where possible
4. Drop old `sku` unique
5. Set `tenant` NOT NULL

Same pattern: barcode, customer_code, supplier_code, brand name (or allow global brand catalog later — product decision).

### Desktop hybrid

Desktop DBs remain single-tenant. Sync layer stamps cloud writes with the authenticated sync tenant (`tenant_slug` + `sync_secret`, constant-time compare). Pull is tenant-scoped; push skips foreign SKUs and stamps `tenant_id` on customers/invoices/inventory. Connection save verifies via `/sync/shop-verify/`.

---

## 6. Domain / subdomain migration

### Phase order

1. Implement `TenantDomain` model + resolver service (API still works via JWT tenant)
2. Add middleware that sets tenant from host **when present**
3. Keep JWT user.tenant as secondary check (must match host tenant unless platform admin)
4. Configure DNS `*.erp.safaritechno.com`
5. Frontend: derive API base / branding from host; no client-trusted tenant id

### Reserved slugs

Block: `www`, `api`, `admin`, `app`, `support`, `billing`, `mail`, `static`, `platform`, `erp`, …

---

## 7. Application migration waves

Aligned with roadmap; each wave: analyze → small change → migrate → test → document.

| Wave | Focus | Risk |
|------|-------|------|
| 0 | Audit + docs (this phase) | None |
| 1 | Core hygiene (payments model design, hold/reserve fix plan) | Low |
| 2 | Tenant FKs + middleware + tests | **High** (security) |
| 3 | Business types + modules + feature flags | Medium |
| 4 | RBAC expansion | Low–med |
| 5 | Catalog attributes | Medium |
| 6 | Inventory receiving/transfers | Medium |
| 7 | POS payments/sessions/refunds | **High** (money) |
| 8 | Pharmacy | Medium |
| 9 | Gym vertical | Medium |
| 10 | Finance foundation | High |
| 11 | Notifications + Celery | Low–med |
| 12 | Onboarding UX | Medium |
| 13 | Frontend polish | Low |
| 14 | Mobile API hardening | Medium |
| 15 | Offline sync foundation (real queue) | High |
| 16 | Schema-per-tenant evaluation | High |

**Do not** start Gym/Pharmacy before Wave 2 exit criteria.

---

## 8. API contract policy

- Prefer additive fields; deprecate with sunset notes
- Do not rename POS checkout payload keys without versioned dual support
- Introduce `/api/v1/` error envelope standardization gradually:

```json
{
  "success": false,
  "code": "MEMBERSHIP_EXPIRED",
  "message": "Membership has expired.",
  "details": {}
}
```

- Breaking changes require migration guide + frontend simultaneous deploy for SPA

---

## 9. Frontend migration policy

| Option | Decision |
|--------|----------|
| Rewrite to Next.js now | **Rejected** for Wave 0–7 |
| Keep Vite React SPA | **Accepted** |
| Introduce Next.js marketing site later | Optional parallel |
| Module-aware nav / tenant branding | Incremental in SPA |

---

## 10. Database migration mechanics

- One Django migration per logical change; avoid squash until stable
- Use `RunPython` for backfills with reverse noop or safe reverse
- For large tables: batched updates (e.g. 1k–5k rows)
- Always run `manage.py check` + migrate on staging clone first
- Composite indexes for `(tenant_id, created_at)`, `(tenant_id, branch_id, status)`, etc., based on measured queries

---

## 11. Tenant provisioning (target)

```
Create account → Create business → Select business type
  → Choose subdomain → Choose plan → Provision tenant
  → Seed roles/settings → Create first branch/warehouse
  → Dashboard
```

Provisioning must be idempotent (retry-safe). Schema-per-tenant provisioning is a later variant of the same pipeline.

### Deletion / archive

- Soft-suspend on subscription expiry (existing `is_usable` / grace pattern)
- Do **not** hard-delete tenant data on expiry
- Archive workflow: disable login → export → retention policy → hard delete only with dual control

---

## 12. Testing gates (mandatory)

Before declaring Wave 2 done:

- [ ] Tenant A cannot `GET/PATCH` Tenant B product/invoice/customer by UUID
- [ ] Sync with Tenant A secret cannot write Tenant B catalog
- [ ] Platform admin paths still work
- [ ] POS checkout stock + invoice integrity
- [ ] Desktop provision smoke test

Before Wave 7 (POS payments):

- [ ] Split tender totals == invoice total
- [ ] Concurrent checkout cannot oversell (locking test)
- [ ] Hold reserve does not double-deduct

---

## 13. Schema-per-tenant (future playbook outline)

Only after Stage A exit:

1. Create `public` control tables (already mostly there)
2. Provision schema + run tenant migrations
3. Dual-read feature flag
4. Copy tenant rows with ID preservation
5. Dual-write period
6. Cut read path
7. Stop dual-write; archive shared rows

Rollback: flip read path to shared schema.

---

## 14. Communication & stop points

After each major wave:

1. Update `CURRENT_SYSTEM_AUDIT.md` status section or changelog
2. Update ERD
3. Summarize completed work and **stop** before the next major domain (e.g. do not silently start Gym mid-inventory)

---

## 15. Explicit non-actions (now)

- No mass model renames
- No deletion of futsal/POS
- No Next.js greenfield
- No React Native app scaffolding
- No schema-per-tenant production cutover
- No dropping `Invoice.notes` until Payment rows backfilled

---

*Companion: [TARGET_ARCHITECTURE.md](./TARGET_ARCHITECTURE.md), [ERP_TRANSFORMATION_ROADMAP.md](./ERP_TRANSFORMATION_ROADMAP.md).*
