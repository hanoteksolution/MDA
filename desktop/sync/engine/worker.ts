/**
 * Sync worker bridge — desktop UI triggers Django `/api/v1/sync/run/`.
 * The authoritative outbox lives in the local Django DB (sync_outbox_entries).
 */

import { requestCloudSync } from "@/components/desktop/syncEvents";
import { syncApi } from "@/services/api/sync";

export async function runCloudSync(): Promise<void> {
  requestCloudSync();
  await syncApi.run();
}

export async function fetchQueueStatus() {
  const res = await syncApi.queue();
  return res.data;
}
