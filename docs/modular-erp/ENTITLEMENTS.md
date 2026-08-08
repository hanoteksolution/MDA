# Entitlement ↔ Module Polish (PHASE 12)

**Date:** 2026-08-07  
**Status:** Done

---

## Rules

| State | Module enablement |
|-------|-------------------|
| No subscription | Business type / preset defaults |
| **Trial** or **demo** | Business type / preset defaults (no plan ∩ strip) |
| Paid active/expired | Business defaults ∩ plan `PlanModule` inclusions |

Starter plan catalog stays retail-core (`pos`, `inventory`, `sales`, `purchases`).  
Business / enterprise include gym, pharmacy, futsal, restaurant.

`plan_includes_module` returns true for trial/demo so `tenant_has_module` is gated by `TenantModule` only during trials.  
Runtime API/nav also requires `tenant_module_ready` (enabled + required dependencies).

---

## Seed sync

`ensure_default_plan_modules` upserts `included=True` (restores soft-disabled default links) and refreshes enterprise to the full `MODULE_SEEDS` catalog.

---

## Demo create

After marking `is_demo`, re-runs `apply_plan_entitlements` so the demo rule is authoritative (no separate preset re-apply hack required for trial).
