# Cafeteria + Barista — Database ERD

**Date:** 2026-09-06  
**Convention:** New tables live in `apps.restaurant` unless noted. Shared engines unchanged.

---

## Core (existing — KEEP)

```
MenuCategory 1──* MenuItem *──? Product
MenuItem 1──* Recipe 1──* RecipeIngredient *──1 Ingredient *──? Product
RestaurantFloor 1──* DiningTable
KitchenStation
ModifierGroup 1──* Modifier
RestaurantOrder *──? DiningTable
RestaurantOrder 1──* OrderLine *──1 MenuItem
```

---

## Extensions (CREATE / EXTEND)

### CafeteriaProfile

`restaurant_cafeteria_profiles`

- tenant, branch (unique active)
- business_name, trading_name, logo_url, phone, email, address
- currency, timezone, language
- tax_profile_id (optional FK/settings ref)
- receipt_header, receipt_footer
- order_prefix, invoice_prefix
- kitchen_barista_mode (enum: kitchen | barista | both)
- flags: table_service, takeaway, delivery, reservations, tips, service_charge, loyalty, recipe_deduction, negative_stock_allowed
- default_warehouse_id, default_cash_account_id, default_sales_account_id, default_inventory_account_id, default_cogs_account_id
- settings JSON

### MenuItem extensions

- kitchen_station_id, preparation_time_minutes
- is_featured, is_popular, pos_visible, mobile_visible
- track_inventory, allow_modifiers, allow_notes
- available_dine_in / takeaway / delivery
- availability_start / availability_end (time)
- base_cost, coffee_attrs JSON (bean, dose, shots, milk, temp — optional)

### MenuItemVariant

`restaurant_menu_item_variants`

- menu_item, name, sku, barcode
- price_adjustment, final_price (or compute)
- recipe_qty_multiplier
- is_default, is_available, sort_order

### MenuItemModifierGroup

`restaurant_menu_item_modifier_groups`

- menu_item ↔ modifier_group (M2M through with sort_order)

### OrderLineModifier

`restaurant_order_line_modifiers`

- order_line, modifier, name snapshot, price_delta, quantity

### OrderLine / Order extensions

- OrderLine.kitchen_station_id, OrderLine.variant_id
- Order.queue_number, priority, barista_user_id, accepted_at, ready_at, served_at
- tip_amount, service_charge_amount (or on Invoice — prefer sales invoice; snapshot on order for KDS)

### Recipe versioning

- status: draft | active | archived
- Only one active recipe per menu_item (+ optional variant) at a time
- activating archives previous active

### Ingredient extensions

- purchase_unit, consumption_unit, conversion_rate
- min_stock, max_stock, reorder_level
- expiry_tracking, batch_tracking, storage_location
- supplier_id (optional), average_cost, last_cost

### WasteRecord

`restaurant_waste_records`

- branch, date, ingredient and/or product/menu_item
- quantity, unit, unit_cost, total_cost
- waste_type (expired, spoiled, prep, spillage, burned, damaged, employee_meal, sample, other)
- employee_user_id, reason, notes, approval_status
- inventory_adjustment_id (FK optional)
- journal_entry_id (optional)

### BaristaProfile

`restaurant_barista_profiles`

- employee/user, barista_code, skill_level, specialization
- assigned_branch, default_station, employment_status, start_date, certification, notes

### KitchenStation extension

- station_type: coffee_bar | cold_drinks | kitchen | bakery | dessert | juice | grill | other

---

## Shared FKs (no new engines)

| Cafeteria concept | Shared table |
|-------------------|--------------|
| Stock on hand | inventory.Inventory / StockMovement |
| PO / GRN | purchases.* |
| Customer / Supplier | customers / suppliers |
| Payment / Invoice / Cash session | sales.* |
| Journal | finance.* |
| Audit | audit.* |

---

## Indexing notes

- (tenant, branch, status, opened_at) on orders — existing
- (tenant, branch, queue_number) unique where set
- (tenant, menu_item, status) on recipes for active lookup
- (tenant, branch, waste_type, date) on waste
