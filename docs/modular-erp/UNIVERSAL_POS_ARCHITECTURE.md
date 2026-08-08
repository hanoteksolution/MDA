# Universal POS Architecture

**Date:** 2026-08-07  
**Status:** EXTEND — profile codes + pay-table + charge-to-room

---

## Rule

**One** POS engine (`apps/sales` + `/pos`). Never `PharmacyPOS` / `GymPOS` / `CafePOS` / `HotelPOS` as separate systems.

---

## Current (KEEP + PHASE 13 + hotel EXTEND)

- Checkout, tenders, holds, refunds → accounting events
- Settings JSON `pos_profile_{user}` + shop `pos.waiters`
- Profile **code** + **capabilities** inferred from enabled modules (`apps/sales/services/pos_profile.py`)
- Pharmacy FEFO / batch selection where pharmacy module enabled
- Waiter performance for cafeteria-style use without restaurant app
- **Pay table:** open restaurant order → hydrate POS cart → checkout with `restaurant_order_id` → order `paid` + table `free`
- **Charge to room:** pick in-house folio → checkout with `hotel_folio_id` / `charge_to_room` → folio `fnb` line; invoice on-account

---

## Profile codes

`RETAIL` · `SUPERMARKET` · `PHARMACY` · `CAFETERIA` · `RESTAURANT` · `GYM` · `HOTEL_SERVICE`

Inference (module order): `hotel`+(`restaurant`|`pos`) → HOTEL_SERVICE; `restaurant` → RESTAURANT; `pharmacy` → PHARMACY; `gym`+`pos` → GYM; else RETAIL.  
Hotel module always sets `charge_to_room` capability even on other profiles.  
Cashier settings may set an explicit code override.

| Profile | Capabilities |
|---------|----------------|
| PHARMACY | batch, expiry, Rx fields |
| CAFETERIA / RESTAURANT | tables, waiters, kitchen ticket (restaurant), modifiers |
| GYM | membership SKUs |
| HOTEL_SERVICE | charge to room / folio (+ tables when restaurant enabled) |

Still posts to central `Invoice` / `Payment` / CAE.

---

## Pay-table bridge

1. Floor UI lists open `RestaurantOrder`s (`GET /api/v1/restaurant/orders/`).
2. `GET /api/v1/restaurant/orders/<id>/pos/` ensures `MenuItem.product` (auto-create under “Restaurant Menu”) and returns POS line items.
3. `POST /api/v1/pos/checkout/` with `restaurant_order_id` after success calls `RestaurantService.update_order_status(…, paid)` which frees the dining table.

FE: POS top bar **Pay table** when `capabilities.tables` and restaurant module enabled.

---

## Charge-to-room bridge

1. `GET /api/v1/hotel/folios/open/?branch_id=` lists in-house open folios (hotel.view / front_desk / pos.access).
2. Cashier selects a room → FE sets `hotel_folio_id`.
3. `POST /api/v1/pos/checkout/` with `hotel_folio_id` (or `payment_method=charge_to_room`) maps payment to on-account, then `HotelService.charge_pos_sale_to_folio` posts an `fnb` folio line for the invoice total.

Guest settlement at hotel check-out: `POST /hotel/reservations/<id>/check-out/` with `payment_method` clears POS AR (`CUSTOMER_PAYMENT_RECEIVED`) and posts room charges as a paid invoice (`SALE_COMPLETED` / `HOTEL_ROOM_REVENUE`).
