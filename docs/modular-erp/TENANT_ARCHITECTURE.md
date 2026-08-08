# Tenant Architecture

**Date:** 2026-08-07  
**Status:** Design — extends existing `apps/platform`

---

## Existing (KEEP)

| Model | Role |
|-------|------|
| `Tenant` | Business account; FK `business_type`; status active/trial/suspended/cancelled |
| `TenantDomain` | Host / subdomain binding |
| `TenantSettings` | POS defaults, branding, accounting flags |
| `TenantSubscription` | Plan + trial/active/expired |
| Resolver | Host → tenant context (never trust FE alone) |

Paths: `apps/platform/models/tenant.py`, `tenant_config.py`, `services/tenant_resolver.py`.

---

## EXTEND — classification vs capability

```text
Tenant.primary_business_type  → BusinessType (classification only)
TenantModule                  → capabilities (authoritative)
Subscription / PlanModule     → entitlement ceiling
```

**Wrong:** `if tenant.business_type == "gym": allow_gym()`  
**Right:** `if tenant.has_module("gym"): allow_gym()`

Optional later: `TenantBusinessType` M2M for multi-sector orgs (`is_primary`).

---

## EXTEND — demo lifecycle

Add (or use TenantSettings flags) without breaking existing statuses:

| Field | Notes |
|-------|-------|
| `is_demo` | bool |
| `demo_status` | ACTIVE / EXPIRED / SUSPENDED / CONVERTED |
| `trial_start` / `trial_end` | already partially via subscription |
| `converted_from_demo_at` | audit |

Policy: expired demos → read-only or login blocked; **never auto-delete journals**.

---

## Onboarding (EXTEND)

```text
Business info
  → Business Type (classification)
  → Recommended Presets
  → Select Preset OR Custom modules
  → Validate dependencies
  → Select features (later)
  → Branches / currency / CoA
  → Admin user
  → Provision (sync TenantModule snapshot from preset)
```

Preset application **copies** module list into `TenantModule`. Later preset edits must not mutate existing tenants.

---

## Domain resolution (KEEP)

```text
Host header → TenantDomain → Tenant → enabled modules → permissions → ERP
```

Documented in `docs/DOMAIN_MANAGEMENT.md`.
