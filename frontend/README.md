# Frontend

React 19 + TypeScript desktop UI for Retail ERP & POS.

## Structure

- `src/app/` — Router, providers, root app
- `src/pages/` — Top-level route pages (auth, dashboard, admin)
- `src/modules/` — Feature modules (pos, products, inventory, etc.)
- `src/components/` — Shared UI (Shadcn + custom)
- `src/layouts/` — AppShell, Sidebar, Header
- `src/store/` — Zustand state stores
- `src/services/` — API client and offline services

## Design

Follow:

- `docs/ui/DESIGN_SYSTEM.md`
- `docs/product/UI_GUIDELINES.md`
- `docs/architecture/UI_ARCHITECTURE.md`

## Rules

- No business logic in components
- No financial calculations on frontend
- Dark mode required on all screens
- Max file size target: 300 lines
