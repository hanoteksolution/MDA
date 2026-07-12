import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Copy,
  Loader2,
  Lock,
  RefreshCw,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";
import { syncApi, type SubscriptionStatus } from "@/services/api/sync";
import { platformApi } from "@/services/api/platform";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatCurrency } from "@/utils/cn";
import { requestCloudSync, SYNC_REQUEST_EVENT } from "@/components/desktop/syncEvents";
import { isTauri } from "@/utils/platform";
import { generateQrDataUrl } from "@/modules/pos/receipt/receiptAssets";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { appDialog } from "@/components/feedback/AppDialog";

function dismissKey(subscriptionId: string): string {
  const today = new Date().toISOString().slice(0, 10);
  return `mda_sub_alert_dismissed_${subscriptionId}_${today}`;
}

/**
 * Soft warning (dismissible) + hard lock (blocks the app until sync after renewal).
 * Shows Waafi/EVC merchant QR + tracks payment for automatic renewal.
 */
export function SubscriptionAlertDialog() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [payerPhone, setPayerPhone] = useState("");
  const [reporting, setReporting] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState<string | null>(null);
  const [tracking, setTracking] = useState(false);

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
    void load();
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

  // While alert/lock is open, poll for auto-renewal / payment confirmation
  useAutoRefresh(
    async () => {
      if (!open || !status?.alert?.subscription_id) return;
      try {
        if (tracking || status.locked) {
          let confirmed = false;
          let statusLabel: string | null = null;
          if (isTauri() || status.source === "sync") {
            const payRes = await syncApi.paymentStatus();
            statusLabel = payRes.data.payment?.status ?? null;
            confirmed = Boolean(
              payRes.data.payment?.status === "confirmed" ||
                payRes.data.is_payment_current ||
                payRes.data.subscription_usable
            );
          } else {
            const payRes = await platformApi.subscriptionPaymentStatus(status.alert.subscription_id);
            statusLabel = payRes.data.payment?.status ?? null;
            confirmed = Boolean(
              payRes.data.payment?.status === "confirmed" || payRes.data.subscription?.is_payment_current
            );
          }
          if (statusLabel) setPaymentStatus(statusLabel);
          if (confirmed) {
            setTracking(false);
            try {
              if (isTauri()) {
                await syncApi.run();
                requestCloudSync();
              }
            } catch {
              /* sync optional */
            }
            await load();
            await appDialog.alert("Payment confirmed. Subscription renewed automatically.", {
              title: "Subscription renewed",
              tone: "success",
            });
          }
        }
      } catch {
        /* keep polling */
      }
      await load();
    },
    { intervalMs: open ? 8_000 : 0, enabled: open, onFocus: true, onVisible: true }
  );

  useEffect(() => {
    let cancelled = false;
    const payment = status?.alert?.payment;
    if (!payment) {
      setQrUrl(null);
      return;
    }
    // Always encode dialable USSD with plan amount (tel:*789*merchant*amount%23)
    const payload = payment.qr_payload || payment.ussd_code;
    if (!payload) {
      setQrUrl(null);
      return;
    }
    generateQrDataUrl(payload, 220)
      .then((url) => {
        if (!cancelled) setQrUrl(url);
      })
      .catch(() => {
        if (!cancelled) setQrUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [status?.alert?.payment]);

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

  const copyText = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      await appDialog.alert(`${label} copied.`, { tone: "success", title: "Copied" });
    } catch {
      await appDialog.alert(value, { title: label });
    }
  };

  const handleReportPaid = async () => {
    if (!status?.alert?.subscription_id) return;
    setReporting(true);
    try {
      const payload = {
        payer_phone: payerPhone.trim(),
        notes: "Paid via Waafi/EVC from subscription alert",
      };
      if (isTauri() || status.source === "sync") {
        const res = await syncApi.reportPayment(payload);
        setPaymentStatus(res.data.payment.status);
      } else {
        const res = await platformApi.reportSubscriptionPayment(status.alert.subscription_id, payload);
        setPaymentStatus(res.data.payment.status);
      }
      setTracking(true);
      await appDialog.alert(
        "Payment reported. We are tracking it online — subscription renews automatically when confirmed.",
        { title: "Tracking payment", tone: "success" }
      );
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not report payment.", {
        tone: "danger",
      });
    } finally {
      setReporting(false);
    }
  };

  if (!open || !status?.alert) {
    return null;
  }

  const alert = status.alert;
  const payment = alert.payment;
  const locked = status.locked;
  const isCritical = locked || alert.severity === "critical";
  const online = typeof navigator !== "undefined" ? navigator.onLine : true;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm">
      <div
        role="alertdialog"
        aria-labelledby="subscription-alert-title"
        aria-describedby="subscription-alert-desc"
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
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

            {payment && (
              <div className="mt-5 overflow-hidden rounded-xl border border-border/70">
                <div className="grid grid-cols-2">
                  <div className="bg-emerald-600 px-3 py-2 text-center text-xs font-semibold text-white">
                    Waafi
                  </div>
                  <div className="bg-sky-600 px-3 py-2 text-center text-xs font-semibold text-white">
                    EVC Plus
                  </div>
                </div>
                <div className="space-y-3 bg-muted/30 p-4">
                  <div className="text-center">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {payment.company_name || "SAFARI TECHNOLOGY SOLUTIONS"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {payment.provider_label || "Waafi / EVC Plus"}
                    </p>
                  </div>
                  <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start sm:justify-center">
                    {qrUrl ? (
                      <img
                        src={qrUrl}
                        alt="Scan to dial subscription USSD"
                        className="h-44 w-44 rounded-lg border border-border bg-white p-2"
                      />
                    ) : (
                      <div className="flex h-44 w-44 items-center justify-center rounded-lg border border-dashed border-border text-xs text-muted-foreground">
                        QR unavailable
                      </div>
                    )}
                    <div className="min-w-[9rem] space-y-2 text-center sm:text-left">
                      <div>
                        <p className="text-[11px] uppercase text-muted-foreground">Merchant No.</p>
                        <p className="text-3xl font-bold tracking-tight text-foreground">
                          {payment.merchant_number || "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] uppercase text-muted-foreground">Plan amount</p>
                        <p className="text-lg font-semibold text-foreground">
                          {formatCurrency(payment.amount || alert.monthly_fee)}
                        </p>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Scan to auto-dial USSD with this amount
                      </p>
                      <div>
                        <p className="text-[11px] uppercase text-muted-foreground">Pay reference</p>
                        <p className="break-all font-mono text-xs font-medium text-foreground">
                          {payment.payment_reference}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap justify-center gap-2">
                    {payment.merchant_number && (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => copyText(payment.merchant_number, "Merchant number")}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy merchant
                      </Button>
                    )}
                    {payment.ussd_code && (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => copyText(payment.ussd_code, "USSD code")}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy USSD
                      </Button>
                    )}
                  </div>

                  {payment.ussd_code && (
                    <p className="rounded-lg bg-background/80 px-3 py-2 text-center font-mono text-sm font-semibold text-foreground">
                      {payment.ussd_code}
                    </p>
                  )}

                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {payment.instructions_title || "How to pay"}
                    </p>
                    <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
                      {(payment.instructions?.length
                        ? payment.instructions
                        : [
                            "Scan the QR — phone dials *789*merchant*amount# automatically",
                            "Confirm the payment in Waafi / EVC Plus",
                            "Or dial the USSD code below manually",
                          ]
                      ).map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                    {payment.contact_phone && (
                      <p className="mt-2 text-xs text-muted-foreground">{payment.contact_phone}</p>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-border/60 pt-3">
                    <label className="text-xs font-medium text-foreground">
                      Your EVC / Waafi phone (optional)
                    </label>
                    <Input
                      value={payerPhone}
                      onChange={(e) => setPayerPhone(e.target.value)}
                      placeholder="61xxxxxxx"
                    />
                    <Button
                      type="button"
                      className="w-full"
                      loading={reporting}
                      disabled={!online}
                      onClick={handleReportPaid}
                    >
                      I paid — track & auto-renew
                    </Button>
                    {(tracking || paymentStatus) && (
                      <p className="text-center text-xs text-muted-foreground">
                        Tracking online
                        {paymentStatus ? ` · status: ${paymentStatus}` : ""}
                        {payment.auto_renew_enabled ? " · auto-renew enabled" : ""}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {locked && !payment && (
              <ol className="mt-4 list-decimal space-y-1.5 pl-4 text-xs text-muted-foreground">
                <li>Pay the monthly fee to the merchant number above (or Platform → Subscriptions).</li>
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
