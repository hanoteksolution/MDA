# Database Migration Plan

**Principle:** additive migrations only. Never destroy accounting history or tenant rows.

## No new tables required for increment (this phase)

Workspace activation remains `TenantModule` + features. FE derives workspaces.

## Later (only when needed)

| Change | Why | Risk |
|---|---|---|
| `TenantWorkspace` / capability / feature tables | Server-driven nav + labels | M — dual source with TenantModule |
| Product industry attributes (or JSON profile) | Pharmacy/restaurant/gym fields without new product tables | L |
| `AuditLog.tenant_id` stamp on create | Isolation | L |
| `customers.delete` / `suppliers.delete` Permission rows | Catalog gap | L |
| Futsal: deprecate `FutsalLedgerEntry` after Invoice backfill | One books | H — migrate then freeze old table |
| Finance as optional `Module` seed | Entitlement visibility | L |
| Property: collapse housing/office TenantModules into features | One Property workspace | M — entitlement remap |
| Journal reverse metadata (`reversed_by`, `reverses_id`) if missing | API reverse | L |

## Constraints to add when touching models

Unique `(tenant_id, sku)`, `(tenant_id, room.code)`, `(tenant_id, batch_number+product)` where not already present. Lease overlap exclusion. Reservation double-book exclusion (hotel already enforces in service).

## Rollback

Every migration reversible. No data wipe. Soft-delete / archive over hard delete for masters with history.
