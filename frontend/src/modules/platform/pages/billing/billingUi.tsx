import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { appDialog } from "@/components/feedback/AppDialog";
import { platformBillingApi, type BillingPage, type BillingQuery } from "@/services/api/platformBilling";

type Tone = NonNullable<BadgeProps["variant"]>;

const TONES: Record<string, Tone> = {
  active: "success",
  current: "success",
  confirmed: "success",
  paid: "success",
  succeeded: "success",
  resolved: "success",
  trial: "default",
  sent: "default",
  no_billing: "secondary",
  draft: "secondary",
  pending: "warning",
  due_soon: "warning",
  review: "warning",
  open: "warning",
  on_hold: "warning",
  expired: "destructive",
  overdue: "destructive",
  failed: "destructive",
  suspended: "destructive",
  cancelled: "secondary",
};

export const humanize = (value: string | null | undefined) =>
  value ? value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—";

export function BillingBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  return <Badge variant={TONES[status] ?? "outline"}>{humanize(status)}</Badge>;
}

/** Decimal strings from the API are shown as-is (no float rounding); missing values stay "—". */
export function money(amount: string | null | undefined, currency?: string | null) {
  if (amount === null || amount === undefined || amount === "") return "—";
  return currency ? `${currency} ${amount}` : amount;
}

export function date(value: string | null | undefined) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return value.length > 10 ? d.toLocaleString() : d.toLocaleDateString();
}

export const option = (value: string, label = humanize(value)) => ({ value, label });

/**
 * Server-paged table state kept in the URL (search, filters, page), so a filtered view survives
 * reloads and can be shared. `load` is re-run whenever the relevant params change.
 */
export function useBillingTable<T>(load: (params: BillingQuery) => Promise<{ data: BillingPage<T> }>, keys: string[]) {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<BillingPage<T>>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState(params.get("search") ?? "");
  const [reload, setReload] = useState(0);

  const query: BillingQuery = { page: params.get("page") ?? undefined, page_size: params.get("page_size") ?? "25", search: params.get("search") ?? undefined };
  keys.forEach((k) => (query[k] = params.get(k) ?? undefined));
  const signature = JSON.stringify(query);

  const set = (key: string, value: string) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.delete("page");
      return next;
    });

  useEffect(() => {
    const t = setTimeout(() => {
      if (search !== (params.get("search") ?? "")) set("search", search);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    load(query)
      .then((r) => active && setData(r.data))
      .catch((e: unknown) => {
        if (!active) return;
        setData(undefined);
        setError(e instanceof Error ? e.message : "Could not load billing data.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, reload]);

  return {
    rows: data?.results ?? [],
    loading,
    error,
    refresh: () => setReload((v) => v + 1),
    filter: (key: string) => ({ value: params.get(key) ?? "", onChange: (v: string) => set(key, v) }),
    table: {
      loading,
      page: data?.page ?? Number(params.get("page") || 1),
      pageSize: Number(params.get("page_size") || 25),
      total: data?.count ?? 0,
      onPageChange: (p: number) => set("page", String(p)),
      onPageSizeChange: (s: number) => set("page_size", String(s)),
      searchValue: search,
      onSearchChange: setSearch,
    },
  };
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Exceptional manual recovery (Super Admin only): extends one billing period, requires a reason and an
 * explicit acknowledgement, is audited server-side, and never records or fakes a payment.
 */
export function RecoveryDialog({
  target,
  onClose,
  onDone,
}: {
  target: { id: string; label: string } | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reason, setReason] = useState("");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setReason("");
    setAck(false);
  }, [target?.id]);
  const valid = reason.trim().length >= 10 && ack;

  const submit = async () => {
    if (!target || !valid) return;
    setBusy(true);
    try {
      await platformBillingApi.recover(target.id, reason.trim());
      onClose();
      onDone();
      await appDialog.alert("Subscription extended by one billing period. No payment was recorded.", { title: "Recovery applied", tone: "success" });
    } catch (e) {
      await appDialog.alert(e instanceof Error ? e.message : "Recovery failed.", { title: "Recovery failed", tone: "danger" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <PlatformConfirmDialog
      open={Boolean(target)}
      title="Manual subscription recovery"
      description={`Extend ${target?.label ?? "this subscription"} by one billing period and mark it active. This is an exceptional, audited action: it does not record a payment, invoice or receipt.`}
      confirmLabel="Apply recovery"
      loading={busy}
      confirmDisabled={!valid}
      onConfirm={() => void submit()}
      onCancel={onClose}
    >
      <div className="space-y-3">
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">Reason (recorded in the audit log)</span>
          <textarea
            className="min-h-[88px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            value={reason}
            maxLength={300}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Provider outage on 2026-09-20 — payment verified by phone with finance"
          />
          {reason.trim().length > 0 && reason.trim().length < 10 && (
            <span className="text-xs text-destructive">At least 10 characters.</span>
          )}
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5" checked={ack} onChange={(e) => setAck(e.target.checked)} />
          <span>I understand no payment is recorded and this action is audited under my name.</span>
        </label>
      </div>
    </PlatformConfirmDialog>
  );
}
