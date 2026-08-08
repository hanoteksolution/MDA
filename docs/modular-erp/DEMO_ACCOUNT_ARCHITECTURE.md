# Demo Account Architecture

**Date:** 2026-08-07  
**Status:** Implemented (PHASE 10–11) — gym/pharmacy seeders produce real rows

---

## Goal

Platform admins create **demo tenants** with module presets, sample data, expiration, and convert-to-customer.

---

## Seeders

| Module | File | Data |
|--------|------|------|
| gym | `apps/platform/demo/gym.py` | 2 plans, 5 members, active subs, check-ins |
| pharmacy | `apps/platform/demo/pharmacy.py` | 3 medicines, FEFO batches (near/far/expired) |
| restaurant | `apps/platform/demo/restaurant.py` | menu, tables, open ticket |
| hotel | `apps/platform/demo/hotel.py` | room types, rooms, booked + in-house |
| property_management | `apps/platform/demo/property.py` | owner, asset, building, units, maintenance |
| housing_rental | `apps/platform/demo/housing.py` | lease + deposit/rent charges on residential unit |
| office_rental | `apps/platform/demo/office.py` | commercial lease + service charge |

Demo create marks `is_demo` then re-runs `apply_plan_entitlements` (PHASE 12 trial/demo rule keeps preset modules without a separate starter ∩ workaround).

API: `/api/v1/platform/demo-tenants/`  
UI: `/platform/demos`

---

## Classification

| Piece | Action |
|-------|--------|
| DemoTenantService | **CREATE** ✓ |
| Gym/Pharmacy seeders | **CREATE** ✓ |
| Restaurant seeder | after app CREATE |
| Expire Celery job | schedule `expire_due` later |
