# Accounting Architecture

**Rule:** ONE Central Accounting Engine. No RestaurantAccounting / GymAccounting.

```
Workspace event (sale, membership, GRN, rent, expense, payment)
    → AccountingEvent (idempotent, source_module, BusinessUnit)
    → PostingRule / PostingService
    → JournalEntry + JournalLine (Dr = Cr)
    → GL / TB / P&L / BS / CF
```

Posted journals are **immutable**. Reverse = offsetting entry. Never casual delete.

## Live mapping (KEEP)

| Workspace | `source_module` | BusinessUnit |
|---|---|---|
| Retail / POS / Sales | pos / sales | RETAIL |
| Gym | gym | GYM |
| Pharmacy | pharmacy | PHARM |
| Restaurant / Cafeteria | restaurant | REST |
| Hotel | hotel | HOTEL |
| Property / housing / office | property* | PROP |
| Futsal | futsal | **unmapped — MIGRATE** |
| Admin / unassigned | finance | CORP (default) |

## KEEP

CoA, mappings, posting rules, journals, maker-checker, periods, BU, cost centers, AR/AP aging selectors, receipt + supplier payment vouchers, bank rec, equation health, gym/POS/pharmacy/futsal posting tests.

## EXTEND (do not fork)

- Stamp purchases / futsal / inventory adjust onto BU map
- `/journal/:id/reverse/` API
- CoA create/deactivate API
- Use `HOTEL_ROOM_CHARGED` / `RESTAURANT_ORDER_PAID` or keep via sales (document choice: **keep via sales Invoice**, stamp `source_module` from workspace)
- Move `sales.Expense` posting BU from always RETAIL → active workspace
- Workspace finance UI (`/gym/finance`) pre-filters BU (increment 2)

## Forbidden

Per-industry ledgers. Physical delete of posted JEs. Frontend-only “finance” numbers that bypass CAE.
