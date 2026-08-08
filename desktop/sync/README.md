# Offline Sync Engine

| Directory | Purpose |
|-----------|---------|
| `schema/` | SQLite schema mirroring server entities |
| `queue/` | Outbox types + pending operation contracts |
| `engine/` | Bridge to Django sync API (`/api/v1/sync/run/`) |
| `conflict/` | Conflict detection and resolution (future) |
| `bridge/` | Tauri commands exposing sync to React |

## STEP 29 — implemented foundation

- **Shop outbox:** Django model `SyncOutboxEntry` — POS checkout enqueues invoices for cloud upload
- **Cloud ingest receipts:** `SyncIngestReceipt` — replay-safe idempotency on `idempotency_key`
- **Finance rules:** `SyncFinancePolicy` — journal/ledger/expense keys rejected from shop push
- **API:** `GET /api/v1/sync/queue/` — pending counts + finance policy docs
- **UI:** `SyncQueueBadge` in desktop header when pending/failed > 0

## Offline Data Scope

Products, inventory, sales, customers, settings (per SYSTEM_ARCHITECTURE.md).

**Not synced from shop:** general ledger, journal entries, finance accounts (cloud/manual only).

## Sync Flow

1. Internet lost → sale saved locally → outbox entry `pending`
2. Connection restored → `POST /api/v1/sync/run/` pushes queued invoices (with idempotency keys)
3. Cloud confirms → outbox marked `synced`; ingest receipt prevents duplicates on replay
4. Conflicts → newest record wins (catalog), invoice idempotency wins (sales)
