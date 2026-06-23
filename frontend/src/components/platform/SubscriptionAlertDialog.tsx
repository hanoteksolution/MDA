import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { platformApi, type SubscriptionAlert } from "@/services/api/platform";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/cn";

function dismissKey(alert: SubscriptionAlert): string {
  const today = new Date().toISOString().slice(0, 10);
  return `mda_sub_alert_dismissed_${alert.subscription_id}_${today}`;
}

export function SubscriptionAlertDialog() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [alert, setAlert] = useState<SubscriptionAlert | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setAlert(null);
      setOpen(false);
      return;
    }

    platformApi
      .mySubscriptionAlert()
      .then((res) => {
        const data = res.data;
        if (!data) {
          setAlert(null);
          setOpen(false);
          return;
        }
        if (sessionStorage.getItem(dismissKey(data))) {
          setAlert(null);
          setOpen(false);
          return;
        }
        setAlert(data);
        setOpen(true);
      })
      .catch(() => {
        setAlert(null);
        setOpen(false);
      });
  }, [isAuthenticated]);

  const dismiss = () => {
    if (alert) {
      sessionStorage.setItem(dismissKey(alert), "1");
    }
    setOpen(false);
  };

  if (!open || !alert) {
    return null;
  }

  const isCritical = alert.severity === "critical";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4">
      <div
        role="alertdialog"
        aria-labelledby="subscription-alert-title"
        aria-describedby="subscription-alert-desc"
        className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl"
      >
        <div className="flex items-start gap-4">
          <div
            className={`rounded-full p-2 ${
              isCritical ? "bg-destructive/15 text-destructive" : "bg-amber-500/15 text-amber-600"
            }`}
          >
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-start justify-between gap-2">
              <h2 id="subscription-alert-title" className="text-lg font-semibold">
                {alert.title}
              </h2>
              <button
                type="button"
                onClick={dismiss}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
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
              {alert.contact_user_name && (
                <div>
                  <dt>Contact</dt>
                  <dd className="font-medium text-foreground">{alert.contact_user_name}</dd>
                </div>
              )}
              <div>
                <dt>Last paid</dt>
                <dd className="font-medium text-foreground">{alert.last_paid_at ?? "Never"}</dd>
              </div>
            </dl>
          </div>
        </div>
        <div className="mt-6 flex justify-end">
          <Button onClick={dismiss}>I Understand</Button>
        </div>
      </div>
    </div>
  );
}
