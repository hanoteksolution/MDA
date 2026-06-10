# Project Structure

Enterprise Retail ERP & POS Desktop Application

This document defines the complete repository layout. Implementation code will be added in subsequent phases per `docs/product/FEATURE_ROADMAP.md`.

---

## Repository Root

```
MDA/
├── agent.md                          # Agent instructions (source of truth)
├── README.md                         # Project overview and setup (future)
├── PROJECT_STRUCTURE.md              # This file
├── .cursor/
│   └── rules/
│       └── master-prompt.md          # Cursor AI master prompt
├── .github/
│   └── workflows/                    # CI/CD pipelines
├── docs/                             # All project documentation
├── backend/                          # Django REST API
├── frontend/                         # React + TypeScript UI
├── desktop/                          # Tauri desktop shell + offline sync
├── infrastructure/                   # Docker, deployment, scripts
└── shared/                           # Shared types, constants, contracts
```

---

## Documentation (`docs/`)

```
docs/
├── architecture/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_ERD.md
│   ├── DATABASE_SCHEMA.md
│   ├── UI_ARCHITECTURE.md
│   ├── MISSING_REQUIREMENTS.md       # Gap analysis
│   ├── OFFLINE_SYNC.md               # (planned)
│   └── DEPLOYMENT.md                 # (planned)
├── product/
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── FEATURE_ROADMAP.md
│   └── UI_GUIDELINES.md
├── workflows/
│   ├── BUSINESS_RULES.md
│   ├── DOCUMENT_LIFECYCLE.md         # (planned)
│   └── TAX_AND_PRICING.md            # (planned)
├── api/
│   └── API_SPECIFICATION.md
└── ui/
    └── DESIGN_SYSTEM.md
```

---

## Backend (`backend/`)

Django modular monolith with Clean Architecture layers.

```
backend/
├── README.md
├── manage.py                         # (implementation phase)
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── config/
│   ├── __init__.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   ├── celery.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── development.py
│       ├── production.py
│       └── test.py
├── apps/
│   ├── authentication/
│   ├── products/
│   ├── inventory/
│   ├── purchases/
│   ├── sales/
│   ├── customers/
│   ├── suppliers/
│   ├── finance/
│   ├── reports/
│   ├── notifications/
│   ├── audit/
│   └── settings_app/
├── core/
│   ├── models/
│   ├── mixins/
│   ├── exceptions/
│   ├── pagination/
│   ├── responses/
│   └── validators/
├── repositories/
├── services/
├── api/
│   └── v1/
│       ├── urls.py
│       ├── auth/
│       ├── products/
│       ├── inventory/
│       ├── sales/
│       ├── pos/
│       ├── purchases/
│       ├── customers/
│       ├── suppliers/
│       ├── finance/
│       ├── reports/
│       ├── users/
│       ├── notifications/
│       ├── audit/
│       └── settings/
├── permissions/
├── utils/
├── tasks/                            # Celery tasks
├── fixtures/                         # Seed data
├── migrations/                       # Shared migration helpers
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### Per-App Internal Structure

Each Django app under `apps/` follows:

```
apps/{app_name}/
├── __init__.py
├── apps.py
├── models/
├── serializers/
├── admin.py
├── urls.py
├── repositories/
├── services/
├── permissions/
└── tests/
```

---

## Frontend (`frontend/`)

React 19 + TypeScript + Shadcn UI + Tailwind CSS + Zustand.

```
frontend/
├── README.md
├── package.json                      # (implementation phase)
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── components.json                   # Shadcn config
├── index.html
├── public/
│   └── assets/
└── src/
    ├── main.tsx
    ├── app/
    │   ├── App.tsx
    │   ├── router.tsx
    │   └── providers.tsx
    ├── pages/
    │   ├── auth/
    │   │   ├── LoginPage.tsx
    │   │   ├── ForgotPasswordPage.tsx
    │   │   └── VerifyOtpPage.tsx
    │   ├── dashboard/
    │   │   └── DashboardPage.tsx
    │   ├── errors/
    │   │   ├── NotFoundPage.tsx
    │   │   ├── ForbiddenPage.tsx
    │   │   └── OfflinePage.tsx
    │   └── admin/
    │       ├── UsersPage.tsx
    │       ├── RolesPage.tsx
    │       └── ActivityLogsPage.tsx
    ├── modules/
    │   ├── pos/
    │   │   ├── components/
    │   │   ├── hooks/
    │   │   ├── services/
    │   │   ├── pages/
    │   │   └── types/
    │   ├── products/
    │   ├── inventory/
    │   ├── purchases/
    │   ├── sales/
    │   ├── customers/
    │   ├── suppliers/
    │   ├── finance/
    │   ├── reports/
    │   ├── notifications/
    │   └── settings/
    ├── components/
    │   ├── ui/                       # Shadcn primitives
    │   ├── common/
    │   │   ├── DataTable/
    │   │   ├── PageHeader/
    │   │   ├── KpiCard/
    │   │   ├── ConfirmDialog/
    │   │   ├── EmptyState/
    │   │   └── LoadingSkeleton/
    │   └── forms/
    ├── layouts/
    │   ├── AppShell/
    │   ├── AuthLayout/
    │   ├── Sidebar/
    │   ├── Header/
    │   ├── FooterStatusBar/
    │   └── NotificationDrawer/
    ├── services/
    │   ├── api/
    │   │   ├── client.ts
    │   │   └── endpoints/
    │   └── offline/
    ├── hooks/
    ├── store/
    │   ├── authStore.ts
    │   ├── uiStore.ts
    │   ├── productStore.ts
    │   ├── inventoryStore.ts
    │   ├── salesStore.ts
    │   └── financeStore.ts
    ├── types/
    │   ├── api/
    │   ├── models/
    │   └── dto/
    ├── utils/
    └── styles/
        ├── globals.css
        └── themes/
