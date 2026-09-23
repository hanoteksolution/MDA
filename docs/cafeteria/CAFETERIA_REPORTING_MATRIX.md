# Cafeteria + Barista — Reporting Matrix

**Date:** 2026-09-06

| Report | Source | Permission |
|--------|--------|------------|
| Daily / Hourly Sales | sales + orders | reports.view |
| Sales by Product / Category / Variant / Modifier | order lines | reports.view |
| Sales by Branch / Cashier / Barista / Order Type / Payment | sales + orders | reports.view |
| Top / Slow Products | order lines | reports.view |
| AOV / Refunds / Discounts / Promotions / Tax | sales | reports.view |
| Orders Prepared / Avg Prep Time / Delayed | order timestamps | barista/reports |
| Productivity by Shift / Barista | orders + shifts | reports.view |
| Stock On Hand / Valuation / Low Stock | inventory | inventory.view |
| Ingredient Usage / Recipe Consumption | recipe consume log | inventory/recipes |
| Waste / Spoilage | WasteRecord | cafeteria.waste |
| Theoretical vs Actual Usage | sales×recipes vs movements | reports + inventory |
| Stock Adjustment / Transfer | inventory | inventory.view |
| Purchase vs Consumption | purchases + recipes | purchasing/reports |
| PO / Supplier / GRN / Returns / Balances | purchases/suppliers | purchasing |
| Revenue / GP / Margin / COGS / Expenses | CAE + sales | finance/reports |
| Cashier Summary / Cash Flow / AR / AP | sales/finance | finance |
| P&L / Trial Balance / Balance Sheet | CAE | finance.view |
| Profitability by Product/Category/Branch/Day/Shift | sales + recipe cost | reports.view |

Pack registration: extend `apps/reports/services/packs/restaurant.py` with cafeteria-labeled variants; do not fork report engine.
