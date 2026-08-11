# RESTAURANT_CRUD_MATRIX

Legend: COMPLETE | PARTIAL | MISSING

## Core Entities

| Entity | List | Create | Detail | Update | Delete/Archive | Restore | Duplicate | Import/Export | Bulk | Permissions | Audit | Tests | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dashboard Summary | COMPLETE | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | PARTIAL | N/A | PARTIAL | PARTIAL |
| Menu Categories | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE (soft delete) | MISSING | MISSING | MISSING | MISSING | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Menu Items | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE (soft delete) | MISSING | MISSING | MISSING | MISSING | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Dining Tables | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE (soft delete) | MISSING | MISSING | MISSING | MISSING | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Restaurant Orders | COMPLETE | COMPLETE | COMPLETE | PARTIAL (status/lines only) | PARTIAL (cancel via status only) | N/A | MISSING | MISSING | MISSING | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Order Lines | PARTIAL | COMPLETE (add-line only) | Embedded only | PARTIAL (status by indirect flow) | PARTIAL (cancel status only) | N/A | MISSING | MISSING | MISSING | PARTIAL | PARTIAL | PARTIAL | PARTIAL |

## Missing Target Entities (all currently MISSING)

- Floor
- FloorPlan
- TableGroup
- ModifierGroup
- Modifier
- MenuItemVariant
- Recipe
- RecipeIngredient
- Ingredient
- KitchenStation
- KitchenPrinter mapping
- OrderItemModifier
- OrderPayment (restaurant-native payment record)
- RestaurantCustomer profile extensions
- RestaurantSupplier profile extensions
- PurchaseOrder (restaurant workspace workflow layer)
- GoodsReceipt (restaurant workspace workflow layer)
- StockLocation (restaurant context)
- StockMovement (restaurant context reporting layer)
- StockAdjustment (restaurant context workflow layer)
- StockTransfer (restaurant context workflow layer)
- WasteRecord
- Discount
- Tax
- PaymentMethod
- Expense / ExpenseCategory (restaurant-first views)
- RestaurantShift
- CashSession / CashMovement
- Invoice / InvoiceItem restaurant views
- RestaurantSetting
- RestaurantStaff
- Restaurant audit activity feed views
