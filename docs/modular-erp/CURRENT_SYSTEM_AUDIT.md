# Current System Audit — Modular Multi-Tenant ERP

**Date:** 2026-08-07  
**Phase:** Prompt §86 — analyze only  
**Scope:** Tenant, modules, presets, demos, nav, POS, verticals, accounting dimensions

---

## 1. Executive verdict

MDA already has a **real modular multi-tenant foundation**:

| Layer | Status |
|-------|--------|
| Shared-schema `Tenant` + domains + settings | **KEEP** |
| `Module` + `TenantModule` + `PlanModule` + entitlements | **KEEP / EXTEND** |
| `BusinessType` with `default_modules` | **EXTEND** (split preset out) |
| `ModuleGateMiddleware` + FE `useModules` | **KEEP / EXTEND** |
| Central Accounting Engine (`apps/finance`) | **KEEP** |
| Cost centers | **KEEP** |
| Gym / Pharmacy / Futsal apps | **KEEP / EXTEND** |
| Universal POS | **KEEP / EXTEND** |
| BusinessPreset | **CREATE** |
| Module dependencies / features | **CREATE** |
| DemoTenant engine | **CREATE** |
| Restaurant/Cafeteria Django app | **CREATE** (stub today) |
| Hotel / Property / Housing / Office | **CREATE** (future) |
| BusinessUnit | **KEEP** (PHASE 09) |
| Dynamic module switcher + composed dashboard | **CREATE** |

**Do not rebuild** platform, finance, gym, pharmacy, or POS. Extend them.

**Frontend is React/Vite**, not Next.js. Mobile: `mobile/gym-member/` exists.

---

## 2. Classification matrix

| Component | Path / notes | Action |
|-----------|--------------|--------|
| `Tenant`, `TenantDomain`, `TenantSettings` | `apps/platform/models/` | **KEEP** |
| Tenant status trial/active/suspended/cancelled | No `demo` | **EXTEND** |
| Host / subdomain resolver | `tenant_resolver.py` | **KEEP** |
| Onboarding wizard | `onboarding_service.py` + FE | **EXTEND** (add preset step) |
| `Module`, `TenantModule` | `models/module.py` | **KEEP** |
| `PlanModule` + `EntitlementService` | plan ∩ business defaults | **KEEP / EXTEND** |
| `BusinessType.default_modules` | overloaded as preset | **REFACTOR** → move to Preset |
| `BusinessPreset` | missing | **CREATE** |
| `ModuleFeature` / `TenantModuleFeature` | missing | **CREATE** |
| Module dependency engine | missing | **CREATE** |
| DemoTenantService + generators | only `seed_data --demo` | **CREATE** product; **KEEP** seed for local |
| Sidebar hardcoded + module filter | `Sidebar.tsx` | **EXTEND** |
| Module switcher | missing | **CREATE** |
| Main dashboard | retail KPIs | **EXTEND** widget registry |
| Universal POS | `apps/sales` + FE pos | **KEEP** |
| POSProfile model | settings JSON only | **EXTEND** → optional model |
| Gym | `apps/gym` | **KEEP / EXTEND** |
| Pharmacy | `apps/pharmacy` | **KEEP / EXTEND** |
| Futsal | `apps/futsal` | **KEEP** |
| Restaurant module code + RBAC | no `apps/restaurant` | **CREATE** app |
| Hotel / Property | absent | **CREATE** later phases |
| `CostCenter` | finance | **KEEP** |
| `BusinessUnit` | done | **KEEP** |
| Platform module APIs | catalog + tenant PUT | **KEEP**; wire FE UI |
| Platform modules admin UI | API unused in UI | **CREATE** screens |
| Finance as catalog module | always-on via perms | **EXTEND** optional `finance` module |
| Party / shared customer profiles | Customer only | **EXTEND** later |

---

## 3. What works today (do not duplicate)

### Tenant
- Provisioning, subdomain, settings, subscriptions, shop groups
- Auth payload includes `enabled_modules`

### Modules (codes seeded)
`pos`, `inventory`, `sales`, `purchases`, `pharmacy`, `restaurant`, `gym`, `futsal`

Gating: `ModuleGateMiddleware` → `MODULE_DISABLED` / `MODULE_DEPENDENCY` (required deps must also be enabled).

### Accounting
Full CAE: journals, mappings, posting rules, equation, maker-checker, cost centers, cutover.

### Verticals with real apps
Gym, Pharmacy (batch/FEFO), Futsal — all post or dual-write toward finance where wired.

---

## 4. Critical product gaps vs prompt

1. **BusinessType == Preset today** — `default_modules` on type must move to `BusinessPreset`.
2. **Restaurant is fake-complete** — module + waiter roles, no backend app / routes.
3. **No SaaS demo tenants** — `seed_data --demo` is local only.
4. **No dependency engine** — invalid combos possible if admin enables pharmacy without inventory.
5. **Nav not catalog-driven** — works but won't scale to Hotel/Property.
6. **Platform UI missing** module editor / presets / demos (APIs partially exist).
7. **Hotel / Property / Housing / Office** — greenfield CREATE phases after core module engine hardening.

---

## 5. First implementation slice (after docs)

See [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) PHASE 03–06:

1. Extend Module metadata (route, deps JSON, is_core)
2. Create BusinessPreset (+ migrate defaults off BusinessType)
3. Module dependency validation on enable
4. Platform admin: tenant modules UI
5. Then DemoTenant skeleton

**Do not start Hotel/Property until module/preset/demo spine is stable.**
