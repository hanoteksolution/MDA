import { useEffect, useMemo, useState } from "react";
import { X, Loader2, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency } from "@/utils/cn";
import { posApi, type PosWaiterSale } from "@/services/api/pos";

interface PosWaiterSalesPanelProps {
  open: boolean;
  waiterId: string;
  waiterName: string;
  branchId?: string;
  onClose: () => void;
}

type SaleFilter = "unpaid" | "all";

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function PosWaiterSalesPanel({
  open,
  waiterId,
  waiterName,
  branchId,
  onClose,
}: PosWaiterSalesPanelProps) {
  const [sales, setSales] = useState<PosWaiterSale[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<SaleFilter>("unpaid");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !waiterId) return;
    setLoading(true);
    setFilter("unpaid");
    posApi
      .waiterSales({ waiter_id: waiterId, branch_id: branchId, days: 30 })
      .then((res) => {
        const rows = res.data;
        setSales(rows);
        const firstUnpaid = rows.find((s) => s.balance_due > 0);
        setExpanded(firstUnpaid?.invoice_id ?? rows[0]?.invoice_id ?? null);
      })
      .catch(() => setSales([]))
      .finally(() => setLoading(false));
  }, [open, waiterId, branchId]);

  const unpaid = useMemo(() => sales.filter((s) => s.balance_due > 0), [sales]);
  const visible = filter === "unpaid" ? unpaid : sales;
  const totalServed = sales.reduce((sum, s) => sum + s.total_amount, 0);

  /** Aggregate products taken on unpaid receipts (served without payment). */
  const unpaidProducts = useMemo(() => {
    const map = new Map<string, { name: string; sku: string; quantity: number; line_total: number }>();
    for (const sale of unpaid) {
      for (const item of sale.items) {
        const key = `${item.sku || ""}::${item.name}`;
        const prev = map.get(key);
        if (prev) {
          prev.quantity += item.quantity;
          prev.line_total += item.line_total;
        } else {
          map.set(key, {
            name: item.name,
            sku: item.sku || "",
            quantity: item.quantity,
            line_total: item.line_total,
          });
        }
      }
    }
    return [...map.values()].sort((a, b) => b.quantity - a.quantity);
  }, [unpaid]);

  if (!open) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3 shrink-0">
          <div>
            <h3 className="text-sm font-semibold">Waiter sales & unpaid products</h3>
            <p className="text-xs text-muted-foreground">{waiterName} · last 30 days</p>
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-2 border-b border-border p-3 shrink-0">
          <div className="rounded-xl bg-muted/40 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Total served</p>
            <p className="text-lg font-bold tabular-nums">{formatCurrency(totalServed)}</p>
          </div>
          <div className="rounded-xl bg-amber-500/10 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-amber-700 dark:text-amber-400">Unpaid</p>
            <p className="text-lg font-bold tabular-nums text-amber-700 dark:text-amber-400">
              {unpaid.length} · {formatCurrency(unpaid.reduce((s, x) => s + x.balance_due, 0))}
            </p>
          </div>
        </div>

        {!loading && unpaidProducts.length > 0 && (
          <div className="border-b border-border bg-amber-500/[0.06] px-4 py-3 shrink-0">
            <div className="mb-2 flex items-center gap-2">
              <Package className="h-4 w-4 text-amber-700 dark:text-amber-400" />
              <p className="text-xs font-semibold text-amber-800 dark:text-amber-300">
                Products taken without payment
              </p>
            </div>
            <ul className="max-h-36 space-y-1.5 overflow-y-auto scrollbar-thin">
              {unpaidProducts.map((p) => (
                <li
                  key={`${p.sku}-${p.name}`}
                  className="flex items-center justify-between gap-3 rounded-lg bg-card/80 px-2.5 py-1.5 text-xs ring-1 ring-border/50"
                >
                  <span className="min-w-0 truncate font-medium">
                    <span className="tabular-nums text-amber-700 dark:text-amber-400">{p.quantity}×</span>{" "}
                    {p.name}
                    {p.sku ? (
                      <span className="ml-1 font-mono text-[10px] text-muted-foreground">{p.sku}</span>
                    ) : null}
                  </span>
                  <span className="shrink-0 tabular-nums font-semibold">{formatCurrency(p.line_total)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex gap-1 border-b border-border px-3 py-2 shrink-0">
          {(
            [
              { id: "unpaid", label: `Unpaid (${unpaid.length})` },
              { id: "all", label: `All (${sales.length})` },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilter(tab.id)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                filter === tab.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted/60"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3 scrollbar-thin">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : visible.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              {filter === "unpaid"
                ? "No unpaid receipts for this waiter."
                : "No sales recorded for this waiter yet."}
            </p>
          ) : (
            <ul className="space-y-2">
              {visible.map((sale) => {
                const isUnpaid = sale.balance_due > 0;
                const isOpen = expanded === sale.invoice_id || (isUnpaid && filter === "unpaid");
                return (
                  <li key={sale.invoice_id} className="rounded-xl border border-border bg-muted/20">
                    <button
                      type="button"
                      className="flex w-full items-start gap-3 p-3 text-left"
                      onClick={() =>
                        setExpanded((id) => (id === sale.invoice_id ? null : sale.invoice_id))
                      }
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-xs font-semibold">{sale.invoice_number}</span>
                          <Badge
                            variant={isUnpaid ? "secondary" : "default"}
                            className="text-[10px]"
                          >
                            {isUnpaid ? "Unpaid" : sale.status}
                          </Badge>
                        </div>
                        <p className="mt-0.5 truncate text-sm">{sale.customer_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(sale.issue_date)} · {sale.payment_method_label} ·{" "}
                          {sale.items.length} item{sale.items.length === 1 ? "" : "s"}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="font-semibold tabular-nums">{formatCurrency(sale.total_amount)}</p>
                        {isUnpaid && (
                          <p className="text-xs text-amber-600 tabular-nums">
                            Due {formatCurrency(sale.balance_due)}
                          </p>
                        )}
                      </div>
                    </button>
                    {isOpen && (
                      <div className="border-t border-border px-3 py-2.5 text-xs">
                        <p className="mb-1.5 font-medium text-muted-foreground">
                          {isUnpaid ? "Products taken (unpaid)" : "Products served"}
                        </p>
                        <ul className="space-y-1">
                          {sale.items.map((item, i) => (
                            <li key={i} className="flex justify-between gap-2">
                              <span className="truncate">
                                <span className="font-semibold tabular-nums">{item.quantity}×</span>{" "}
                                {item.name}
                              </span>
                              <span className="tabular-nums shrink-0">{formatCurrency(item.line_total)}</span>
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

        <div className="border-t border-border p-3 shrink-0">
          <Button variant="secondary" className="w-full" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
