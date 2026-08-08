# Cross-Module Integration

**Date:** 2026-08-07  
**Status:** Design

---

## Patterns (KEEP where present)

| Pattern | Today | Target |
|---------|-------|--------|
| Accounting events | CAE posting service | EXTEND event types per vertical |
| Module gate | Middleware | KEEP |
| Notifications | Celery + module checks | EXTEND templates |
| Shared Customer | `apps/customers` | EXTEND profiles later |

---

## Party model (CREATE later)

```text
Party (person|company)
  → Customer role
  → GymMemberProfile
  → HotelGuestProfile
  → RentalTenantProfile
```

Avoid duplicating contact identity. Migrate carefully from Customer — do not big-bang rewrite.

---

## Integration examples

| Event | Consumers |
|-------|-----------|
| `GYM_MEMBERSHIP_SOLD` | CAE, notifications |
| `HOTEL_SERVICE_CHARGED` | Folio + CAE |
| `CAFETERIA_ORDER_PAID` | CAE, inventory |
| `RENT_INVOICE_GENERATED` | AR, notifications — **shipped** via housing/office charge invoice |
| Charge to room | Cafeteria POS → Hotel folio → one settlement |

Durable outbox already exists for sync — reuse patterns for critical cross-module events where needed.
