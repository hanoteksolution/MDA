import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/utils/cn";
import { posApi, type PosWaiterSale } from "@/services/api/pos";

interface PosWaiterSalesPanelProps {
  open: boolean;
  waiterId: string;
  waiterName: string;
  branchId?: string;
  onClose: () => void;
}

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
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !waiterId) return;
    setLoading(true);
    posApi
      .waiterSales({ waiter_id: waiterId, branch_id: branchId, days: 30 })
      .then((res) => setSales(res.data))
      .catch(() => setSales([]))
      .finally(() => setLoading(false));
  }, [open, waiterId, branchId]);

  if (!open) return null;

  const unpaid = sales.filter((s) => s.balance_due > 0);
  const totalServed = sales.reduce((sum, s) => sum + s.total_amount, 0);

  return (
    <div className="absolute inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3 shrink-0">
          <div>
            <h3 className="text-sm font-semibold">Waiter sales</h3>
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

        <div className="min-h-0 flex-1 overflow-y-auto p-3 scrollbar-thin">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : sales.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No sales recorded for this waiter yet.
            </p>
          ) : (
            <ul className="space-y-2">
              {sales.map((sale) => (
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
                          variant={sale.balance_due > 0 ? "secondary" : "default"}
                          className="text-[10px]"
                        >
                          {sale.balance_due > 0 ? "Unpaid" : sale.status}
                        </Badge>
                      </div>
                      <p className="mt-0.5 truncate text-sm">{sale.customer_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(sale.issue_date)} · {sale.payment_method_label}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-semibold tabular-nums">{formatCurrency(sale.total_amount)}</p>
                      {sale.balance_due > 0 && (
                        <p className="text-xs text-amber-600 tabular-nums">
                          Due {formatCurrency(sale.balance_due)}
                        </p>
                      )}
                    </div>
                  </button>
                  {expanded === sale.invoice_id && (
                    <div className="border-t border-border px-3 py-2 text-xs">
                      <p className="mb-1 font-medium text-muted-foreground">Products served</p>
                      <ul className="space-y-1">
                        {sale.items.map((item, i) => (
                          <li key={i} className="flex justify-between gap-2">
                            <span className="truncate">
                              {item.quantity}× {item.name}
                            </span>
                            <span className="tabular-nums shrink-0">{formatCurrency(item.line_total)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </li>
              ))}
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
