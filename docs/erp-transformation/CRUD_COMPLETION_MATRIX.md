# CRUD Completion Matrix

**Legend:** Y = done · I = inline on list (no dedicated `/new` or `/edit` route) · W = workflow only · P = partial · — = missing · N/A = not applicable (report/ops)

Dedicated Detail pages are almost universally **—** (except platform tenant/shop). Target: add Detail for master data after List/Create/Update are solid.

## Shared engines

| Workspace | Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|---|
| Retail/All | Product | Y | Y | P | Y | Y (soft) | P | Y | Y |
| Retail/All | Category | Y | I | — | I | I | — | Y | P |
| Retail/All | Brand | API Y | API Y | — | API Y | API Y | — | Y | P |
| Retail/All | Unit | Y | — | — | — | — | — | — | — |
| Retail/All | Warehouse | Y | **FE this phase** | — | API Y / FE — | — | — | P | P |
| Retail/All | Stock | Y | Restock D | — | Adj | N/A | N/A | Y | Y |
| Retail/All | Adjustment | Y | I | — | — | — | — | Y | Y |
| Retail/All | Transfer | API Y | API Y | API Y | confirm/cancel | — | — | Y | P |
| Retail/All | Customer | Y | Y | P | Y | Y | — | P (no delete code) | P |
| Retail/All | Supplier | Y | Y | P | Y | Y | — | P | P |
| Retail/All | Invoice | Y | Y | D print | Y | Y | Trash | Y | P |
| Retail/All | Quotation | Y | Y | D | Y | Y | — | Y | — |
| Retail/All | Receipt | Y | via POS | D | via invoice | — | — | Y | P |
| Retail/All | Expense | Y | I | — | I | I | — | Y | P |
| Retail/All | Purchase Order | Y | Y | P | Y | Y | — | P | Y |
| POS | Checkout/Holds | Y | Y | Receipt | Hold resume | — | — | Y | Y |

## Finance (CAE)

| Entity | List | Create | View | Update | Delete | Workflow | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Chart of Accounts | Y | API — / FE — | P | — | deactivate — | — | view | Y seed |
| Journal | Y | **FE this phase** (API Y) | expand | draft only | discard draft | post / self-approve | view/create/approve | Y |
| Period | Y | auto | Y | — | — | close/lock/reopen | Y | Y |
| Cost center / BU | API L+C | API C | — | — | — | — | P | Y |
| Receipt voucher | — | API POST | — | — | — | — | Y | Y |
| Supplier payment | — | API POST | — | — | — | — | Y | Y |
| Bank rec | Y | I | Y | match | — | complete | Y | Y |
| Reverse posted JE | — | service only | — | — | **never** | **API missing** | — | Y service |

## Gym

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Member | Y | I | P | I | I | — | gym.manage | Y |
| Plan | Y | I | — | I | I | — | gym.manage | Y |
| Subscription | Y | I sell | — | — | — | freeze/cancel/pay | gym.manage | Y |
| Attendance | Y | check-in W | — | check-out W | — | — | checkin | Y |
| Trainer | Y | I | — | I | I | — | gym.manage | P |
| Class / Schedule / Booking | Y | I | — | P | cancel W | — | gym.manage | Y |
| Workout stack | Y | I | P | P | — | — | gym.manage | P |

## Pharmacy

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Medicine (Product) | Y | Y | P | Y | Y | P | products.* | Y |
| Batch | Y | **FE this phase** (API Y) | — | — | — | — | pharmacy.manage | Y |
| Prescription | Y | I | — | — | — | dispense W | pharmacy.dispense | Y |
| Dispense | via Rx | W | — | — | — | — | dispense | Y |

## Restaurant / Cafeteria

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Menu category | Y | I | — | **API —** | **API —** | — | restaurant.manage | P |
| Menu item | Y | I | — | **API —** | **API —** | — | restaurant.manage | P |
| Table | Y | I | — | status W / **U/D API —** | **API —** | — | floor/manage | P |
| Order | Y | I | Y | status W | — | — | floor | P |
| Kitchen | **tab this phase** | N/A | queue | status | — | — | kitchen | — |

## Hotel

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Room type | Y | I | — | **API —** | **API —** | — | manage | P |
| Room | Y | I | — | status W | **API —** | — | housekeeping/manage | P |
| Guest | **no page** | on reservation | — | **API —** | **API —** | — | manage | P |
| Reservation | Y | I | folio | check-in/out/cancel W | — | cancel | front_desk | Y |
| Folio | open list | charge W | Y | settle W | — | — | front_desk | Y |

## Property / Housing / Office

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Owner / Asset / Building / Unit / Maint / Doc | Y | I | — | status W / **U/D API —** | **API —** | — | *.manage | P |
| Housing/Office tenant | Y | I | — | **API —** | **API —** | — | *.manage | P |
| Lease | Y | I | Y | activate/terminate W | — | terminate | *.manage | Y |
| Lease charge | Y | I | — | invoice/paid W | — | — | *.manage | Y |

## Futsal

| Entity | List | Create | View | Update | Delete | Archive | Perms | Tests |
|---|---|---|---|---|---|---|---|---|
| Court / Team / Player / Booking | Y | I | — | I (API Y) | I (API Y) | — | futsal.manage | P |
| Ledger | Y | I | — | — | — | — | futsal.finance | Y CAE |

## Admin / Platform

| Entity | List | Create | View | Update | Delete | Notes |
|---|---|---|---|---|---|---|
| User / Role / Branch | Y | Y | — | Y | deactivate | KEEP |
| Tenant / Shop / Demo / Plan | Y | Y | **Detail Y** | Y | platform | KEEP |

---

## Priority backlog (implementation order)

1. URL → tab sync (workspace IA actually works) — **this phase**
2. FE Create where API already exists: Warehouse, Journal, Pharmacy batch — **this phase**
3. Restaurant kitchen tab + hotel housekeeping tab — **this phase**
4. Vertical master-data PATCH/DELETE APIs (menu, table, room, guest, property, lease tenant)
5. Dedicated `/new` + `/edit` + `/ :id` Detail shells for gym members, hotel reservations, property units
6. CoA write API + deactivate; journal reverse API
7. Fine-grained permissions + audit write on all mutations
8. FE automated tests + E2E CRUD flows
