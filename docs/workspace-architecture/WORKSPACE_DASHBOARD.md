# Workspace Dashboard

**Date:** 2026-08-08  
**Status:** Increment 1 — hub cards; increment 2 — per-workspace dashboards

---

## Hub (`/modules`) — Your Business Workspaces

Replace engine cards with industry cards:

```
┌───────────────────────────────┐
│ Restaurant                    │
│ Revenue        Orders         │
│ $4,250         184            │
│ POS · Sales · Inventory       │
│ Purchasing · Finance          │
│ Open Restaurant →             │
└───────────────────────────────┘
```

Live metrics come from existing summary APIs (`/restaurant/summary/`, `/gym/summary/`, `/sales/summary/`, …) — **KEEP** `useHubOverview`, re-key by industry code.

Cross-tenant KPIs on the hub (revenue today, cash, AR/AP) stay as the **Lifestyle Center** strip.

---

## Main dashboard (`/dashboard`)

**EXTEND** (not increment 1 rewrite): aggregate enabled workspaces.

```
Revenue Today
  Gym · Cafeteria · Total
Orders · Memberships · Inventory alerts
Cash · Receivables · Payables
Gym overview · Cafeteria overview
```

Widget registry already deep-links industry routes. Align copy with workspace names.

---

## Per-workspace dashboard

Each industry home (`/restaurant`, `/gym`, …) **is** the workspace dashboard today (tab shell). **KEEP** those pages.

Later: `/restaurant/dashboard` alias + dedicated KPI header; still no second POS/Sales implementation.

---

## Finance on a workspace

`/restaurant/finance` renders the **same** `FinancePage` (central CAE). Optional later: default `BusinessUnit` filter to `REST`. Increment 1 only sets workspace brand + nav context.
