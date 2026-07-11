import { FileText, Play, Trash2, X, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/utils/cn";
import type { HeldSale } from "../hooks/usePosCart";
import { printHeldSaleSlip } from "../receipt/printCartSlip";

interface PosHeldSalesPanelProps {
  open: boolean;
  heldSales: HeldSale[];
  customers: { id: string; name: string }[];
  taxRate: number;
  branchName?: string;
  branchId?: string;
  onClose: () => void;
  onResume: (id: string) => void;
  onDelete: (id: string) => void;
}

function formatHeldTime(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function customerLabel(sale: HeldSale, customers: { id: string; name: string }[]) {
  if (!sale.customerId || sale.customerId === "walkin") return "Walk-in Customer";
  return customers.find((c) => c.id === sale.customerId)?.name ?? "Customer";
}

export function PosHeldSalesPanel({
  open,
  heldSales,
  customers,
  taxRate,
  branchName,
  branchId,
  onClose,
  onResume,
  onDelete,
}: PosHeldSalesPanelProps) {
  if (!open) return null;

  const printHeld = async (sale: HeldSale) => {
    const disc = sale.discountAmount;
    const afterDisc = sale.subtotal - disc;
    const tax = afterDisc * taxRate;
    const total = afterDisc + tax;
    await printHeldSaleSlip({
      label: sale.label,
      customerName: customerLabel(sale, customers),
      waiterName: sale.waiterName,
      branchName,
      branchId,
      cart: sale.cart,
      subtotal: sale.subtotal,
      discount: disc,
      tax,
      taxRate,
      grandTotal: total,
      notes: sale.notes,
      heldAt: formatHeldTime(sale.heldAt),
    });
  };

  return (
    <div className="absolute inset-0 z-40 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">On hold</h3>
            {heldSales.length > 0 && (
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {heldSales.length}
              </span>
            )}
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="max-h-80 overflow-y-auto p-3 scrollbar-thin">
          {heldSales.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No held sales. Use &quot;On Hold&quot; in the cart to park an order and print a slip.
            </p>
          ) : (
            <ul className="space-y-2">
              {heldSales.map((sale) => (
                <li
                  key={sale.id}
                  className="flex items-center gap-2 rounded-xl border border-border bg-muted/20 p-3"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{sale.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {sale.itemCount} items · {formatCurrency(sale.subtotal)} · {formatHeldTime(sale.heldAt)}
                    </p>
                    {sale.waiterName && (
                      <p className="text-[10px] text-amber-600 mt-0.5">Waiter: {sale.waiterName}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 shrink-0"
                    onClick={() => printHeld(sale)}
                    title="Print hold slip"
                  >
                    <Printer className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    className="h-8 gap-1 shrink-0"
                    onClick={() => {
                      onResume(sale.id);
                      onClose();
                    }}
                  >
                    <Play className="h-3.5 w-3.5" />
                    Resume
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 shrink-0 text-destructive"
                    onClick={() => onDelete(sale.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
