# DATABASE_SCHEMA.md

Version: 2.0

Database: PostgreSQL

All important tables include audit fields: `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`, `deleted_by`.

---

## Audit Field Standard

Every important table includes:

| Field | Type | Notes |
|-------|------|-------|
| id | UUID or BigInt PK | UUID preferred for sync |
| created_at | DateTime | Auto on create |
| updated_at | DateTime | Auto on update |
| created_by | FK → users | Nullable for system actions |
| updated_by | FK → users | Nullable |
| deleted_at | DateTime | Null = active (soft delete) |
| deleted_by | FK → users | Nullable |

---

## Core & Authentication

### companies

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | Required |
| legal_name | VARCHAR(255) | |
| tax_id | VARCHAR(100) | |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| address | TEXT | |
| logo | VARCHAR(500) | File path/URL |
| currency_id | FK → currencies | Default currency |
| + audit fields | | |

**Indexes:** `name`

---

### branches

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| company_id | FK → companies | Required |
| name | VARCHAR(255) | Required |
| code | VARCHAR(50) | Unique per company |
| address | TEXT | |
| phone | VARCHAR(50) | |
| email | VARCHAR(255) | |
| is_active | BOOLEAN | Default true |
| is_default | BOOLEAN | One default per company |
| + audit fields | | |

**Indexes:** `code`, `company_id`, `is_active`

---

### roles

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | Unique. Values: Super Admin, Admin, Branch Manager, Accountant, Inventory Manager, Cashier, Sales Staff, Read Only User |
| slug | VARCHAR(100) | Unique, machine-readable |
| description | TEXT | |
| is_system | BOOLEAN | System roles cannot be deleted |
| + audit fields | | |

**Indexes:** `slug`, `name`

---

### permissions

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | Unique |
| codename | VARCHAR(100) | Unique, e.g. `products.view` |
| module | VARCHAR(50) | dashboard, pos, products, inventory, etc. |
| description | TEXT | |
| + audit fields | | |

**Indexes:** `codename`, `module`

---

### role_permissions

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| role_id | FK → roles | |
| permission_id | FK → permissions | |
| + audit fields | | |

**Unique:** `(role_id, permission_id)`

---

### users

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| username | VARCHAR(150) | Unique |
| email | VARCHAR(255) | Unique |
| password | VARCHAR(255) | Hashed |
| first_name | VARCHAR(150) | |
| last_name | VARCHAR(150) | |
| role_id | FK → roles | Required |
| branch_id | FK → branches | Nullable for Super Admin |
| phone | VARCHAR(50) | |
| avatar | VARCHAR(500) | |
| is_active | BOOLEAN | Default true |
| is_staff | BOOLEAN | Django admin access |
| last_login | DateTime | |
| + audit fields | | |

**Indexes:** `username`, `email`, `role_id`, `branch_id`, `is_active`

---

## Master Data

### categories

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | Required |
| parent_id | FK → categories | Nullable, self-ref |
| description | TEXT | |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `name`, `parent_id`

---

### brands

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | Required, unique |
| description | TEXT | |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `name`

---

### units

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | e.g. Piece, Kg, Liter |
| abbreviation | VARCHAR(20) | e.g. pc, kg, L |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

---

### taxes

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | Required |
| rate | DECIMAL(8,4) | Percentage, e.g. 15.0000 |
| is_inclusive | BOOLEAN | Tax included in price |
| branch_id | FK → branches | Nullable = all branches |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `branch_id`, `is_active`

---

### currencies

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| code | VARCHAR(3) | ISO 4217, unique |
| name | VARCHAR(100) | |
| symbol | VARCHAR(10) | |
| exchange_rate | DECIMAL(18,6) | Against base currency |
| is_base | BOOLEAN | One base currency |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `code`

---

### payment_methods

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | Cash, Card, Mobile, Credit |
| code | VARCHAR(50) | Unique |
| is_active | BOOLEAN | Default true |
| requires_reference | BOOLEAN | e.g. card auth code |
| + audit fields | | |

---

### expense_categories

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | Required |
| account_id | FK → accounts | Nullable |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

---

### notification_types

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | low_stock, out_of_stock, payment_due, etc. |
| code | VARCHAR(50) | Unique |
| + audit fields | | |

