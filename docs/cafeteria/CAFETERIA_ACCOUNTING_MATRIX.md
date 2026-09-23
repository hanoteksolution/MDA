# Cafeteria + Barista — Accounting Matrix

**Date:** 2026-09-06  
**Rule:** One Central Accounting Engine. Every journal: Σ Debit = Σ Credit.

## Events → journals (examples)

| Event | Debit | Credit |
|-------|-------|--------|
| Cash sale | Cash | Cafeteria Sales Revenue; Tax Payable |
| Card sale | Card Clearing / Bank | Sales Revenue; Tax Payable |
| Mobile money | Mobile Money | Sales Revenue; Tax Payable |
| Credit / pay later | Accounts Receivable | Sales Revenue; Tax Payable |
| Inventory consumption (recipe) | COGS | Inventory |
| Purchase on credit | Inventory | Accounts Payable |
| Supplier payment | Accounts Payable | Cash / Bank |
| Expense paid | Expense | Cash / Payable |
| Waste posted | Waste Expense | Inventory |
| Tip (liability mode) | Cash / Clearing | Employee Tip Payable |
| Service charge (revenue mode) | Cash/AR | Service Charge Revenue |
| Discount | Discount (contra) / reduce revenue per policy | — |
| Refund | reverse original legs | reverse |

## Configurable mappings (CafeteriaProfile / posting rules)

`CAFETERIA_SALES_REVENUE`, `COFFEE_REVENUE`, `FOOD_REVENUE`, `DELIVERY_REVENUE`, `INVENTORY`, `COGS`, `WASTE_EXPENSE`, `DISCOUNT_ACCOUNT`, `TAX_PAYABLE`, `SERVICE_CHARGE`, `TIP_PAYABLE`, `CASH`, `BANK`, `CARD_CLEARING`, `MOBILE_MONEY`, `ACCOUNTS_RECEIVABLE`, `ACCOUNTS_PAYABLE`

## Integration points

- POS checkout → existing `SALE_COMPLETED` / tax posting path
- Restaurant order paid → POS → CAE (no parallel restaurant ledger)
- Recipe deduction → inventory movement → COGS posting when accounting enabled
- Waste approve → inventory + waste expense
- Tips: never revenue if configured as employee payable

## Controls

- Posted journals immutable; corrections via reversing entries
- Tenant + branch on every entry
- Accounting disabled tenants skip post but keep operational audit
