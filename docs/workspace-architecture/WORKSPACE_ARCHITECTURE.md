# Workspace Architecture

**Date:** 2026-08-08  
**Status:** Target — incremental, non-breaking  
**Product:** Safari ERP (MDA)

---

## Problem

The hub treats POS, Sales, Inventory, Purchases, Gym, Pharmacy, Restaurant, and Hotel as **equal top-level modules**. That is engine-centric, not industry-centric.

Users should enter a **business workspace** (Restaurant ERP, Gym ERP, Pharmacy ERP) and find POS / Sales / Inventory as **capabilities inside that workspace**. Shared engines must not be duplicated.

---

## Target shape

```
SAFARI ERP
│
├── CORE
│   ├── Dashboard · IAM · Users · Roles · Branches · Settings · Audit
│
├── CENTRAL ACCOUNTING ENGINE
│   └── CoA · Periods · Journals · GL · AR · AP · Cash · TB · P&L · BS · CF
│
└── BUSINESS WORKSPACES          ← user-facing top level
    ├── Restaurant / Cafeteria
    ├── Gym / Futsal
    ├── Pharmacy
    ├── Hotel
    ├── Property (Housing + Office as features)
    └── Retail
         └── each embeds: POS · Sales · Products · Inventory · Purchasing
                          Customers · Suppliers · Finance · Reports
                          + industry features (tables, batches, members, …)
```

---

## Principles

1. **Industry-centric UX.** Hub cards = business verticals, not engines.
2. **One implementation per engine.** Restaurant POS and Pharmacy POS are profiles of the same `PosService`.
3. **One accounting engine.** No RestaurantAccounting. Workspace → finance context → CAE → journals.
4. **Tenant-aware.** A tenant enables 1..N workspaces (e.g. Gym + Cafeteria).
5. **Do not rewrite working modules.** Classify KEEP / EXTEND / REFACTOR / MIGRATE / DEPRECATE, then ship incrementally.
6. **Row-level multi-tenancy stays.** Workspaces are rows/config inside a tenant, not new schemas.

---

## Layers

| Layer | What the user sees | What the platform is |
|---|---|---|
| Business workspace | Restaurant, Gym, Pharmacy… | Industry pack + nav + dashboard + brand |
| Capability | POS, Sales, Inventory… | Shared Django app / engine |
| Feature | Tables, Batches, Classes… | `TenantModule.configuration.features` |
| Core / platform | Admin, Settings, Subscriptions | IAM, tenant, audit |
| Central finance | Finance (one) | CAE + `BusinessUnit` dimension |

---

## Current vs target

| Today | Target |
|---|---|
| `TenantModule` industry codes sit beside `pos`/`sales` | Industry codes = workspace activation; `pos`/`sales`/`inventory`/`purchases` = engines |
| Hub `MODULE_WORKSPACES` is a flat 18-card list | Hub shows industry workspaces + Finance + Administration |
| Sidebar hard-codes POS next to Gym | Sidebar generated from workspace → capabilities + features |
| URLs `/pos`, `/gym` | URLs `/restaurant/pos`, `/gym/members` (aliases; engines unchanged) |
| Finance is permission-only, not a TenantModule | Still one CAE; optional later catalog as engine module |
| `BusinessUnit` (RETAIL/GYM/PHARM/…) is P&L only | Keep as accounting dimension mapped from workspace |

---

## Related docs

- [SHARED_CAPABILITY_ARCHITECTURE.md](./SHARED_CAPABILITY_ARCHITECTURE.md)
- [WORKSPACE_REGISTRY.md](./WORKSPACE_REGISTRY.md)
- [TENANT_WORKSPACE_ARCHITECTURE.md](./TENANT_WORKSPACE_ARCHITECTURE.md)
- [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md)
- [WORKSPACE_DASHBOARD.md](./WORKSPACE_DASHBOARD.md)
- [ACCOUNTING_INTEGRATION.md](./ACCOUNTING_INTEGRATION.md)
- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md)