---

### settings

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| key | VARCHAR(255) | Unique per scope |
| value | JSONB | Flexible value storage |
| category | VARCHAR(50) | general, company, pos, tax, security, backup |
| branch_id | FK → branches | Nullable = global |
| company_id | FK → companies | Nullable |
| + audit fields | | |

**Unique:** `(key, branch_id, company_id)`
**Indexes:** `key`, `category`

---

## Products

### products

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| sku | VARCHAR(100) | Unique |
| barcode | VARCHAR(100) | Unique, nullable |
| name | VARCHAR(255) | Required |
| category_id | FK → categories | Required |
| brand_id | FK → brands | Nullable |
| unit_id | FK → units | Required |
| tax_id | FK → taxes | Nullable |
| cost_price | DECIMAL(18,4) | Required |
| selling_price | DECIMAL(18,4) | Required |
| minimum_stock | INTEGER | Default 5 |
| description | TEXT | |
| image | VARCHAR(500) | |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `sku`, `barcode`, `name`, `category_id`, `is_active`

---

### product_images

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| product_id | FK → products | |
| image | VARCHAR(500) | Required |
| is_primary | BOOLEAN | |
| sort_order | INTEGER | |
| + audit fields | | |

---

## Inventory

### warehouses

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(255) | Required |
| code | VARCHAR(50) | Unique per branch |
| branch_id | FK → branches | Required |
| address | TEXT | |
| is_active | BOOLEAN | Default true |
| is_default | BOOLEAN | One default per branch |
| + audit fields | | |

**Indexes:** `branch_id`, `code`

---

### inventory

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| product_id | FK → products | |
| warehouse_id | FK → warehouses | |
| quantity | DECIMAL(18,4) | Available stock |
| reserved_quantity | DECIMAL(18,4) | Default 0 |
| damaged_quantity | DECIMAL(18,4) | Default 0 |
| returned_quantity | DECIMAL(18,4) | Default 0 |
| + audit fields | | |

**Unique:** `(product_id, warehouse_id)`
**Indexes:** `product_id`, `warehouse_id`, `quantity`

---

### stock_movements

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| product_id | FK → products | |
| warehouse_id | FK → warehouses | |
| movement_type | VARCHAR(50) | sale, purchase, adjustment, transfer_in, transfer_out, return |
| quantity | DECIMAL(18,4) | Signed delta |
| reference_type | VARCHAR(50) | Polymorphic: sale, purchase, adjustment, etc. |
| reference_id | UUID | Polymorphic FK |
| notes | TEXT | |
| + audit fields | | |

**Indexes:** `product_id`, `warehouse_id`, `movement_type`, `reference_type`, `reference_id`, `created_at`

---

### inventory_transactions

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| inventory_id | FK → inventory | |
| transaction_type | VARCHAR(50) | in, out, reserve, unreserve, damage, return |
| quantity_before | DECIMAL(18,4) | |
| quantity_after | DECIMAL(18,4) | |
| quantity_change | DECIMAL(18,4) | |
| reference_type | VARCHAR(50) | |
| reference_id | UUID | |
| + audit fields | | |

**Indexes:** `inventory_id`, `transaction_type`, `created_at`

---

### inventory_adjustments

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| adjustment_number | VARCHAR(50) | Unique per branch |
| warehouse_id | FK → warehouses | |
| branch_id | FK → branches | |
| reason | TEXT | |
| status | VARCHAR(50) | draft, confirmed, cancelled |
| + audit fields | | |

---

### inventory_adjustment_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| adjustment_id | FK → inventory_adjustments | |
| product_id | FK → products | |
| quantity_before | DECIMAL(18,4) | |
| quantity_after | DECIMAL(18,4) | |
| quantity_change | DECIMAL(18,4) | |
| + audit fields | | |

---

### inventory_transfers

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| transfer_number | VARCHAR(50) | Unique |
| from_warehouse_id | FK → warehouses | |
| to_warehouse_id | FK → warehouses | |
| branch_id | FK → branches | |
| status | VARCHAR(50) | draft, in_transit, received, cancelled |
| + audit fields | | |

---

### inventory_transfer_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| transfer_id | FK → inventory_transfers | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| + audit fields | | |

---

## Customers & Suppliers

