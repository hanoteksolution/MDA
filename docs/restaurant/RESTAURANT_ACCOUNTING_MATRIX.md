# RESTAURANT_ACCOUNTING_MATRIX

## Current Accounting Integration

Restaurant accounting currently flows through shared POS/Sales invoice posting:

- Restaurant order -> POS payload bridge
- POS checkout -> Sales invoice + payments
- Sales posting service -> central accounting journals

## Coverage Matrix

| Transaction | Current Path | Journal Integration | Status |
|---|---|---|---|
| Restaurant sale paid cash/card/mobile | POS checkout | Shared sales posting | PARTIAL |
| Restaurant sale on-account/AR | POS checkout with `on_account` | Shared sales posting | PARTIAL |
| Table order settlement | POS checkout with `restaurant_order_id` | Shared sales posting + order close | PARTIAL |
| Tax payable from sale | Shared sales posting | yes (shared finance) | PARTIAL |
| Inventory consumption from recipe | N/A | missing | MISSING |
| Purchase/receiving accrual for restaurant | shared purchasing generic | not restaurant-contextualized in workspace | PARTIAL |
| Waste valuation entry | N/A | missing | MISSING |
| Shift open/close/cash variance | shared cashier sessions for POS | not restaurant workspace workflow | PARTIAL |

## Gaps to Complete

1. Restaurant-specific accounting mapping keys/events for:
   - kitchen waste
   - recipe consumption COGS
   - table transfer/void/refund adjustments
2. Mandatory balance assertions for all restaurant financial workflows.
3. Restaurant finance dashboard/reporting with BU and cost center controls from CAE.

## Control Requirements

- Posted journal immutability preserved (already a shared engine rule).
- Reversal/void mechanisms must be used for corrections.
- All restaurant financial actions need explicit audit metadata (`reason`, actor, branch).
