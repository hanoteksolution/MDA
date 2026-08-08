import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Lock } from "lucide-react";
import { platformApi, type TenantEntitlements } from "@/services/api/platform";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";

export function SubscriptionPaywallBanner() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [entitlements, setEntitlements] = useState<TenantEntitlements | null>(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setEntitlements(null);
      return;
    }
    try {
      const res = await platformApi.entitlements();
      setEntitlements(res.data ?? null);
    } catch {
      setEntitlements(null);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!entitlements?.has_subscription) return null;

  const phase = entitlements.phase;
  const show =
    phase === "warning" ||
    phase === "grace" ||
    phase === "expired" ||
    phase === "suspended" ||
    !entitlements.can_write;

  if (!show) return null;

  const locked = !entitlements.can_write;
  const title = locked
    ? "Subscription expired — read-only mode"
    : phase === "grace"
      ? "Grace period — renew soon"
      : "Subscription payment due";

  const message = locked
    ? "You can view your data but cannot make changes until you renew. Nothing has been deleted."
    : entitlements.grace_days_remaining != null
      ? `${entitlements.grace_days_remaining} grace day(s) remaining. Renew to avoid lockout.`
      : entitlements.days_until_expiry != null
        ? `${entitlements.days_until_expiry} day(s) until expiry on plan ${entitlements.plan_name ?? entitlements.plan_code}.`
        : "Renew your subscription to keep full access.";

  return (
    <div
      className={cn(
        "flex shrink-0 items-center gap-3 border-b px-4 py-2.5 text-sm",
        locked
          ? "border-destructive/30 bg-destructive/10 text-destructive"
          : "border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-100"
      )}
      role="status"
    >
      {locked ? (
        <Lock className="h-4 w-4 shrink-0" />
      ) : (
        <AlertTriangle className="h-4 w-4 shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <p className="font-medium leading-snug">{title}</p>
        <p className="text-xs opacity-90">{message}</p>
      </div>
      <Button
        type="button"
        size="sm"
        variant={locked ? "destructive" : "secondary"}
        onClick={() => window.dispatchEvent(new CustomEvent("mda:open-subscription-alert"))}
      >
        Renew
      </Button>
    </div>
  );
}
