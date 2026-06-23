import { useEffect, useRef } from "react";
import { loadDesktopConnection } from "@/config/connection";
import { syncApi } from "@/services/api/sync";
import { isTauri } from "@/utils/platform";
import { SYNC_REQUEST_EVENT } from "./syncEvents";

const SYNC_INTERVAL_MS = 5 * 60 * 1000;

export function CloudSyncManager() {
  const syncing = useRef(false);

  useEffect(() => {
    if (!isTauri()) return;

    const trySync = async () => {
      if (!navigator.onLine || syncing.current) return;
      syncing.current = true;
      try {
        await loadDesktopConnection();
        const cfg = await syncApi.config();
        const data = cfg.data;
        if (!data.cloud_api_base || !data.tenant_slug || !data.sync_secret) return;
        await syncApi.run();
      } catch {
        // Silent background sync — optional manual retry in Settings
      } finally {
        syncing.current = false;
      }
    };

    const onOnline = () => {
      void trySync();
    };

    const onSyncRequest = () => {
      void trySync();
    };

    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void trySync();
      }
    };

    window.addEventListener("online", onOnline);
    window.addEventListener(SYNC_REQUEST_EVENT, onSyncRequest);
    document.addEventListener("visibilitychange", onVisible);
    const timer = window.setInterval(() => {
      void trySync();
    }, SYNC_INTERVAL_MS);

    void loadDesktopConnection().then(() => trySync());

    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener(SYNC_REQUEST_EVENT, onSyncRequest);
      document.removeEventListener("visibilitychange", onVisible);
      window.clearInterval(timer);
    };
  }, []);

  return null;
}
