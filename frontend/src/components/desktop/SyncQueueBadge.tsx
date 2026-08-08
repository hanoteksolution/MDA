import { useCallback, useEffect, useState } from "react";
import { CloudOff, RefreshCw } from "lucide-react";

import { requestCloudSync } from "@/components/desktop/syncEvents";
import { syncApi, type SyncQueueSummary } from "@/services/api/sync";
import { isTauri } from "@/utils/platform";
import { cn } from "@/utils/cn";

export function SyncQueueBadge({ compact }: { compact?: boolean }) {
  const [summary, setSummary] = useState<SyncQueueSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!isTauri()) return;
    try {
      const res = await syncApi.queue();
      setSummary(res.data.summary);
    } catch {
      setSummary(null);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  if (!isTauri() || !summary) return null;

  const pending = summary.pending + summary.failed;
  if (pending === 0) return null;

  const handleSync = async () => {
    setLoading(true);
    try {
      requestCloudSync();
      await syncApi.run();
      await load();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void handleSync()}
      disabled={loading}
      title="Sync pending sales to cloud"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs font-medium transition-colors",
        summary.failed > 0
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        compact && "px-2 py-1"
      )}
    >
      {loading ? (
        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <CloudOff className="h-3.5 w-3.5" />
      )}
      {pending > 0 ? `${pending} pending` : "Sync"}
    </button>
  );
}
