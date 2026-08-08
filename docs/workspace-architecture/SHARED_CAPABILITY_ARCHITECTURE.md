# Shared Capability Architecture

**Date:** 2026-08-08  
**Status:** Target — engines stay singleton

---

## Rule

Do **not** create RestaurantPOS, GymSales, PharmacyInventory, HotelFinance.

Build **one engine**, many **workspace profiles**.

```
Shared POS Engine
  ├── Restaurant POS profile
  ├── Cafeteria POS profile
  ├── Pharmacy POS profile
  ├── Retail / Supermarket POS profile
  ├── Gym POS profile
  └── Hotel POS profile (charge-to-room)
```

---

## Engine map (live code)

| Capability | Django home | Key types / services | Verdict |
|---|---|---|---|
| POS | `apps.sales` (`PosService`, `pos_profile.py`) | Profiles: RETAIL, SUPERMARKET, PHARMACY, CAFETERIA, RESTAURANT, GYM, HOTEL_SERVICE | **KEEP** |
| Sales | `apps.sales` | `Invoice`, `Payment`, `Quotation`, `InvoiceService` | **KEEP** |
| Products / catalog | `apps.products` | `Product`, `Category`, attributes | **KEEP** |
| Inventory | `apps.inventory` | `Warehouse`, `Inventory`, movements, FEFO via pharmacy batches | **KEEP** |
| Purchasing | `apps.purchases` | `PurchaseOrder` + receive | **KEEP** |
| Customers | `apps.customers` | Shared CRM; vertical parties optionally FK | **KEEP** / **EXTEND** unification |
| Suppliers | `apps.suppliers` | AP master | **KEEP** |
| Payments | sales `Payment` + Waafi/EVC platform | | **KEEP** |
| Finance / CAE | `apps.finance` | `AccountingEvent`, journals, periods, `BusinessUnit` | **KEEP** — one engine |
| Reports | `apps.reports` + vertical packs | | **KEEP** / **EXTEND** bind to workspace |
| Notifications | `apps.notifications` | | **KEEP** |
| IAM / tenant / audit | authentication, platform, audit | | **KEEP** |

---

## How verticals already use engines

| Vertical | POS | Sales / Invoice | Inventory | Finance CAE `source_module` |
|---|---|---|---|---|
| Restaurant | Floor → `PosService.checkout` | Yes | MenuItem → Product | restaurant → BU `REST` |
| Pharmacy | Rx gate + FEFO POS | Yes | `ProductBatch` on Product | pharmacy → `PHARM` |
| Gym | Membership SKUs | `GymPaymentService` → Invoice | Optional retail SKUs | gym → `GYM` |
| Hotel | Charge to folio / room-night SKU | `HotelSettlementService` | Optional F&B | hotel → `HOTEL` |
| Property / housing / office | No POS | `RentalBillingService` → Invoice | No | property → `PROP` |
| Futsal | Weak (retail profile) | **Parallel `FutsalLedgerEntry`** | No | futsal (outlier) |
| Retail | Universal POS | Yes | Yes | retail → `RETAIL` |

**Futsal ledger:** **MIGRATE** onto Invoice + CAE when touched; do not duplicate a second books system.

---

## Profile vs fork

POS already infers profile from enabled modules (`backend/apps/sales/services/pos_profile.py`). Workspace context should **select or pin** that profile (query `?workspace=restaurant` or path `/restaurant/pos`) instead of forking checkout.

Inventory / purchasing / customers stay tenant-scoped. Workspace is a **nav + posting dimension**, not a second stock table.

---

## Central accounting (non-negotiable)

```
Restaurant POS checkout
    → Invoice + Payment
    → AccountingEvent(source_module=restaurant, business_unit=REST)
    → PostingService → JournalEntry
    → one Chart of Accounts / one GL
```

Same path for Gym, Pharmacy, Hotel, Property. See [ACCOUNTING_INTEGRATION.md](./ACCOUNTING_INTEGRATION.md).