### customers

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| customer_code | VARCHAR(50) | Unique |
| full_name | VARCHAR(255) | Required |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| address | TEXT | |
| credit_limit | DECIMAL(18,4) | Default 0 |
| outstanding_balance | DECIMAL(18,4) | Default 0, computed/cached |
| branch_id | FK → branches | Nullable |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `customer_code`, `full_name`, `phone`, `branch_id`

---

### customer_credit_accounts

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| customer_id | FK → customers | Unique |
| credit_limit | DECIMAL(18,4) | |
| balance | DECIMAL(18,4) | Outstanding |
| + audit fields | | |

---

### credit_transactions

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| credit_account_id | FK → customer_credit_accounts | |
| transaction_type | VARCHAR(50) | charge, payment, adjustment |
| amount | DECIMAL(18,4) | |
| balance_after | DECIMAL(18,4) | |
| reference_type | VARCHAR(50) | sale, payment |
| reference_id | UUID | |
| + audit fields | | |

---

### suppliers

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| supplier_code | VARCHAR(50) | Unique |
| company_name | VARCHAR(255) | Required |
| contact_person | VARCHAR(255) | |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| address | TEXT | |
| payment_terms | INTEGER | Days |
| outstanding_balance | DECIMAL(18,4) | Default 0 |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `supplier_code`, `company_name`

---

### supplier_payments

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| supplier_id | FK → suppliers | |
| payment_number | VARCHAR(50) | Unique |
| amount | DECIMAL(18,4) | |
| payment_method_id | FK → payment_methods | |
| payment_date | Date | |
| reference | VARCHAR(255) | |
| purchase_id | FK → purchases | Nullable |
| + audit fields | | |

---

## Sales Documents

### sales

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| sale_number | VARCHAR(50) | Unique per branch |
| customer_id | FK → customers | Nullable (walk-in) |
| branch_id | FK → branches | Required |
| user_id | FK → users | Cashier/staff |
| status | VARCHAR(50) | See DOCUMENT_LIFECYCLE.md |
| sale_date | DateTime | |
| subtotal | DECIMAL(18,4) | |
| discount_amount | DECIMAL(18,4) | Default 0 |
| tax_amount | DECIMAL(18,4) | Default 0 |
| total_amount | DECIMAL(18,4) | |
| amount_paid | DECIMAL(18,4) | Default 0 |
| notes | TEXT | |
| is_offline | BOOLEAN | Created offline |
| synced_at | DateTime | Nullable |
| + audit fields | | |

**Indexes:** `sale_number`, `customer_id`, `branch_id`, `status`, `sale_date`, `created_at`

---

### sale_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| sale_id | FK → sales | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_price | DECIMAL(18,4) | |
| cost_price | DECIMAL(18,4) | Snapshot at sale time |
| discount_amount | DECIMAL(18,4) | Default 0 |
| tax_amount | DECIMAL(18,4) | Default 0 |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### sale_returns

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| return_number | VARCHAR(50) | Unique |
| sale_id | FK → sales | |
| branch_id | FK → branches | |
| status | VARCHAR(50) | draft, confirmed, cancelled |
| return_date | DateTime | |
| total_amount | DECIMAL(18,4) | |
| reason | TEXT | |
| + audit fields | | |

---

### sale_return_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| return_id | FK → sale_returns | |
| sale_item_id | FK → sale_items | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_price | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### quotations

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| quotation_number | VARCHAR(50) | Unique per branch |
| customer_id | FK → customers | Required |
| branch_id | FK → branches | |
| user_id | FK → users | |
| status | VARCHAR(50) | See DOCUMENT_LIFECYCLE.md |
| valid_until | Date | |
| subtotal | DECIMAL(18,4) | |
| discount_amount | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| total_amount | DECIMAL(18,4) | |
| + audit fields | | |

**Indexes:** `quotation_number`, `customer_id`, `status`

---

### quotation_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| quotation_id | FK → quotations | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_price | DECIMAL(18,4) | |
| discount_amount | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### invoices

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| invoice_number | VARCHAR(50) | Unique per branch |
| customer_id | FK → customers | Required |
| sale_id | FK → sales | Nullable |
| quotation_id | FK → quotations | Nullable |
| branch_id | FK → branches | |
| status | VARCHAR(50) | See DOCUMENT_LIFECYCLE.md |
| issue_date | Date | |
| due_date | Date | |
| subtotal | DECIMAL(18,4) | |
| discount_amount | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| total_amount | DECIMAL(18,4) | |
| amount_paid | DECIMAL(18,4) | |
| + audit fields | | |

