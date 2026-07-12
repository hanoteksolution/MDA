import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CircleCheck,
  ClipboardList,
  Loader2,
  PauseCircle,
  UserCheck,
  Wallet,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  posApi,
  type PosWaiterSale,
  type WaiterPerformanceData,
  type WaiterPerformanceRow,
} from "@/services/api/pos";
import { type HeldSale } from "@/modules/pos/hooks/usePosCart";
import { cn, formatCurrency } from "@/utils/cn";
import { salesApi } from "@/services/api/sales";
import { appDialog } from "@/components/feedback/AppDialog";

const HELD_KEY = "mda_pos_held";

type ReceiptFilter = "all" | "paid" | "unpaid" | "on_account";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function monthStartIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function loadHeldSales(): HeldSale[] {
  try {
    const raw = localStorage.getItem(HELD_KEY);
    return raw ? (JSON.parse(raw) as HeldSale[]) : [];
  } catch {
    return [];
  }
}

function statusVariant(status: string): "success" | "warning" | "secondary" | "destructive" {
  if (status === "paid") return "success";
  if (status === "overdue" || status === "cancelled") return "destructive";
  return "warning";
}

export function WaiterPerformancePage() {
  const [dateFrom, setDateFrom] = useState(monthStartIso);
  const [dateTo, setDateTo] = useState(todayIso);
  const [data, setData] = useState<WaiterPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<WaiterPerformanceRow | null>(null);
  const [receipts, setReceipts] = useState<PosWaiterSale[]>([]);
  const [receiptsLoading, setReceiptsLoading] = useState(false);
  const [receiptFilter, setReceiptFilter] = useState<ReceiptFilter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [markingId, setMarkingId] = useState<string | null>(null);
  const [heldSales, setHeldSales] = useState<HeldSale[]>(() => loadHeldSales());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await posApi.waiterPerformance({
        date_from: dateFrom,
        date_to: dateTo,
      });
      setData(res.data);
      setHeldSales(loadHeldSales());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onStorage = () => setHeldSales(loadHeldSales());
    window.addEventListener("storage", onStorage);
    const id = window.setInterval(() => setHeldSales(loadHeldSales()), 5000);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.clearInterval(id);
    };
  }, []);

  const loadReceipts = useCallback(
    async (waiter: WaiterPerformanceRow) => {
      setReceiptsLoading(true);
      try {
        const res = await posApi.waiterPerformance({
          date_from: dateFrom,
          date_to: dateTo,
          waiter_id: waiter.waiter_id || undefined,
          waiter_name: waiter.waiter_name,
        });
        setReceipts(res.data.receipts);
      } catch {
        setReceipts([]);
      } finally {
        setReceiptsLoading(false);
      }
    },
    [dateFrom, dateTo]
  );

  const handleSelect = (waiter: WaiterPerformanceRow) => {
    setSelected(waiter);
    setReceiptFilter("all");
    setExpanded(null);
    loadReceipts(waiter);
  };

  useEffect(() => {
    if (!selected || !data) return;
    const updated = data.waiters.find(
      (w) =>
        (selected.waiter_id && w.waiter_id === selected.waiter_id) ||
        w.waiter_name.toLowerCase() === selected.waiter_name.toLowerCase()
    );
    if (updated) {
      setSelected(updated);
    }
  }, [data, selected?.waiter_id, selected?.waiter_name]);

  const waiterHolds = useMemo(() => {
    if (!selected) return heldSales;
    const name = selected.waiter_name.toLowerCase();
    return heldSales.filter(
      (h) =>
        (h.waiterId && selected.waiter_id && h.waiterId === selected.waiter_id) ||
        (h.waiterName || "").toLowerCase() === name
    );
  }, [heldSales, selected]);

  const filteredReceipts = useMemo(() => {
    return receipts.filter((r) => {
      if (receiptFilter === "paid") return r.status === "paid";
      if (receiptFilter === "unpaid") return r.status !== "paid" && r.balance_due > 0;
      if (receiptFilter === "on_account")
        return r.payment_method === "on_account" || (r.status !== "paid" && r.payment_method === "invoice");
      return true;
    });
  }, [receipts, receiptFilter]);

  const handleMarkPaid = async (sale: PosWaiterSale) => {
    if (sale.status === "paid") return;
    if (
      !window.confirm(
        `Mark ${sale.invoice_number} as paid for ${formatCurrency(sale.total_amount)}?`
      )
    ) {
      return;
    }
    setMarkingId(sale.invoice_id);
    try {
      await salesApi.markInvoicePaid(sale.invoice_id);
      await load();
      if (selected) await loadReceipts(selected);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    } finally {
      setMarkingId(null);
    }
  };

  const summary = data?.summary;

  return (
    <PageLayout
      title="Waiter Performance"
      description="See what each waiter served — paid, unpaid, pay-later, and on-hold carts."
      breadcrumbs={["Home", "Waiter Performance"]}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-10 w-[150px] rounded-xl"
          />
          <span className="text-xs text-muted-foreground">to</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-10 w-[150px] rounded-xl"
          />
          <Button className="h-10 rounded-xl" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
          </Button>
        </div>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          {
            label: "Waiters",
            value: String(summary?.waiters_count ?? 0),
            sub: "Active in period",
            icon: UserCheck,
          },
          {
            label: "Receipts served",
            value: String(summary?.receipts_count ?? 0),
            sub: "All waiters",
            icon: ClipboardList,
          },
          {
            label: "Total served",
            value: formatCurrency(summary?.total_served ?? 0),
            sub: "Gross sales",
            icon: Wallet,
          },
          {
            label: "Paid",
            value: formatCurrency(summary?.paid_total ?? 0),
            sub: "Collected",
            icon: CircleCheck,
            tone: "success" as const,
          },
          {
            label: "Unpaid due",
            value: formatCurrency(summary?.unpaid_total ?? 0),
            sub: `${summary?.on_account_count ?? 0} pay later`,
            icon: PauseCircle,
            tone: "warn" as const,
          },
        ].map(({ label, value, sub, icon: Icon, tone }) => (
          <div
            key={label}
            className="rounded-2xl border border-border/80 bg-gradient-to-br from-card to-muted/30 px-5 py-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
                <p
                  className={cn(
                    "mt-1 text-xl font-semibold tracking-tight tabular-nums",
                    tone === "success" && "text-emerald-600",
                    tone === "warn" && "text-amber-600"
                  )}
                >
                  {value}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
              </div>
              <div
                className={cn(
                  "rounded-xl p-2.5",
                  tone === "success"
                    ? "bg-emerald-500/10 text-emerald-600"
                    : tone === "warn"
                      ? "bg-amber-500/10 text-amber-600"
                      : "bg-primary/10 text-primary"
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        {/* Waiter list */}
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
          <div className="border-b border-border px-5 py-3.5">
            <h2 className="text-sm font-semibold">Waiters</h2>
            <p className="text-xs text-muted-foreground">Select a waiter to see receipts & holds</p>
          </div>
          <div className="max-h-[min(70vh,760px)] overflow-y-auto scrollbar-thin">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                Loading…
              </div>
            ) : !data?.waiters.length ? (
              <p className="px-5 py-16 text-center text-sm text-muted-foreground">
                No waiter activity in this period. Add waiters in Settings → POS profile.
              </p>
            ) : (
              <ul className="divide-y divide-border/70">
                {data.waiters.map((w) => {
                  const active =
                    selected &&
                    ((w.waiter_id && selected.waiter_id === w.waiter_id) ||
                      w.waiter_name === selected.waiter_name);
                  const holdsFor = heldSales.filter(
                    (h) =>
                      (h.waiterId && w.waiter_id && h.waiterId === w.waiter_id) ||
                      (h.waiterName || "").toLowerCase() === w.waiter_name.toLowerCase()
                  ).length;
                  return (
                    <li key={w.waiter_id || w.waiter_name}>
                      <button
                        type="button"
                        onClick={() => handleSelect(w)}
                        className={cn(
                          "flex w-full flex-col gap-2 px-5 py-4 text-left transition-colors",
                          active
                            ? "bg-primary/[0.06] ring-1 ring-inset ring-primary/20"
                            : "hover:bg-muted/40"
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-bold text-primary">
                              {w.waiter_name.slice(0, 1).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="truncate font-semibold">{w.waiter_name}</p>
                              <p className="text-xs text-muted-foreground">
                                {w.receipts_count} receipt{w.receipts_count === 1 ? "" : "s"}
                                {holdsFor > 0 ? ` · ${holdsFor} on hold` : ""}
                              </p>
                            </div>
                          </div>
                          <p className="shrink-0 text-sm font-semibold tabular-nums">
                            {formatCurrency(w.total_served)}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-1.5 pl-[52px]">
                          <Badge variant="success" className="text-[10px]">
                            Paid {formatCurrency(w.paid_total)}
                          </Badge>
                          {w.unpaid_total > 0 && (
                            <Badge variant="warning" className="text-[10px]">
                              Due {formatCurrency(w.unpaid_total)}
                            </Badge>
                          )}
                          {w.on_account_count > 0 && (
                            <Badge variant="secondary" className="text-[10px]">
                              {w.on_account_count} pay later
                            </Badge>
                          )}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Detail */}
        <div className="space-y-4">
          {!selected ? (
            <div className="flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-muted/20 px-6 text-center">
              <UserCheck className="h-10 w-10 text-muted-foreground/40" />
              <p className="mt-3 text-sm font-medium">Select a waiter</p>
              <p className="mt-1 max-w-sm text-xs text-muted-foreground">
                View receipts they served, paid vs unpaid amounts, pay-later accounts, and on-hold carts from this POS.
              </p>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">{selected.waiter_name}</h2>
                    <p className="text-xs text-muted-foreground">
                      {dateFrom} → {dateTo}
                    </p>
                  </div>
                  <Badge variant="secondary">{selected.receipts_count} receipts</Badge>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-xl bg-muted/40 px-3 py-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Served</p>
                    <p className="text-base font-bold tabular-nums">{formatCurrency(selected.total_served)}</p>
                  </div>
                  <div className="rounded-xl bg-emerald-500/10 px-3 py-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-emerald-700">Paid</p>
                    <p className="text-base font-bold tabular-nums text-emerald-700">
                      {selected.paid_count} · {formatCurrency(selected.paid_total)}
                    </p>
                  </div>
                  <div className="rounded-xl bg-amber-500/10 px-3 py-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-amber-700">Unpaid</p>
                    <p className="text-base font-bold tabular-nums text-amber-700">
                      {selected.unpaid_count} · {formatCurrency(selected.unpaid_total)}
                    </p>
                  </div>
                  <div className="rounded-xl bg-muted/40 px-3 py-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Items sold</p>
                    <p className="text-base font-bold tabular-nums">{selected.items_sold}</p>
                  </div>
                </div>
              </div>

              {/* On hold */}
              <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <div className="flex items-center justify-between border-b border-border px-5 py-3">
                  <div>
                    <h3 className="text-sm font-semibold">On hold (this device)</h3>
                    <p className="text-xs text-muted-foreground">
                      Carts held in POS on this browser · resume from POS
                    </p>
                  </div>
                  <Badge variant="secondary">{waiterHolds.length}</Badge>
                </div>
                {waiterHolds.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">No held carts for this waiter.</p>
                ) : (
                  <ul className="divide-y divide-border/70">
                    {waiterHolds.map((h) => (
                      <li key={h.id} className="flex items-center justify-between gap-3 px-5 py-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{h.label || "Held sale"}</p>
                          <p className="text-xs text-muted-foreground">
                            {h.itemCount} item{h.itemCount === 1 ? "" : "s"} ·{" "}
                            {new Date(h.heldAt).toLocaleString()}
                          </p>
                        </div>
                        <p className="shrink-0 font-semibold tabular-nums">{formatCurrency(h.subtotal)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Receipts */}
              <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <div className="border-b border-border px-5 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold">Receipts served</h3>
                      <p className="text-xs text-muted-foreground">Paid, unpaid, and pay-later</p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(
                        [
                          { id: "all", label: "All" },
                          { id: "paid", label: "Paid" },
                          { id: "unpaid", label: "Unpaid" },
                          { id: "on_account", label: "Pay later" },
                        ] as const
                      ).map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setReceiptFilter(t.id)}
                          className={cn(
                            "rounded-full px-3 py-1 text-xs font-medium transition-all",
                            receiptFilter === t.id
                              ? "bg-foreground text-background"
                              : "bg-muted/60 text-muted-foreground hover:bg-muted"
                          )}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="max-h-[min(52vh,560px)] overflow-y-auto scrollbar-thin">
                  {receiptsLoading ? (
                    <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
                      <Loader2 className="h-5 w-5 animate-spin" />
                    </div>
                  ) : filteredReceipts.length === 0 ? (
                    <p className="px-5 py-10 text-center text-sm text-muted-foreground">
                      No receipts for this filter.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border/70">
                      {filteredReceipts.map((sale) => {
                        const open = expanded === sale.invoice_id;
                        return (
                          <li key={sale.invoice_id}>
                            <div className="flex items-start gap-3 px-5 py-3.5">
                              <button
                                type="button"
                                className="min-w-0 flex-1 text-left"
                                onClick={() =>
                                  setExpanded((id) => (id === sale.invoice_id ? null : sale.invoice_id))
                                }
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-mono text-sm font-semibold">{sale.invoice_number}</span>
                                  <Badge variant={statusVariant(sale.status)} className="capitalize">
                                    {sale.status}
                                  </Badge>
                                  <span className="text-[11px] text-muted-foreground">
                                    {sale.payment_method_label}
                                  </span>
                                </div>
                                <p className="mt-0.5 truncate text-sm">{sale.customer_name}</p>
                                <p className="mt-0.5 text-xs text-muted-foreground">{sale.issue_date}</p>
                              </button>
                              <div className="shrink-0 text-right">
                                <p className="text-sm font-semibold tabular-nums">
                                  {formatCurrency(sale.total_amount)}
                                </p>
                                {sale.balance_due > 0 && sale.status !== "paid" ? (
                                  <p className="text-xs font-medium text-amber-600">
                                    Due {formatCurrency(sale.balance_due)}
                                  </p>
                                ) : (
                                  <p className="text-xs text-emerald-600">Settled</p>
                                )}
                                {sale.status !== "paid" && sale.balance_due > 0 && (
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    className="mt-2 h-8 gap-1 text-emerald-700"
                                    disabled={markingId === sale.invoice_id}
                                    onClick={() => handleMarkPaid(sale)}
                                  >
                                    {markingId === sale.invoice_id ? (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                      <CircleCheck className="h-3.5 w-3.5" />
                                    )}
                                    Paid
                                  </Button>
                                )}
                              </div>
                            </div>
                            {open && (
                              <div className="border-t border-border/50 bg-muted/20 px-5 py-3">
                                <ul className="space-y-1.5">
                                  {sale.items.map((item, i) => (
                                    <li
                                      key={`${sale.invoice_id}-${i}`}
                                      className="flex justify-between gap-3 text-xs"
                                    >
                                      <span className="text-muted-foreground">
                                        {item.quantity}× {item.name}
                                      </span>
                                      <span className="tabular-nums">{formatCurrency(item.line_total)}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
