# Implementation Roadmap — Modular ERP

**Date:** 2026-08-07  
**Status:** Binding order after PHASE 01–02 audit docs

Stack: Django + DRF + React/Vite (+ RN). Extend `apps/platform` / vertical apps — do **not** create parallel ERP.

---

## Phase status

| Phase | Name | Status |
|-------|------|--------|
| 01–02 | System + tenant audit | **DONE** (this folder) |
| 03 | Module registry metadata EXTEND | **DONE** |
| 04 | Tenant module engine harden + platform UI | **DONE** (shop Modules tab) |
| 05 | Module dependencies | **DONE** |
| 06 | Business presets (split from BusinessType) | **DONE** (preset model + seed; type JSON kept for back-compat) |
| 07 | Dynamic navigation + module switcher | **DONE** |
| 08 | Dashboard widget framework | **DONE** (registry + module cards + finance KPI strip) |
| 09 | BusinessUnit engine | **DONE** (model + seed + journal stamp + P&L/GL filter + API) |
| 10–11 | Demo tenant + modular seeders | **DONE** (gym/pharmacy seed real rows) |
| 12 | Subscription ↔ module entitlement polish | **DONE** (trial/demo bypass paid starter caps) |
| 13 | Universal POS profiles | **DONE** (profile codes + restaurant pay-table) |
| 14 | Gym EXTEND features/demo | **PARTIAL** (PT + class drop-in billing; base KEEP) |
| 15 | Cafeteria/Restaurant **CREATE** app | **DONE** (skeleton: menu/tables/orders) |
| 16 | Pharmacy EXTEND | **PARTIAL** (CAE + Rx + POS + FEFO + categories + features; base KEEP) |
| 17 | Hotel **CREATE** | **DONE** (skeleton + charge-to-room + folio settle) |
| 18 | Property core **CREATE** | **DONE** (assets/buildings/units/maintenance) |
| 19 | Housing rental **CREATE** | **DONE** (leases on PropertyUnit) |
| 20 | Office rental **CREATE** | **DONE** (commercial leases on PropertyUnit) |
| 21–23 | Cross-module + CAE mappings + reporting | continuous |
| 24 | RN dynamic modules | **PARTIAL** (member nav + staff switcher gym/pharmacy/hotel/restaurant/property/housing/office) |
| 25–28 | Security, perf, tests, production migration | continuous |

---

## Immediate next implementation slice

1–14. ~~Earlier modular ERP slices through Housing~~ ✓
15. ~~Office rental leases~~ ✓
16. ~~Hotel charge-to-room (POS → folio)~~ ✓
17. ~~Hotel folio settlement at check-out~~ ✓
18. ~~Housing/Office lease charge → Invoice/CAE~~ ✓
19. ~~Hotel/Restaurant/Property report packs~~ ✓
20. ~~BusinessUnit P&L dimension (PHASE 09)~~ ✓
21. ~~Gym PT service billing → Invoice/CAE~~ ✓
22. ~~Pharmacy POS → PHARMACY_SALE_COMPLETED / PHARM BU~~ ✓
23. ~~Gym class drop-in billing → Invoice/CAE~~ ✓
24. ~~Dashboard widget registry (PHASE 08)~~ ✓
25. ~~Finance cross-module dashboard KPIs~~ ✓
26. ~~Pharmacy prescriptions thin MVP (list/create/dispense)~~ ✓
27. ~~RN dynamic modules — mobile_nav bootstrap + gym-member gated Home~~ ✓
28. ~~Pharmacy Product.requires_prescription + POS Rx gate~~ ✓
29. ~~Pharmacy Rx FEFO dispense + quantity remaining caps~~ ✓
30. ~~Pharmacy demo seeder Rx rows (DEMO-RX-001/002)~~ ✓
31. ~~RN staff mobile_nav audience + workspace switcher app~~ ✓
32. ~~Pharmacy Rx partial-fill UI + scheduled demo expire~~ ✓
33. ~~RN staff hotel + restaurant workspaces~~ ✓
34. ~~Module dependency gate polish (checklist 9–11)~~ ✓
35. ~~Pharmacy categories UX (inventory Category filter + demo Analgesics/Antibiotics)~~ ✓
36. ~~RN staff property + housing + office workspaces~~ ✓
37. ~~Pharmacy module features (`batches`, `prescriptions`, `expiry_alerts`)~~ ✓

**Next:** Futsal staff workspace — **or** gym module features (`members`, `classes`, `attendance`).

**Stop before:** inventing a second Property/Building stack.

---

## Execution rule (per phase)

```text
ANALYZE → DESIGN → DB → BACKEND → API → FE → (RN) → CAE → PERMS → TESTS → DOCS → VERIFY
```

Do not start the next major vertical until the current phase is stable.

---

## Non-negotiables checklist (prompt §88)

Tracked against audit:

| # | Requirement | Today |
|---|-------------|-------|
| 1–3 | One / many modules; demo combos | Partial (modules yes; demo SaaS no) |
| 4 | Demo data by module | Partial (gym/pharmacy/hotel/… seeders; pharmacy includes Rx) |
| 5–8 | Module dashboards / switcher / dynamic nav | Partial (widget registry + module cards yes) |
| 9–11 | URL gate + deps + perms | **Done** (enable-time expand + runtime `MODULE_DEPENDENCY`) |
| 12 | Subscription modules | Yes (PlanModule) |
| 13–18 | Vertical independence | Gym/Pharmacy/Futsal yes; others no |
| 19–23 | Together + POS + CAE + BU P&L | Partial (CostCenter + BusinessUnit yes) |
| 24–25 | Demo expire/convert | **Done** (API + platform UI + scheduled `expire_demo_tenants`) |
| 26–28 | Isolation / mobile / extensibility | Isolation yes |

---

## Related

- Index: [README.md](./README.md)
- Accounting: `docs/accounting/`
- Legacy module note: `docs/MODULE_SYSTEM.md` (superseded in detail by this folder; keep as short ops reference)