**Indexes:** `invoice_number`, `customer_id`, `status`, `due_date`

---

### invoice_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| invoice_id | FK → invoices | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_price | DECIMAL(18,4) | |
| discount_amount | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### receipts

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| receipt_number | VARCHAR(50) | Unique per branch |
| sale_id | FK → sales | Required |
| customer_id | FK → customers | Nullable |
| branch_id | FK → branches | |
| payment_date | DateTime | |
| total_amount | DECIMAL(18,4) | |
| + audit fields | | |

**Indexes:** `receipt_number`, `sale_id`

---

### receipt_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| receipt_id | FK → receipts | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_price | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

## Purchase Documents

### purchase_orders

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| order_number | VARCHAR(50) | Unique per branch |
| supplier_id | FK → suppliers | Required |
| branch_id | FK → branches | |
| user_id | FK → users | |
| status | VARCHAR(50) | See DOCUMENT_LIFECYCLE.md |
| order_date | Date | |
| expected_date | Date | Nullable |
| subtotal | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| total_amount | DECIMAL(18,4) | |
| notes | TEXT | |
| + audit fields | | |

**Indexes:** `order_number`, `supplier_id`, `status`, `order_date`

---

### purchase_order_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| purchase_order_id | FK → purchase_orders | |
| product_id | FK → products | |
| quantity_ordered | DECIMAL(18,4) | |
| quantity_received | DECIMAL(18,4) | Default 0 |
| unit_cost | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### purchases

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| purchase_number | VARCHAR(50) | Unique per branch |
| purchase_order_id | FK → purchase_orders | Nullable |
| supplier_id | FK → suppliers | Required |
| branch_id | FK → branches | |
| user_id | FK → users | |
| status | VARCHAR(50) | draft, received, cancelled |
| purchase_date | DateTime | |
| subtotal | DECIMAL(18,4) | |
| tax_amount | DECIMAL(18,4) | |
| total_amount | DECIMAL(18,4) | |
| amount_paid | DECIMAL(18,4) | |
| + audit fields | | |

**Indexes:** `purchase_number`, `supplier_id`, `purchase_date`

---

### purchase_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| purchase_id | FK → purchases | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_cost | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

### purchase_returns

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| return_number | VARCHAR(50) | Unique |
| purchase_id | FK → purchases | |
| supplier_id | FK → suppliers | |
| branch_id | FK → branches | |
| status | VARCHAR(50) | draft, confirmed, cancelled |
| return_date | DateTime | |
| total_amount | DECIMAL(18,4) | |
| + audit fields | | |

---

### purchase_return_items

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| return_id | FK → purchase_returns | |
| product_id | FK → products | |
| quantity | DECIMAL(18,4) | |
| unit_cost | DECIMAL(18,4) | |
| line_total | DECIMAL(18,4) | |
| + audit fields | | |

---

## Finance

### accounts

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| account_code | VARCHAR(50) | Unique |
| account_name | VARCHAR(255) | Required |
| account_type | VARCHAR(50) | asset, liability, equity, revenue, expense |
| parent_id | FK → accounts | Nullable |
| is_active | BOOLEAN | Default true |
| + audit fields | | |

**Indexes:** `account_code`, `account_type`

---

### journal_entries

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| entry_number | VARCHAR(50) | Unique |
| account_id | FK → accounts | |
| branch_id | FK → branches | |
| entry_date | Date | |
| description | TEXT | |
| debit | DECIMAL(18,4) | Default 0 |
| credit | DECIMAL(18,4) | Default 0 |
| reference_type | VARCHAR(50) | sale, purchase, expense |
| reference_id | UUID | |
| + audit fields | | |

**Indexes:** `account_id`, `entry_date`, `reference_type`, `reference_id`

---

### expenses

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| expense_number | VARCHAR(50) | Unique |
| category_id | FK → expense_categories | |
| account_id | FK → accounts | |
| branch_id | FK → branches | |
| amount | DECIMAL(18,4) | |
| description | TEXT | |
| expense_date | Date | |
| + audit fields | | |

