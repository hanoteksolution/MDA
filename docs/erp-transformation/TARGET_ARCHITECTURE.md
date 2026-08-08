# Target Architecture

**Date:** 2026-08-08

```
SAFARI ERP
├── CORE          IAM · Users · Roles · Branches · Settings · Audit
├── CENTRAL ACCOUNTING ENGINE     one books, many BusinessUnits
└── BUSINESS WORKSPACES           user-facing industries
      Restaurant / Cafeteria / Gym / Pharmacy / Hotel
      Property (+ Housing / Office features) / Retail / Futsal / Supermarket
           └── shared capabilities: POS · Sales · Products · Inventory
               Purchasing · Customers · Suppliers · Finance · Reports
           └── industry features: tables, batches, members, rooms, leases…
```

## Non-negotiables

1. Do not rebuild. Do not fork POS/Sales/Inventory/Finance per industry.
2. Business Type is descriptive. Authorization = `tenant.has_workspace(X)` + entitlements + RBAC.
3. Preset applies once → tenant owns `TenantModule` + features.
4. Every posted financial event: double entry, Dr = Cr, Assets = Liabilities + Equity.
5. Posted journals are immutable; reverse/void, never unpost-delete.
6. Tenant isolation on every query.
7. Complete CRUD = DB + API + UI + validation + permissions + audit + tests.

## UX contract

Restaurant must feel like Restaurant ERP. Gym like Gym ERP. Underneath: shared engines + industry profile + feature flags.

## Stack stay

Keep Django + Vite React. Do not migrate to Next.js in this programme. RN consumes the same `/api/v1`.