```

---

## Desktop (`desktop/`)

Tauri wrapper with offline SQLite and sync engine.

```
desktop/
├── README.md
├── package.json                      # (implementation phase)
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs
│   │   └── commands/
│   └── icons/
└── sync/
    ├── README.md
    ├── schema/                       # SQLite schema definitions
    ├── queue/                        # Sync queue manager
    ├── engine/                       # Background sync engine
    ├── conflict/                     # Conflict resolution
    └── bridge/                       # Tauri ↔ frontend bridge
```

---

## Infrastructure (`infrastructure/`)

```
infrastructure/
├── README.md
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── nginx/
│   └── nginx.conf
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   ├── seed.sh
│   └── migrate.sh
└── monitoring/
    └── README.md
```

---

## Shared (`shared/`)

Cross-cutting contracts between backend, frontend, and desktop.

```
shared/
├── README.md
├── constants/
│   ├── modules.ts
│   ├── roles.ts
│   ├── permissions.ts
│   └── document-status.ts
└── schemas/                          # JSON Schema / OpenAPI fragments
```

---

## Module-to-Directory Mapping

| Module | Backend App | Frontend Module | API Prefix |
|--------|-------------|-----------------|------------|
| Dashboard | reports + services | pages/dashboard | /api/v1/dashboard |
| POS | sales (pos) | modules/pos | /api/v1/pos |
| Products | products | modules/products | /api/v1/products |
| Inventory | inventory | modules/inventory | /api/v1/inventory |
| Purchases | purchases | modules/purchases | /api/v1/purchases |
| Sales | sales | modules/sales | /api/v1/sales |
| Customers | customers | modules/customers | /api/v1/customers |
| Suppliers | suppliers | modules/suppliers | /api/v1/suppliers |
| Finance | finance | modules/finance | /api/v1/finance |
| Reports | reports | modules/reports | /api/v1/reports |
| Users | authentication | pages/admin | /api/v1/users |
| Roles | authentication | pages/admin | /api/v1/roles |
| Settings | settings_app | modules/settings | /api/v1/settings |
| Notifications | notifications | modules/notifications | /api/v1/notifications |
| Audit Logs | audit | pages/admin | /api/v1/audit |

---

## Development Phases (from FEATURE_ROADMAP)

Structure supports incremental delivery:

1. **Phase 1** — `backend/config`, `authentication`, `settings_app`, `frontend/layouts`, auth pages
2. **Phase 2** — `products`, `inventory` apps and modules
3. **Phase 3** — `purchases`, `suppliers`
4. **Phase 4** — `modules/pos`, `desktop/sync`
5. **Phase 5–8** — sales, customers, finance, reports
6. **Phase 9** — `desktop/sync` full engine
7. **Phase 10** — audit, notifications, infrastructure, optimization
