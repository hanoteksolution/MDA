# DATABASE_ERD.md

# Database Entity Relationship Rules

Database:

PostgreSQL

Architecture:

Normalized Database Design

Target:

Millions of Records

High Performance

---

# Core Entity Relationships

Branch

1:N Users

1:N Warehouses

1:N Sales

1:N Purchases

---

# User Relationships

Role

1:N Users

Users

1:N Audit Logs

Users

1:N Sales

Users

1:N Purchases

---

# Product Relationships

Category

1:N Products

Brand

1:N Products

Product

1:N Inventory

Product

1:N Sale Items

Product

1:N Purchase Items

Product

1:N Stock Movements

---

# Inventory Relationships

Warehouse

1:N Inventory

Inventory

N:1 Product

Inventory

N:1 Warehouse

Inventory

1:N Inventory Transactions

---

# Customer Relationships

Customer

1:N Sales

Customer

1:N Quotations

Customer

1:N Invoices

Customer

1:N Receipts

---

# Supplier Relationships

Supplier

1:N Purchases

Supplier

1:N Supplier Payments

Supplier

1:N Purchase Orders

---

# Purchase Relationships

Purchase

1:N Purchase Items

Purchase

N:1 Supplier

Purchase

N:1 Branch

Purchase

1:N Payments

---

# Sales Relationships

Sale

1:N Sale Items

Sale

N:1 Customer

Sale

N:1 Branch

Sale

N:1 User

Sale

1:N Payments

---

# Financial Relationships

Account

1:N Journal Entries

Journal Entry

N:1 Account

Expense

N:1 Account

Income

N:1 Account

---

# Notification Relationships

User

1:N Notifications

Notification

N:1 User

---

# Audit Relationships

User

1:N Audit Logs

Audit Log

N:1 User

---

# Required Master Tables

roles

permissions

branches

categories

brands

warehouses

taxes

units

currencies

payment_methods

expense_categories

notification_types

---

# Required Transaction Tables

sales

sale_items

purchases

purchase_items

stock_movements

payments

expenses

incomes

journal_entries

inventory_transactions

---

# Required Document Tables

quotations

quotation_items

invoices

invoice_items

receipts

receipt_items

purchase_orders

purchase_order_items

---

# Inventory Rules

Inventory quantity must NEVER be stored only in products table.

Use:

inventory table

stock_movements table

inventory_transactions table

All stock changes must generate transaction history.

---

# Financial Rules

Never store profit directly.

Profit must be calculated.

Formula:

## Revenue

# Cost Of Goods Sold

Gross Profit

## Gross Profit

# Expenses

Net Profit

---

# Soft Delete Rules

All important tables must support:

deleted_at

deleted_by

Never permanently delete business data.

---

# Audit Rules

Every important table must contain:

created_at

updated_at

created_by

updated_by

---

# Index Rules

Create indexes for:

sku

barcode

invoice_number

receipt_number

quotation_number

customer_code

supplier_code

sale_date

purchase_date

created_at

---

# ERD Design Principle

Every transaction must be traceable.

Every stock movement must be traceable.

Every financial entry must be traceable.

No orphan records allowed.

No duplicate business records allowed.

Referential integrity is mandatory.
