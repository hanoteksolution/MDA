# Shared Capabilities

## Rule

One engine, many **workspace profiles**. Never `RestaurantPOS` / `GymAccounting`.

| Capability | Django home | Profile / dimension |
|---|---|---|
| POS | `apps.sales.PosService` + `pos_profile.py` | RETAIL, SUPERMARKET, PHARMACY, CAFETERIA, RESTAURANT, GYM, HOTEL_SERVICE |
| Sales | Invoice, Quotation, Payment | `source_module` + BusinessUnit |
| Products | `apps.products` | Industry fields via attributes / overlays (MenuItem, ProductBatch, membership SKU) |
| Inventory | `apps.inventory` | FEFO via pharmacy batches |
| Purchasing | `apps.purchases` | Receive → stock (+ optional batch) |
| Customers / Suppliers | dedicated apps | Vertical parties may FK Customer |
| Payments | sales Payment + finance vouchers | CAE events |
| Finance | `apps.finance` | **one** CAE |
| Reports / Notifications / IAM / Tenant / Audit | dedicated apps | KEEP |

## Industry overlays (EXTEND, do not fork)

| Vertical | Overlay |
|---|---|
| Restaurant | MenuItem, DiningTable, RestaurantOrder → POS checkout |
| Pharmacy | ProductBatch FEFO, Prescription, dispense |
| Gym | Member, plans, attendance; checkout → Invoice + `post_gym_membership` |
| Hotel | Room, Reservation, Folio; charge-to-room → sales |
| Property | Asset/Unit + housing/office Lease → Invoice (`RentalBillingService`) |
| Futsal | Booking + `FutsalLedgerEntry` (**MIGRATE** onto Invoice + CAE BU map) |

## Product form profiles (target)

Base: name, SKU, category, price, cost, tax, unit, status.  
+ Pharmacy: generic, manufacturer, Rx flag, batch/expiry.  
+ Restaurant: recipe, modifiers, prep time, station (MenuItem or Product attributes).  
+ Gym: membership/service association.
