export const SYNC_REQUEST_EVENT = "mda-sync-request";

/** Ask the background sync manager to run immediately (e.g. after saving cloud settings). */
export function requestCloudSync(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(SYNC_REQUEST_EVENT));
  }
}
