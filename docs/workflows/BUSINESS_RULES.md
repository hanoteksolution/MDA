# BUSINESS_RULES.md

# Business Rules

This document is the source of truth for all business logic.

---

# Product Rules

Every product must have:

SKU

Name

Cost Price

Selling Price

Category

Minimum Stock

A product cannot be sold if stock is unavailable.

---

# Inventory Rules

Every stock change must create:

Stock Movement Record

Inventory Transaction Record

Audit Log

---

# Low Stock Rule

If stock <= minimum_stock

Create Notification

Show Dashboard Alert

Show Inventory Warning

Default threshold:

5 Units

---

# Sales Rules

When sale is completed:

Reduce inventory

Create sale record

Create receipt

Create audit log

Update customer history

---

# Return Rules

When sale return occurs:

Increase inventory

Create return record

Create audit log

Reverse financial impact

---

# Purchase Rules

When purchase is received:

Increase inventory

Create inventory transaction

Update supplier balance

Create audit log

---

# Quotation Rules

Quotation does not affect inventory.

Quotation does not affect finance.

Quotation can be converted to invoice.

---

# Invoice Rules

Invoice affects finance.

Invoice does not reduce inventory until sale is completed.

---

# Receipt Rules

Receipt generated after payment.

Receipt linked to sale.

Receipt printable.

---

# Profit Rules

Revenue

Minus

Cost Of Goods Sold

Equals

Gross Profit

Gross Profit

Minus

Expenses

Equals

Net Profit

Profit must never be manually entered.

Profit is always calculated.

---

# Customer Credit Rules

Customer can purchase on credit.

Credit balance must be tracked.

Outstanding balances must appear in reports.

---

# Supplier Balance Rules

All unpaid purchases create supplier balance.

Supplier payments reduce supplier balance.

---

# Audit Rules

Track:

Create

Update

Delete

Login

Logout

Inventory Changes

Sales

Purchases

Finance

Audit logs cannot be edited.

---

# Permission Rules

Cashier:

POS only

Inventory Manager:

Inventory only

Accountant:

Finance and Reports

Branch Manager:

Branch Operations

Admin:

All Branch Data

Super Admin:

Full System Access

---

# Offline Rules

System must continue operating offline.

All transactions stored locally.

Sync automatically when connection returns.

No transaction loss allowed.

---

# Financial Rules

All financial calculations happen on backend.

Never calculate financial reports on frontend.

Backend is the single source of truth.

---

# Final Rule

If implementation conflicts with this document:

Always follow BUSINESS_RULES.md
