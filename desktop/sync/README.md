# Offline Sync Engine

| Directory | Purpose |
|-----------|---------|
| `schema/` | SQLite schema mirroring server entities |
| `queue/` | Pending sync operations queue |
| `engine/` | Background sync worker |
| `conflict/` | Conflict detection and resolution |
| `bridge/` | Tauri commands exposing sync to React |

## Offline Data Scope

Products, inventory, sales, customers, settings (per SYSTEM_ARCHITECTURE.md).

## Sync Flow

1. Internet lost → save to SQLite → queue transaction
2. Connection restored → sync engine pushes queued changes
3. Server confirms → mark synced
4. Conflicts → newest record wins, audit conflict event
