# Offline Sync Architecture

> **Status:** Planned — placeholder created during structure phase.  
> See [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) for gaps to resolve before implementation.

## Overview

The desktop client uses SQLite for local storage and a background sync engine to reconcile with PostgreSQL when connectivity is restored.

## Principles

- No transaction loss
- Newest record wins (`updated_at` comparison)
- Audit all conflict events
- Retry failed synchronizations with backoff

## Components

| Component | Location |
|-----------|----------|
| SQLite schema | `desktop/sync/schema/` |
| Sync queue | `desktop/sync/queue/` |
| Sync engine | `desktop/sync/engine/` |
| Conflict resolver | `desktop/sync/conflict/` |
| Tauri bridge | `desktop/sync/bridge/` |

## Offline Data Scope

- Products (read cache)
- Inventory (read + local delta)
- Sales / POS transactions (write queue)
- Customers (read + local create)
- Settings (read cache)

## To Be Defined

- [ ] Full SQLite table definitions
- [ ] Sync API endpoints (`/api/v1/sync/push`, `/pull`, `/status`)
- [ ] Stock conflict handling (server authority vs client)
- [ ] Offline authentication token refresh
- [ ] Partial vs full sync triggers
- [ ] Retry policy (intervals, max attempts)
