# Workspace Registry

**Date:** 2026-08-08  
**Status:** Target catalog (FE first; backend TenantModule codes stay)

---

## Two registries

| Registry | Purpose | Today |
|---|---|---|
| **Business workspace** | Industry the user opens | Split across `BusinessType`, `TenantModule` industry codes, hub `MODULE_WORKSPACES`, mobile nav |
| **Shared capability** | Engine embedded in a workspace | `Module` seeds `pos`, `inventory`, `sales`, `purchases` |

Finance / reports / IAM are **platform capabilities**, not industry workspaces.

---

## Business workspaces

| Code | Label | Activating TenantModule(s) | Tone | Home |
|---|---|---|---|---|
| `restaurant` | Restaurant | `restaurant` | amber | `/restaurant` |
| `cafeteria` | Cafeteria | `restaurant` + cafeteria POS profile / business type | amber | `/cafeteria` → restaurant engine |
| `gym` | Gym | `gym` | violet | `/gym` |
| `futsal` | Futsal | `futsal` | green | `/futsal` |
| `pharmacy` | Pharmacy | `pharmacy` | emerald | `/pharmacy` |
| `hotel` | Hotel | `hotel` | cyan | `/hotel` |
| `property` | Property | `property_management` (+ housing/office features) | teal | `/property` |
| `retail` | Retail | `pos` and/or `sales` and/or `inventory` when no venue, **or** always as retail pack | orange | `/retail` → `/retail/pos` |

Housing + office are **features of Property**, not top-level hub cards (sidebar still reaches `/property/housing`, `/property/office`).

---

## Capabilities (shared)

| Code | Engine module | Permission (typical) | Default embed in |
|---|---|---|---|
| `dashboard` | — | `dashboard.view` | all |
| `pos` | `pos` | `pos.access` | restaurant, cafeteria, pharmacy, gym, hotel, retail |
| `sales` | `sales` | `sales.view` | restaurant, cafeteria, pharmacy, gym, hotel, retail |
| `products` | `inventory` | `products.view` | restaurant, cafeteria, pharmacy, gym, retail |
| `inventory` | `inventory` | `inventory.view` | restaurant, cafeteria, pharmacy, gym, hotel, retail |
| `purchasing` | `purchases` | `purchases.view` | restaurant, cafeteria, pharmacy, hotel, retail |
| `customers` | `sales` | `customers.view` | restaurant, cafeteria, pharmacy, gym, hotel, retail |
| `suppliers` | `purchases` | `suppliers.view` | restaurant, cafeteria, pharmacy, hotel, retail |
| `finance` | (CAE, perm) | `finance.view` | all |
| `reports` | (perm) | `reports.view` | all |

---

## Industry features

| Workspace | Features (today or next) | Source |
|---|---|---|
| Restaurant / Cafeteria | tables, kitchen, recipes, modifiers, delivery, waiters | Restaurant app + POS profile; feature catalog **EXTEND** |
| Gym | members, memberships, attendance, trainers, classes, PT | `ModuleFeatureService` gym keys **KEEP** / **EXTEND** |
| Pharmacy | batches, expiry, prescriptions, dispensing | `ModuleFeatureService` pharmacy keys **KEEP** |
| Hotel | rooms, reservations, guests, front_desk, housekeeping, room_service | Hotel app; feature catalog **EXTEND** |
| Property | properties, units, tenants, leases, rent, maintenance, housing, office | three TenantModules **REFACTOR** → features |
| Futsal | courts, teams, bookings | Futsal app **EXTEND** |
| Retail | none required | engines only |

---

## Platform workspaces (not industry)

| Code | Home | Notes |
|---|---|---|
| `overview` | `/dashboard` | Cross-workspace KPIs |
| `finance` | `/finance` | Central accounting UI |
| `admin` | `/admin` | IAM |
| `settings` | `/settings` | Company / branches / POS profile |
| `platform` | `/platform` | Super-admin SaaS console |

---

## FE source of truth (increment 1)

`frontend/src/navigation/businessWorkspaces.ts`

Backend `MODULE_SEEDS` remains the entitlement catalog. Do not invent a second enablement system in the SPA.
