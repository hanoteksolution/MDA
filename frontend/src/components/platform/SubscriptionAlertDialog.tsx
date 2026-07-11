import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Loader2, Lock, RefreshCw, Wifi, WifiOff, X } from "lucide-react";
import { Link } from "react-router-dom";
import { syncApi, type SubscriptionStatus } from "@/services/api/sync";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/cn";
import { requestCloudSync, SYNC_REQUEST_EVENT } from "@/components/desktop/syncEvents";
import { isTauri } from "@/utils/platform";

function dismissKey(subscriptionId: string): string {
  const today = new Date().toISOString().slice(0, 10);
  return `mda_sub_alert_dismissed_${subscriptionId}_${today}`;
}

/**
 * Soft warning (dismissible) + hard lock (blocks the app until sync after renewal).
 * Uses last cloud-synced subscription evaluated against the device clock — works offline.
 */
export function SubscriptionAlertDialog() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setStatus(null);
      setOpen(false);
      return;
    }
    try {
      const res = await syncApi.subscriptionStatus();
      const data = res.data;
      setStatus(data);

      if (data.locked) {
        setOpen(true);
        return;
      }

      if (!data.show_alert || !data.alert) {
        setOpen(false);
        return;
      }

      const id = data.alert.subscription_id || "unknown";
      if (sessionStorage.getItem(dismissKey(id))) {
        setOpen(false);
        return;
      }
      setOpen(true);
    } catch {
      setStatus(null);
      setOpen(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onSync = () => {
      void load();
    };
    window.addEventListener(SYNC_REQUEST_EVENT, onSync);
    window.addEventListener("online", onSync);
    return () => {
      window.removeEventListener(SYNC_REQUEST_EVENT, onSync);
      window.removeEventListener("online", onSync);
    };
  }, [load]);

  const dismiss = () => {
    if (status?.locked) return;
    if (status?.alert?.subscription_id) {
      sessionStorage.setItem(dismissKey(status.alert.subscription_id), "1");
    }
    setOpen(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      await syncApi.run();
      requestCloudSync();
      await load();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Sync failed. Check internet and connection settings.");
    } finally {
      setSyncing(false);
    }
  };

  if (!open || !status?.alert) {
    return null;
  }

  const alert = status.alert;
  const locked = status.locked;
  const isCritical = locked || alert.severity === "critical";
  const online = typeof navigator !== "undefined" ? navigator.onLine : true;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm">
      <div
        role="alertdialog"
        aria-labelledby="subscription-alert-title"
        aria-describedby="subscription-alert-desc"
        className="w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl"
      >
        <div className="flex items-start gap-4">
          <div
            className={`rounded-full p-2.5 ${
              locked
                ? "bg-destructive/15 text-destructive"
                : isCritical
                  ? "bg-destructive/15 text-destructive"
                  : "bg-amber-500/15 text-amber-600"
            }`}
          >
            {locked ? <Lock className="h-6 w-6" /> : <AlertTriangle className="h-6 w-6" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <h2 id="subscription-alert-title" className="text-lg font-semibold tracking-tight">
                {alert.title}
              </h2>
              {!locked && (
                <button
                  type="button"
                  onClick={dismiss}
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                  aria-label="Dismiss"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            {alert.tenant_name && (
              <p className="mt-1 text-sm font-medium text-primary">{alert.tenant_name}</p>
            )}
            <p id="subscription-alert-desc" className="mt-2 text-sm text-muted-foreground">
              {alert.message}
            </p>

            <dl className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div>
                <dt>Plan</dt>
                <dd className="font-medium text-foreground">{alert.plan}</dd>
              </div>
              <div>
                <dt>Reference</dt>
                <dd className="font-mono font-medium text-foreground">{alert.reference_code}</dd>
              </div>
              <div>
                <dt>Expires</dt>
                <dd className="font-medium text-foreground">{alert.expires_at ?? "—"}</dd>
              </div>
              <div>
                <dt>Monthly fee</dt>
                <dd className="font-medium text-foreground">{formatCurrency(alert.monthly_fee)}</dd>
              </div>
              {alert.grace_days_remaining != null && (
                <div>
                  <dt>Grace left</dt>
                  <dd className="font-medium text-foreground">{alert.grace_days_remaining} day(s)</dd>
                </div>
              )}
              <div>
                <dt>Device</dt>
                <dd className="flex items-center gap-1 font-medium text-foreground">
                  {online ? <Wifi className="h-3 w-3 text-emerald-600" /> : <WifiOff className="h-3 w-3" />}
                  {online ? "Online" : "Offline"}
                </dd>
              </div>
            </dl>

            {locked && (
              <ol className="mt-4 list-decimal space-y-1.5 pl-4 text-xs text-muted-foreground">
                <li>Owner renews payment on the cloud (Platform → Subscriptions).</li>
                <li>Connect this PC to the internet.</li>
                <li>Tap <strong className="text-foreground">Sync now</strong> below to unlock.</li>
              </ol>
            )}

            {syncError && (
              <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{syncError}</p>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
          {!locked && (
            <Button variant="secondary" onClick={dismiss}>
              I Understand
            </Button>
          )}
          {(isTauri() || locked) && (
            <Button variant="secondary" asChild>
              <Link to="/settings">Connection</Link>
            </Button>
          )}
          <Button onClick={handleSync} disabled={syncing || !online}>
            {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Sync now
          </Button>
        </div>
      </div>
    </div>
  );
}
