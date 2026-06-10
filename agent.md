# AGENT.md

## Project Overview

This project is a premium enterprise Retail ERP + POS Desktop Application.

The goal is to build a modern, scalable, secure, offline-first, high-performance retail management system.

The system must feel comparable to Odoo Enterprise, Zoho Inventory, Shopify POS, and Microsoft Dynamics.

Every implementation decision must prioritize:

1. Performance
2. Scalability
3. Security
4. User Experience
5. Offline Capability
6. Maintainability

Never generate unnecessary complexity.

---

# Technology Stack

Backend:

* Django
* Django REST Framework
* PostgreSQL
* Redis
* Celery

Frontend:

* React
* TypeScript
* Shadcn UI
* Tailwind CSS

Desktop:

* Tauri

Offline:

* SQLite local cache
* Sync engine

Authentication:

* JWT

---

# Architecture Rules

Always follow Clean Architecture.

Required layers:

backend/
├── apps/
├── core/
├── services/
├── repositories/
├── api/
├── permissions/
├── utils/

Frontend:

src/
├── pages/
├── components/
├── layouts/
├── modules/
├── services/
├── hooks/
├── store/
├── types/
├── utils/

Never place business logic inside UI components.

Business logic belongs in services.

Database logic belongs in repositories.

---

# UI Design Rules

Design style:

* Premium
* Modern
* Enterprise
* Minimal
* Professional

Inspired by:

* Odoo Enterprise
* Linear
* Stripe Dashboard
* Shopify Admin
* Notion

Avoid:

* Old Bootstrap appearance
* Cluttered layouts
* Crowded tables
* Large gradients
* Excessive colors

Use:

* White backgrounds
* Light gray surfaces
* Emerald green primary color
* Soft shadows
* Rounded corners
* Consistent spacing

---

# Performance Rules

Performance is critical.

Always:

* Use pagination
* Use lazy loading
* Use memoization
* Optimize database queries
* Use select_related
* Use prefetch_related
* Cache heavy queries
* Avoid N+1 queries

Never:

* Load unnecessary data
* Fetch large datasets at once
* Create heavy dashboard queries

Target:

* API response under 200ms
* Dashboard under 2 seconds
* Fast startup time

---

# Database Rules

Database is PostgreSQL.

Requirements:

* Proper indexes
* Foreign keys
* Soft delete support
* Audit fields

Every table must include:

* id
* created_at
* updated_at
* created_by
* updated_by

Never store duplicated data.

---

# Security Rules

Always:

* Validate inputs
* Sanitize outputs
* Check permissions
* Log important actions

Never:

* Expose sensitive data
* Store passwords in plain text
* Skip permission checks

---

# User Roles

Required roles:

* Super Admin
* Admin
* Branch Manager
* Accountant
* Inventory Manager
* Cashier
* Sales Staff
* Read Only User

Role permissions must be enforced on backend.

Frontend permissions are not sufficient.

---

# Core Modules

Required modules:

1. Dashboard
2. POS
3. Products
4. Inventory
5. Purchases
6. Sales
7. Customers
8. Suppliers
9. Finance
10. Reports
11. Users
12. Settings

Never remove or rename these modules.

---

# POS Requirements

POS must be:

* Extremely fast
* Offline capable
* Keyboard friendly
* Touch friendly

Required features:

* Barcode scanning
* Product search
* Cart
* Discounts
* Taxes
* Multiple payments
* Receipt printing

POS must continue functioning without internet.

---

# Inventory Rules

Inventory tracking must include:

* Available stock
* Reserved stock
* Damaged stock
* Returned stock

Low stock alert:

Trigger warning when stock <= minimum stock level.

Default alert threshold:

5 units remaining.

---

# Finance Rules

Finance calculations must always be accurate.

Required calculations:

* Revenue
* Expenses
* Cost of Goods Sold
* Gross Profit
* Net Profit
* Inventory Value

Never calculate financial figures on frontend.

Always calculate on backend.

---

# Reporting Rules

Reports must support:

* PDF Export
* Excel Export
* Printing

Reports should use filters.

Never load all records into memory.

---

# Offline Sync Rules

System must work offline.

When internet returns:

1. Sync local changes
2. Resolve conflicts
3. Retry failed syncs
4. Preserve data integrity

No transaction should be lost.

---

# Coding Standards

Always:

* Write clean code
* Use TypeScript types
* Use reusable components
* Use descriptive names
* Add comments for complex logic

Never:

* Use any
* Duplicate code
* Create giant files
* Mix concerns

Maximum file size target:

300 lines.

Split files when necessary.

---

# Development Workflow

Before implementing any feature:

1. Create database model
2. Create repository
3. Create service
4. Create API
5. Create frontend page
6. Add tests

Never skip architecture layers.

Always think enterprise first.

This project must remain maintainable for years.
# Required Documents

Before making any change, read:

1. docs/architecture/SYSTEM_ARCHITECTURE.md
2. docs/architecture/DATABASE_ERD.md
3. docs/architecture/DATABASE_SCHEMA.md
4. docs/architecture/UI_ARCHITECTURE.md
5. docs/product/PRODUCT_REQUIREMENTS.md
6. docs/product/UI_GUIDELINES.md
7. docs/product/FEATURE_ROADMAP.md
7. docs/api/API_SPECIFICATION.md
7. docs/ui/DESIGN_SYSTEM.md
7. docs/workflows/BUSINESS_RULES.md

These documents are the source of truth.

If implementation conflicts with these documents:

ALWAYS FOLLOW THE DOCUMENTS.

## POS Design Rules

POS is the most important screen in the application.

Requirements:

- Must utilize 95% of available workspace
- Must support touch screens
- Must support barcode scanning
- Must support keyboard shortcuts
- Product grid must show at least 5 products per row on desktop
- Cart panel must always remain visible
- Checkout actions must always remain visible
- Product images are mandatory
- Category navigation is mandatory
- Fast search is mandatory

Never use large empty whitespace.

The POS must be optimized for speed and cashier productivity.