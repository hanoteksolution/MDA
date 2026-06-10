# Missing Requirements & Documentation Gaps

Analysis date: 2026-06-06

This document identifies gaps between existing documentation, inconsistencies across documents, and requirements needed before implementation begins.

---

## Document Inconsistencies

| Issue | Location A | Location B | Resolution Needed |
|-------|-----------|-----------|-------------------|
| BUSINESS_RULES path | `master-prompt.md` → `docs/product/BUSINESS_RULES.md` | Actual: `docs/workflows/BUSINESS_RULES.md` | Fix path in master-prompt |
| Module count | `agent.md` lists 12 modules | `master-prompt.md` lists 15 (adds Roles, Notifications, Audit Logs) | Align module list; treat Roles/Audit under Administration |
| Suppliers placement | `SYSTEM_ARCHITECTURE.md` → Purchases app | `UI_ARCHITECTURE.md` → separate Suppliers module | Separate Django app + frontend module for suppliers |
| Invoice vs inventory | `BUSINESS_RULES.md` — invoice does not reduce stock until sale completed | POS checkout creates sale + receipt immediately | Define document lifecycle states (draft, confirmed, paid, cancelled) |

---

## Database Schema Gaps

`DATABASE_SCHEMA.md` is incomplete relative to `DATABASE_ERD.md` and business rules.

### Missing Master Tables

- `taxes` — rate, name, is_active, branch scope
- `units` — unit of measure (piece, kg, liter)
- `currencies` — code, symbol, exchange_rate
- `payment_methods` — cash, card, mobile, credit
- `expense_categories`
- `notification_types`
- `role_permissions` — M2M between roles and permissions
- `companies` — company profile for invoices/receipts
- `settings` — key/value system configuration
- `branches` — missing audit fields, soft delete, is_active

### Missing Transaction / Document Tables

- `stock_movements`
- `inventory_transactions`
- `payments` — polymorphic link to sales/purchases
- `incomes`
- `purchase_orders` + `purchase_order_items`
- `quotation_items`
- `invoice_items`
- `receipt_items`
- `sale_returns` + `sale_return_items`
- `purchase_returns` + `purchase_return_items`
- `inventory_transfers` + `transfer_items`
- `inventory_adjustments` + `adjustment_items`
- `supplier_payments`
- `customer_credit_accounts` + `credit_transactions`

### Missing Fields on Existing Tables

All important tables require: `created_by`, `updated_by`, `deleted_at`, `deleted_by`

Additional field gaps:

- `inventory.returned_quantity` — required by master-prompt
- `products.is_active`, `products.tax_id`, `products.unit_id`
- `sales.branch_id`, `sales.user_id`, `sales.status`, `sales.discount_amount`, `sales.tax_amount`
- `users` — missing `created_by`, `updated_by`, soft delete
- `customers` — credit_limit, outstanding_balance
- `suppliers` — outstanding_balance, payment_terms

### Missing Index & Constraint Spec

- Composite indexes for `(branch_id, sale_date)`, `(warehouse_id, product_id)`
- Unique constraints for document numbers per branch
- Check constraints for non-negative quantities

---

## API Specification Gaps

### Missing Endpoint Groups

- Users CRUD + activate/deactivate
- Roles CRUD + permission assignment
- Permissions list
- Branches CRUD
- Settings (company, tax, POS, backup, security)
- Brands CRUD
- Warehouses CRUD
- Units, taxes, currencies, payment methods
- Quotations CRUD + convert-to-invoice
- Invoices CRUD + payment recording
- Receipts list + print
- Notifications list + mark-read
- Audit logs (read-only, filtered)
- Sync (push/pull/status/conflicts)
- Backup trigger + restore
- Dashboard KPIs
- File upload (product images, attachments)

### Missing API Standards

- JWT header format and refresh flow
- Pagination parameters (`page`, `page_size`, `ordering`)
- Filter query conventions
- Rate limiting response codes
- Idempotency keys for POS checkout
- WebSocket or SSE for real-time notifications (optional)
- OpenAPI/Swagger generation policy

