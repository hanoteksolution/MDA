import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { syncApi } from "@/services/api/sync";
import { isTauri } from "@/utils/platform";

function formatSyncTime(iso: string) {
  if (!iso) return "never";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function FooterStatusBar() {
  const branch = useAuthStore((s) => s.user?.branch);
  const [syncLine, setSyncLine] = useState("");
  const online = typeof navigator !== "undefined" ? navigator.onLine : true;

  useEffect(() => {
    if (!isTauri()) return;
    const load = () => {
      syncApi
        .config()
        .then((res) => {
          const c = res.data;
          if (!c.cloud_api_base || !c.tenant_slug) {
            setSyncLine("Local only — cloud sync not configured");
            return;
          }
          const status = c.last_status === "success" ? "Synced" : c.last_status || "Pending";
          setSyncLine(`${status} ${formatSyncTime(c.last_sync_at)}`);
        })
        .catch(() => setSyncLine("Local mode"));
    };
    load();
    const id = window.setInterval(load, 60_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-card px-6 text-[11px] text-muted-foreground">
      <span>MDA Retail ERP v0.1.0 · Enterprise Edition</span>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${online ? "bg-success animate-pulse" : "bg-muted-foreground"}`}
          />
          {online ? "Online" : "Offline — local DB active"}
        </span>
        {isTauri() && syncLine && <span>{syncLine}</span>}
        {branch && (
          <span>
            {branch.name} ({branch.code})
          </span>
        )}
      </div>
    </footer>
  );
}
