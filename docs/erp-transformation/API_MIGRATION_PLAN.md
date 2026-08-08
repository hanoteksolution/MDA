# API Migration Plan

**Base:** `/api/v1/` — keep. Do not introduce a parallel `/api/v2` until a breaking need exists.

## Compatibility

- Keep `/pos`, `/sales`, `/inventory` module gates.
- Add optional `?workspace=` or infer from `X-Workspace` / path later; increment 1 does not require it.
- Industry apps stay under `/api/v1/gym|pharmacy|restaurant|hotel|property|housing|office|futsal/`.

## Add (priority)

| Endpoint | Why |
|---|---|
| Restaurant menu category/item + table `GET/PATCH/DELETE /:id/` | Master CRUD |
| Hotel room type / room / guest `GET/PATCH/DELETE /:id/` | Master CRUD |
| Property owner/asset/building/unit/maint `GET/PATCH/DELETE /:id/` | Master CRUD |
| Housing/office tenant `GET/PATCH/DELETE` | Master CRUD |
| Gym subscription PATCH (notes/dates) | Lifecycle beyond freeze |
| `POST /finance/journal/:id/reverse/` | Accounting safe reverse |
| `POST/PATCH /finance/accounts/` | CoA CRUD |
| `GET /audit/logs/` | `audit.view` |
| `GET /platform/workspaces/` | Derived workspace serializer (no new table) |

## Fix

- Customer/supplier delete permission codes vs `customers.create` gate
- Expense dedicated retrieve if FE Detail is added
- Warehouse retrieve + delete/deactivate
- Pharmacy batch retrieve

## Response contract (KEEP)

`{ success, message, data }` + DRF pagination `{ count, results }` where lists already use it.

## AuthZ

Backend remains authoritative. Elevate only `is_elevated_admin`. ModuleGate + HasPermission stay.

## Mobile

Same endpoints. Staff nav catalog should switch to industry-first groups (see MOBILE_ARCHITECTURE).
