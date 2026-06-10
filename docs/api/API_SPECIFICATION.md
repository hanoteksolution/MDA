# API_SPECIFICATION.md

Version: 2.0

Base URL: `/api/v1/`

Authentication: JWT Bearer token in `Authorization` header.

---

## Global Standards

### Request Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
X-Branch-Id: <branch_uuid>        # Optional, defaults to user's branch
X-Idempotency-Key: <uuid>        # Required for POS checkout
```

### Pagination

Query parameters on all list endpoints:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| page_size | integer | 20 | Items per page (max 100) |
| ordering | string | -created_at | Field to sort by, prefix `-` for desc |
| search | string | | Full-text search where supported |

### Paginated Response

```json
{
  "success": true,
  "message": "",
  "data": {
    "results": [],
    "count": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

### Success Response

```json
{
  "success": true,
  "message": "Operation completed.",
  "data": {}
}
```

### Error Response

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "field_name": ["Error message."]
  }
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 409 | Conflict (sync, duplicate) |
| 429 | Rate limited |
| 500 | Server error |

---

## Authentication APIs

### POST /auth/login

Authenticate user and receive JWT tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "secret"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>",
    "user": {
      "id": "uuid",
      "username": "admin",
      "email": "admin@example.com",
      "first_name": "Admin",
      "last_name": "User",
      "role": { "id": "uuid", "name": "Super Admin", "slug": "super_admin" },
      "branch": { "id": "uuid", "name": "Main Branch", "code": "BR01" },
      "permissions": ["dashboard.view", "products.view"]
    }
  }
}
```

### POST /auth/logout

Invalidate refresh token.

**Request:** `{ "refresh": "<jwt_refresh_token>" }`

### POST /auth/refresh

**Request:** `{ "refresh": "<jwt_refresh_token>" }`

**Response:** `{ "access": "<new_access_token>" }`

### POST /auth/change-password

**Request:**
```json
{
  "current_password": "old",
  "new_password": "new",
  "confirm_password": "new"
}
```

### POST /auth/forgot-password

**Request:** `{ "email": "user@example.com" }`

### POST /auth/verify-otp

**Request:** `{ "email": "user@example.com", "otp": "123456", "new_password": "new" }`

### GET /auth/me

Return current authenticated user profile.

---

## Users APIs

Permission: `users.view`, `users.create`, `users.update`, `users.delete`

### GET /users

List users. Filters: `role`, `branch`, `is_active`, `search`.

### GET /users/{id}

Get user detail.

### POST /users

**Request:**
```json
{
  "username": "cashier1",
  "email": "cashier@example.com",
  "password": "secret",
  "first_name": "John",
  "last_name": "Doe",
  "role_id": "uuid",
  "branch_id": "uuid",
  "phone": "+1234567890",
  "is_active": true
}
```

### PUT /users/{id}

Update user (password optional).

### DELETE /users/{id}

Soft delete user.

### POST /users/{id}/activate

Reactivate deactivated user.

### POST /users/{id}/deactivate

Deactivate user.

---

## Roles APIs

Permission: `roles.view`, `roles.create`, `roles.update`, `roles.delete`

### GET /roles

List all roles with permission counts.

### GET /roles/{id}

Get role with assigned permissions.

### POST /roles

**Request:**
```json
{
  "name": "Custom Role",
  "slug": "custom_role",
  "description": "Description",
  "permission_ids": ["uuid1", "uuid2"]
}
```

### PUT /roles/{id}

Update role and permissions. System roles (`is_system=true`) cannot be deleted.

### DELETE /roles/{id}

Soft delete non-system role.

### GET /permissions

List all available permissions grouped by module.

---

## Branches APIs

Permission: `branches.view`, `branches.create`, `branches.update`, `branches.delete`

### GET /branches

List branches. Filter: `is_active`, `search`.

### GET /branches/{id}

Get branch detail with warehouse count.

### POST /branches

**Request:**
```json
{
  "name": "Downtown Store",
  "code": "BR02",
  "address": "123 Main St",
  "phone": "+1234567890",
  "email": "downtown@example.com",
  "is_active": true,
  "is_default": false
}
```

### PUT /branches/{id}

Update branch.

### DELETE /branches/{id}

Soft delete branch.

### POST /branches/{id}/set-default

Set branch as company default.

---

## Settings APIs

Permission: `settings.view`, `settings.update`

### GET /settings

List settings. Filter: `category` (general, company, pos, tax, security, backup, notifications).

### GET /settings/{key}

Get single setting by key.

### PUT /settings/{key}

**Request:**
```json
{
  "value": { "company_name": "Acme Retail", "tax_id": "12345" },
  "category": "company"
}
```

### GET /settings/company

Get company profile (aggregated from settings + companies table).

### PUT /settings/company

Update company profile.

**Request:**
```json
{
  "name": "Acme Retail Ltd",
  "legal_name": "Acme Retail Limited",
  "tax_id": "TAX-12345",
  "email": "info@acme.com",
  "phone": "+1234567890",
  "address": "123 Business Ave",
  "logo": "path/to/logo.png"
}
```

### GET /settings/pos

Get POS configuration.

### PUT /settings/pos

Update POS settings (receipt header, default payment method, barcode prefix, etc.).

### GET /settings/taxes

List configured taxes for current branch.

### GET /settings/security

Get security settings (session timeout, password policy).

### PUT /settings/security

Update security settings.

### POST /settings/backup/trigger

Trigger manual backup. Permission: `settings.backup`.

### GET /settings/backup/status

Get last backup status and history.

---

## Dashboard APIs

Permission: `dashboard.view`

### GET /dashboard/kpis

**Response:**
```json
{
  "success": true,
  "data": {
    "total_sales": 125000.00,
    "revenue": 98000.00,
    "profit": 32000.00,
    "expenses": 15000.00,
    "inventory_value": 450000.00,
    "period": "today"
  }
}
```

Query: `period` = today | week | month | year

### GET /dashboard/sales-trend

Sales trend data for charts. Query: `period`, `granularity` (day|week|month).

### GET /dashboard/recent-sales

Paginated recent sales for dashboard table.

### GET /dashboard/low-stock

Paginated low stock products.

### GET /dashboard/alerts

Active alerts (low stock, overdue invoices, pending approvals).

---

## Sync APIs (Offline)

Permission: authenticated + device registration

### POST /sync/register

Register desktop device for sync.

**Request:**
```json
{
  "device_id": "unique-device-uuid",
  "device_name": "POS Terminal 1",
  "branch_id": "uuid"
}
```

### GET /sync/status

**Response:**
```json
{
  "success": true,
  "data": {
    "last_sync_at": "2026-06-06T10:00:00Z",
    "pending_count": 0,
    "failed_count": 0,
    "server_version": "1.0.0"
  }
}
```

### POST /sync/pull

Pull server changes since last sync.

**Request:**
```json
{
  "device_id": "uuid",
  "last_sync_at": "2026-06-06T09:00:00Z",
  "entities": ["products", "inventory", "customers", "settings"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "synced_at": "2026-06-06T10:00:00Z",
    "changes": {
      "products": [],
      "inventory": [],
      "customers": [],
      "settings": []
    }
  }
}
```

### POST /sync/push

Push local changes to server.

**Request:**
```json
{
  "device_id": "uuid",
  "changes": [
    {
      "entity_type": "sale",
      "entity_id": "local-uuid",
      "operation": "create",
      "payload": {},
      "client_updated_at": "2026-06-06T09:30:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "accepted": ["local-uuid"],
    "conflicts": [],
    "failed": []
  }
}
```

### GET /sync/conflicts

List unresolved sync conflicts for device.

### POST /sync/conflicts/{id}/resolve

**Request:**
```json
{
  "resolution": "server_wins"
}
```

---

## Audit APIs

Permission: `audit.view`

### GET /audit/logs

List audit logs. Filters: `user`, `action`, `module`, `entity_type`, `date_from`, `date_to`.

Read-only. No create/update/delete.

---

## Notifications APIs

Permission: authenticated

### GET /notifications

List user notifications. Filter: `is_read`, `type`.

### GET /notifications/unread-count

**Response:** `{ "count": 5 }`

### POST /notifications/{id}/read

Mark notification as read.

### POST /notifications/read-all

Mark all notifications as read.

---

## Products APIs

Permission: `products.view`, `products.create`, `products.update`, `products.delete`

### GET /products

List products. Filters: `category`, `brand`, `is_active`, `search`.

### GET /products/{id}

### POST /products

### PUT /products/{id}

### DELETE /products/{id}

Soft delete.

### GET /products/search

Quick search for POS. Query: `q`, `limit` (default 20).

### GET /products/barcode/{barcode}

Lookup product by barcode.

---

## Categories APIs

### GET /categories

### POST /categories

### PUT /categories/{id}

### DELETE /categories/{id}

---

## Brands APIs

### GET /brands

### POST /brands

### PUT /brands/{id}

### DELETE /brands/{id}

---

## Inventory APIs

Permission: `inventory.view`, `inventory.adjust`, `inventory.transfer`

### GET /inventory

List inventory. Filters: `warehouse`, `product`, `low_stock`.

### GET /inventory/low-stock

### GET /inventory/out-of-stock

### POST /inventory/adjustments

### GET /inventory/adjustments

### POST /inventory/adjustments/{id}/confirm

### POST /inventory/transfers

### GET /inventory/transfers

### POST /inventory/transfers/{id}/receive

### POST /inventory/returns

---

## Sales APIs

### GET /sales

### GET /sales/{id}

### POST /sales

### POST /sales/{id}/cancel

### POST /sales/return

### GET /sales/reports

---

## POS APIs

Permission: `pos.access`

### POST /pos/cart

Validate cart items and calculate totals.

### POST /pos/checkout

Complete POS sale (draft → completed). Requires `X-Idempotency-Key`.

### POST /pos/payment

Record additional payment on partially paid sale.

### GET /pos/receipt/{sale_id}

Get receipt data for printing.

---

## Purchases APIs

### GET /purchases

### POST /purchases

### PUT /purchases/{id}

### POST /purchases/{id}/receive

### GET /purchase-orders

### POST /purchase-orders

### PUT /purchase-orders/{id}

### POST /purchase-orders/{id}/submit

### POST /purchase-orders/{id}/approve

---

## Customers APIs

### GET /customers

### POST /customers

### PUT /customers/{id}

### DELETE /customers/{id}

### GET /customers/{id}/credit

Get credit account balance and history.

---

## Suppliers APIs

### GET /suppliers

### POST /suppliers

### PUT /suppliers/{id}

### DELETE /suppliers/{id}

### GET /suppliers/{id}/balance

### POST /suppliers/{id}/payments

---

## Finance APIs

Permission: `finance.view`, `finance.create`

### GET /finance/dashboard

### GET /expenses

### POST /expenses

### GET /accounts

### POST /accounts

### GET /journal-entries

### POST /journal-entries

### GET /finance/cash-flow

### GET /finance/profit-analysis

---

## Reports APIs

Permission: `reports.view`, `reports.export`

### GET /reports/sales

Filters: `date_from`, `date_to`, `branch`, `customer`, `format` (json|pdf|excel|csv).

### GET /reports/inventory

### GET /reports/finance

### GET /reports/customers

### GET /reports/suppliers

### GET /reports/purchases

### GET /reports/profit

### GET /reports/tax

---

## API Rules

1. Always use pagination on list endpoints.
2. Always validate input server-side.
3. Never expose password hashes or internal fields.
4. Always enforce role permissions on backend.
5. Always return consistent `{ success, message, data/errors }` structure.
6. Soft deletes only — DELETE endpoints set `deleted_at`.
7. All write operations create audit log entries.
8. Financial calculations always performed server-side.
9. Rate limit: 100 requests/minute per user (auth endpoints: 10/minute).
10. Idempotency keys required for POS checkout and sync push.
