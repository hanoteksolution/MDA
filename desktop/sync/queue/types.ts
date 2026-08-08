/** Sync outbox types aligned with backend SyncOutboxEntry (STEP 29). */

export type OutboxStatus = "pending" | "synced" | "failed";
export type OutboxResource = "invoice" | "customer" | "inventory";

export interface OutboxEntry {
  id: string;
  resource_type: OutboxResource;
  resource_id: string;
  idempotency_key?: string;
  payload?: Record<string, unknown>;
  status: OutboxStatus;
  attempts: number;
  last_error?: string;
  created_at: string;
}

export interface OutboxSummary {
  pending: number;
  failed: number;
  synced: number;
  total: number;
}
