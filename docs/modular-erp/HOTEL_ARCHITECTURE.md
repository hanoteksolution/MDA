# Hotel Architecture

**Date:** 2026-08-07  
**Status:** CREATE skeleton + charge-to-room + folio settlement

---

## Scope

```text
Hotel → RoomType → Room
Reservation → Guest → Check-in → Folio (+ FolioLine)
POS Charge to Room → FolioLine (fnb)
Check-out → settle folio (Invoice/Payment + CAE) → room dirty
```

## Shipped

- Django app `apps.hotel` + API `/api/v1/hotel/`
- Models: RoomType, Room, Guest, Reservation, Folio, FolioLine
- Front desk: book / check-in / check-out / cancel; overlap guard on assigned rooms
- Folio opens on check-in with room-night charge; post extra lines via API
- **Charge to room:** `GET /hotel/folios/open/` + POS checkout `hotel_folio_id` → `fnb` line; invoice on-account
- **Folio settlement:** check-out requires `payment_method` when outstanding > 0
  - Pays linked POS invoices (`CUSTOMER_PAYMENT_RECEIVED`)
  - Creates paid room invoice for unlinked charges (`SALE_COMPLETED` + `HOTEL_ROOM_REVENUE`)
  - Folio `amount_paid` / `payment_method` / `settled_at`, then closed
- Housekeeping: dirty → vacant
- Module `hotel`, perms, BT/presets, demo seeder, FE `/hotel` settle dialog

## Still later

- Calendar / availability engine
- Partial payments / comps / split tender on folio
- Dedicated `HOTEL_ROOM_CHARGED` / `HOTEL_SERVICE_CHARGED` event builders (keys seeded; sales path used today)
- Rate plans, deposits, group bookings

## Cross-module

One Universal POS + central Invoice/Payment/CAE — no `HotelAccounting`.
