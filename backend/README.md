# Backend

Django REST API — modular monolith with Clean Architecture.

## Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API | `api/v1/` | Thin views, routing, serializers |
| Services | `services/` + `apps/*/services/` | Business logic |
| Repositories | `repositories/` + `apps/*/repositories/` | Database access |
| Models | `apps/*/models/` | Django ORM models |
| Permissions | `permissions/` + `apps/*/permissions/` | Authorization |

## Django Apps

- `authentication` — JWT, users, roles, permissions
- `products` — categories, brands, products
- `inventory` — warehouses, stock, adjustments, transfers
- `purchases` — purchase orders, receiving
- `sales` — POS, sales, invoices, quotations, receipts
- `customers` — profiles, credit accounts
- `suppliers` — supplier management, balances
- `finance` — accounts, journal entries, expenses
- `reports` — report generation and export
- `notifications` — alerts and system notifications
- `audit` — activity and security logs
- `settings_app` — company, branches, taxes, system config

## Rules

- Business logic never in views
- All financial calculations on backend
- All endpoints enforce permissions
- Follow `docs/architecture/DATABASE_SCHEMA.md`