---

### incomes

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| income_number | VARCHAR(50) | Unique |
| account_id | FK → accounts | |
| branch_id | FK → branches | |
| amount | DECIMAL(18,4) | |
| description | TEXT | |
| income_date | Date | |
| reference_type | VARCHAR(50) | |
| reference_id | UUID | |
| + audit fields | | |

---

### payments

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| payment_number | VARCHAR(50) | Unique |
| payment_method_id | FK → payment_methods | |
| amount | DECIMAL(18,4) | |
| payment_date | DateTime | |
| reference_type | VARCHAR(50) | sale, purchase, invoice |
| reference_id | UUID | |
| branch_id | FK → branches | |
| user_id | FK → users | |
| notes | TEXT | |
| + audit fields | | |

**Indexes:** `reference_type`, `reference_id`, `payment_date`

---

## Notifications & Audit

### notifications

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| user_id | FK → users | |
| notification_type_id | FK → notification_types | |
| title | VARCHAR(255) | |
| message | TEXT | |
| type | VARCHAR(20) | success, warning, error, info |
| is_read | BOOLEAN | Default false |
| read_at | DateTime | Nullable |
| reference_type | VARCHAR(50) | |
| reference_id | UUID | |
| + audit fields | | |

**Indexes:** `user_id`, `is_read`, `created_at`

---

### audit_logs

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| user_id | FK → users | Nullable |
| action | VARCHAR(50) | create, update, delete, login, logout |
| module | VARCHAR(50) | |
| entity_type | VARCHAR(100) | Model name |
| entity_id | UUID | |
| old_values | JSONB | Nullable |
| new_values | JSONB | Nullable |
| ip_address | VARCHAR(45) | |
| user_agent | TEXT | |
| timestamp | DateTime | Indexed |

**Indexes:** `user_id`, `action`, `module`, `entity_type`, `entity_id`, `timestamp`

---

## Sync (Offline)

### sync_queue

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| device_id | VARCHAR(255) | Client device identifier |
| entity_type | VARCHAR(100) | Model name |
| entity_id | UUID | Local or server ID |
| operation | VARCHAR(20) | create, update, delete |
| payload | JSONB | Serialized entity |
| status | VARCHAR(20) | pending, syncing, synced, failed, conflict |
| retry_count | INTEGER | Default 0 |
| last_error | TEXT | Nullable |
| synced_at | DateTime | Nullable |
| + audit fields | | |

**Indexes:** `device_id`, `status`, `created_at`

---

### sync_conflicts

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| sync_queue_id | FK → sync_queue | |
| entity_type | VARCHAR(100) | |
| entity_id | UUID | |
| local_payload | JSONB | |
| server_payload | JSONB | |
| resolution | VARCHAR(50) | server_wins, client_wins, merged |
| resolved_at | DateTime | |
| + audit fields | | |

---

## Relationships Summary

```
companies 1:N branches
branches 1:N users, warehouses, sales, purchases
roles 1:N users
roles N:M permissions (via role_permissions)
categories 1:N products
brands 1:N products
products 1:N inventory, sale_items, purchase_items, stock_movements
warehouses 1:N inventory
customers 1:N sales, quotations, invoices, receipts
suppliers 1:N purchases, purchase_orders, supplier_payments
sales 1:N sale_items, payments, receipts
sale 1:1 receipt (on completion)
purchase_orders 1:N purchase_order_items
purchases 1:N purchase_items
accounts 1:N journal_entries, expenses, incomes
users 1:N audit_logs, notifications
```

---

## Index Rules

Create indexes on all foreign keys plus:

- `sku`, `barcode`, `name` (products)
- `sale_number`, `invoice_number`, `receipt_number`, `quotation_number`, `purchase_number`, `order_number`
- `customer_code`, `supplier_code`
- `sale_date`, `purchase_date`, `created_at`
- Composite: `(branch_id, sale_date)`, `(warehouse_id, product_id)`, `(user_id, is_read)`

---

## Soft Delete Rules

All business tables use `deleted_at` / `deleted_by`. Default queries filter `deleted_at IS NULL`. Hard deletes are prohibited for transactional data.