---

## Architecture Gaps

### Offline Sync Engine

Not fully specified:

- SQLite schema mirroring strategy (subset vs full)
- Sync queue table structure
- Conflict resolution beyond "newest wins" (e.g., stock conflicts)
- Retry backoff policy
- Partial sync vs full sync triggers
- Offline auth session handling

### Infrastructure & DevOps

Missing documents:

- Deployment architecture (on-prem vs cloud)
- Docker Compose service definitions
- Environment variable catalog
- CI/CD pipeline requirements
- PostgreSQL backup/restore procedure
- Redis/Celery monitoring
- Log aggregation strategy
- SSL/TLS termination

### File Storage

- Product image storage (local vs S3-compatible)
- Purchase attachment storage
- Max file size and allowed MIME types

### Hardware Integration

- Receipt printer protocols (ESC/POS)
- Barcode scanner input mode (keyboard wedge vs serial)
- Cash drawer trigger
- Label printer (future)

---

## Business Rules Gaps

### Undefined Workflows

- Tax calculation (inclusive vs exclusive, multi-tax)
- Discount rules (line vs order, max %, role-based limits)
- Split payment allocation and change calculation
- Purchase order approval states (draft → submitted → approved → received)
- Sale/invoice status machine
- Stock reservation during open POS cart
- Inter-branch transfer approval
- Customer credit limit enforcement
- Supplier payment terms and due dates
- Rounding rules for currency

### Branch Isolation

- Can Admin see all branches?
- Is inventory shared or branch-scoped?
- Document number sequences per branch?

### Security Detail

- Password policy (length, complexity, expiry)
- Account lockout after failed attempts
- Session timeout duration
- OTP delivery channel (email/SMS)
- Sensitive field encryption at rest

---

## UI / UX Gaps

- Dedicated Notifications page (master-prompt module vs drawer-only in UI_ARCHITECTURE)
- Error pages (403, 404, 500, offline)
- Loading skeleton standards
- Empty state patterns
- Onboarding / first-run setup wizard
- Print preview layouts (receipt, invoice, report)
- Accessibility (WCAG level target)
- Localization / i18n strategy
- Keyboard shortcut registry (especially POS)

---

## Testing & Quality Gaps

- Unit test coverage targets
- Integration test scope
- E2E test tooling (Playwright/Cypress)
- Performance benchmark suite
- Load testing criteria for POS concurrency
- Security testing checklist (OWASP)

---

## Recommended Pre-Implementation Deliverables

1. ~~`docs/architecture/DATABASE_SCHEMA.md` — full schema with all ERD tables and audit fields~~ **Done (v2.0)**
2. ~~`docs/architecture/OFFLINE_SYNC.md` — sync engine specification~~ **Placeholder exists; full spec pending**
3. ~~`docs/architecture/DEPLOYMENT.md` — infrastructure and environment guide~~ **Placeholder exists; full spec pending**
4. ~~`docs/api/API_SPECIFICATION.md` — complete endpoint catalog with request/response schemas~~ **Done (v2.0)**
5. ~~`docs/workflows/DOCUMENT_LIFECYCLE.md` — status transitions for sales, purchases, invoices~~ **Done (v1.0)**
6. `docs/workflows/TAX_AND_PRICING.md` — tax, discount, and rounding rules
7. ~~Fix path inconsistency for BUSINESS_RULES in master-prompt~~ **Done**

---

## Priority Classification

| Priority | Gap | Impact |
|----------|-----|--------|
| P0 | Complete database schema | Blocks all backend work |
| P0 | Document lifecycle states | Blocks sales, purchases, finance |
| P0 | Offline sync specification | Blocks POS offline mode |
| P1 | Full API specification | Blocks frontend/backend contract |
| P1 | Branch isolation rules | Blocks multi-branch features |
| P1 | Tax and discount rules | Blocks POS and invoicing |
| P2 | DevOps/deployment docs | Blocks production release |
| P2 | Hardware integration spec | Blocks receipt printing |
| P3 | i18n and accessibility | Post-MVP enhancement |
