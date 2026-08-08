# Modular ERP — Documentation Index

**Date:** 2026-08-07  
**Status:** PHASE 01–02 audit complete (prompt §86). **No implementation in this phase.**  
**Stack reality:** Django + DRF + **React/Vite** (not Next.js) + React Native gym-member app.

---

## Conceptual hierarchy (non-negotiable)

```text
BUSINESS TYPE     → classification (what kind of org)
BUSINESS PRESET   → onboarding template (recommended modules)
SUBSCRIPTION      → entitlement (what is purchased)
MODULE            → installable capability
FEATURE           → capability inside a module
TENANT MODULE     → actually enabled for this tenant
BRANCH            → location
BUSINESS UNIT     → profitability / org dimension
COST CENTER       → accounting dimension (exists)
CENTRAL ACCOUNTING → financial source of truth
```

**Never merge** BusinessType ↔ Module ↔ Preset ↔ Subscription ↔ Branch ↔ BusinessUnit.

---

## Documents

| Document | Purpose |
|----------|---------|
| [CURRENT_SYSTEM_AUDIT.md](./CURRENT_SYSTEM_AUDIT.md) | What exists; KEEP/EXTEND/CREATE/DEPRECATE |
| [TENANT_ARCHITECTURE.md](./TENANT_ARCHITECTURE.md) | Tenant, domain, trial, demo status |
| [MODULE_ARCHITECTURE.md](./MODULE_ARCHITECTURE.md) | Module vs preset vs feature vs entitlement |
| [MODULE_REGISTRY.md](./MODULE_REGISTRY.md) | Target catalog + metadata |
| [MODULE_DEPENDENCIES.md](./MODULE_DEPENDENCIES.md) | Dependency engine design |
| [BUSINESS_PRESETS.md](./BUSINESS_PRESETS.md) | Presets; split from BusinessType |
| [DEMO_ACCOUNT_ARCHITECTURE.md](./DEMO_ACCOUNT_ARCHITECTURE.md) | Demo create / expire / convert |
| [ENTITLEMENTS.md](./ENTITLEMENTS.md) | PHASE 12 trial/demo vs paid plan caps |
| [DYNAMIC_NAVIGATION.md](./DYNAMIC_NAVIGATION.md) | Sidebar + module switcher |
| [NAVIGATION_SWITCHER.md](./NAVIGATION_SWITCHER.md) | PHASE 07 implementation note |
| [DASHBOARD_ARCHITECTURE.md](./DASHBOARD_ARCHITECTURE.md) | Main + module dashboards |
| [UNIVERSAL_POS_ARCHITECTURE.md](./UNIVERSAL_POS_ARCHITECTURE.md) | One POS + profiles |
| [GYM_ARCHITECTURE.md](./GYM_ARCHITECTURE.md) | Gym vertical |
| [PHARMACY_ARCHITECTURE.md](./PHARMACY_ARCHITECTURE.md) | Pharmacy vertical |
| [CAFETERIA_ARCHITECTURE.md](./CAFETERIA_ARCHITECTURE.md) | Cafeteria / restaurant gap |
| [HOTEL_ARCHITECTURE.md](./HOTEL_ARCHITECTURE.md) | Hotel (future CREATE) |
| [PROPERTY_MANAGEMENT_ARCHITECTURE.md](./PROPERTY_MANAGEMENT_ARCHITECTURE.md) | Shared property core |
| [HOUSING_RENTAL_ARCHITECTURE.md](./HOUSING_RENTAL_ARCHITECTURE.md) | Housing rental |
| [OFFICE_RENTAL_ARCHITECTURE.md](./OFFICE_RENTAL_ARCHITECTURE.md) | Office rental |
| [CROSS_MODULE_INTEGRATION.md](./CROSS_MODULE_INTEGRATION.md) | Events, Party, charge-to-room |
| [ACCOUNTING_INTEGRATION.md](./ACCOUNTING_INTEGRATION.md) | CAE + mappings + business units |
| [MOBILE_ARCHITECTURE.md](./MOBILE_ARCHITECTURE.md) | RN dynamic modules |
| [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) | Phased execution order |

Related existing docs (do not duplicate): `docs/MODULE_SYSTEM.md`, `docs/accounting/*`, `docs/MOBILE_ARCHITECTURE.md`, `docs/TARGET_ARCHITECTURE.md`.
