# Workspace Architecture

See also `docs/workspace-architecture/`.

```
SAFARI ERP
│
┌─────────────┴─────────────┐
│                           │
PLATFORM                  CENTRAL FINANCE
IAM • Tenant • RBAC       Accounting Engine
Branch • Subscription     General Ledger
Audit • Settings          P&L • Balance Sheet
│
▼
        BUSINESS WORKSPACES
                 │
 ┌───────────────┼────────────────┐
 │               │                │
RESTAURANT      GYM           PHARMACY
 │               │                │
 Dashboard     Dashboard        Dashboard
 POS           Members          POS
 Sales         Memberships      Sales
 Products      Attendance       Medicines
 Inventory     Classes          Batches
 Purchasing    POS              Expiry
 Customers     Products         Inventory
 Suppliers     Inventory        Purchasing
 Kitchen       Sales            Prescriptions
 Tables        Finance          Finance
 Finance       Reports          Reports
 Reports
 │
 └───────────────┬────────────────┘
                 │
         SHARED ENGINES
                 │
  POS • Sales • Inventory • Purchasing
  Products • Customers • Suppliers
  Payments • Notifications • Reporting
                 │
                 ▼
        CENTRAL ACCOUNTING ENGINE
```

## Business workspace

User-facing industry pack: nav + dashboard + brand + feature set. Not a second schema.

| Code | Activating TenantModule(s) | Home |
|---|---|---|
| restaurant | `restaurant` | `/restaurant` |
| cafeteria | `restaurant` + cafeteria POS profile | `/cafeteria` |
| gym | `gym` | `/gym` |
| pharmacy | `pharmacy` | `/pharmacy` |
| hotel | `hotel` | `/hotel` |
| property | `property_management` ∪ housing ∪ office | `/property` |
| retail | engines when no venue vertical | `/retail` |
| futsal | `futsal` | `/futsal` |

Housing / Office = **features of Property**, not hub peers.

## Dynamic visibility

```
visible = tenant usable modules ∩ workspace map ∩ features ∩ user perms ∩ subscription
```

Switcher: industries + Central Finance + Administration. Never POS/Sales/Inventory as peers.

## URL

`/{workspace}/{capability|feature}`  
Examples: `/restaurant/pos`, `/gym/members`, `/pharmacy/batches`, `/hotel/housekeeping`.

Shared engine pages are **aliases** (`WorkspaceGate` + same `PosPage` / `SalesPage` / `FinancePage`).

## Increment status

| Item | Status |
|---|---|
| FE registry + hub + switcher + sidebar | Done |
| Alias capability routes | Done |
| URL → mega-page tab sync | This phase |
| Backend `TenantWorkspace` table | Deferred (derive from TenantModule) |
| Fine-grained `restaurant.products.create` perms | Later phase |
