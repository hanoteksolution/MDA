# Hold / Reserve Design (STEP 03)

**Status:** STEP 12 wired — new holds reserve; legacy deducted holds unchanged (Option A)  
**Date:** 2026-08-07

---

## Current behavior (bug)

`PosService.hold` → `InvoiceService.create` with `status=on_hold` → `_apply_stock_for_create` → **deducts `Inventory.quantity`**.

`Inventory.reserved_quantity` and transaction types `reserve` / `unreserve` existed but were unused.

Impact:

- Held carts reduce sellable stock as if sold
- Cancelling/deleting a hold restores via sale-delete path (works, but semantics wrong)
- Concurrent POS can oversell relative to true available stock

---

## Target behavior (STEP 12)

```
HOLD
  → create Invoice(status=on_hold)
  → InventoryService.reserve_quantity per line
  → do NOT change Inventory.quantity

RESUME / CHECKOUT from hold
  → InventoryService.consume_reserved (unreserve + sale deduct)
  → or unreserve then apply new cart deltas

CANCEL hold
  → InventoryService.unreserve_quantity per line
  → soft-delete / cancel invoice without sale restock
```

`available_quantity = quantity - reserved_quantity` remains the POS availability metric.

---

## Primitives added (STEP 03)

In `apps/inventory/services/inventory_service.py`:

| Method | Effect |
|--------|--------|
| `reserve_quantity` | +reserved; InventoryTransaction `reserve` |
| `unreserve_quantity` | −reserved; InventoryTransaction `unreserve` |
| `consume_reserved` | unreserve then `apply_sale_delta(-qty)` |

Transfer / receiving interfaces:

- `apps/inventory/services/transfer_service.py` → STEP 11
- `apps/inventory/services/receiving_service.py` → STEP 11

---

## Migration of existing on-hold invoices

When STEP 12 ships:

1. Detect holds that already have `StockMovement` sale rows
2. Option A (safer): leave historical holds as “legacy deducted”; only new holds use reserve
3. Option B: for open holds, restock quantity and create matching reserve (one-time data fix)

Prefer Option A + feature flag `pos.hold_uses_reserve`.

---

## Tests required at STEP 12

- Hold does not reduce `quantity`, only increases `reserved_quantity`
- Checkout from hold consumes reserve exactly once
- Concurrent hold cannot reserve beyond available
