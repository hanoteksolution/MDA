import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProductAvailability } from "@/types/models/catalog";
import { TRANSFER_TONE, num, qtyText, statusLabel } from "../lib";

/**
 * Stock of one product in the acting branch and, where the caller may see them, every other
 * branch. Visibility only: selling another branch's stock is impossible — the way to get it is a
 * branch transfer request, which the source branch must approve.
 */
export function CrossBranchPanel({
  data,
  requested = 0,
  onRequestTransfer,
}: {
  data: ProductAvailability;
  /** Quantity the user wants here (e.g. a POS cart line) — drives the shortage line. */
  requested?: number;
  onRequestTransfer?: (sourceBranchId: string, sourceBranchName: string, suggested: number) => void;
}) {
  const local = num(data.current_branch.available);
  const shortage = Math.max(0, requested - local);
  return (
    <div className="space-y-3 text-sm">
      <div className="rounded-xl border bg-muted/30 px-3 py-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-medium">{data.current_branch.branch_name} (this branch)</span>
          <Badge variant={local > 0 ? "success" : "destructive"}>{qtyText(local)} available</Badge>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          On hand {qtyText(data.current_branch.on_hand)} · reserved {qtyText(data.current_branch.reserved)} · incoming{" "}
          {qtyText(data.current_branch.in_transit)}
        </div>
        {shortage > 0 && (
          <div className="mt-1 text-xs font-medium text-destructive">Local shortage: {qtyText(shortage)} short of {qtyText(requested)}.</div>
        )}
      </div>

      {data.other_branches.length === 0 ? (
        <p className="text-xs text-muted-foreground">Your role in this branch cannot see other branches' stock.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Branch</th>
                <th className="px-3 py-2 text-right">On hand</th>
                <th className="px-3 py-2 text-right">Reserved</th>
                <th className="px-3 py-2 text-right">Available</th>
                <th className="px-3 py-2 text-right">In transit</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.other_branches.map((b) => (
                <tr key={b.branch_id} className="border-t align-top">
                  <td className="px-3 py-2">
                    <div className="font-medium">{b.branch_name}</div>
                    {b.warehouses?.map((w) => (
                      <div key={w.warehouse_id} className="text-xs text-muted-foreground">
                        {w.warehouse_name}: {qtyText(w.available)} available
                      </div>
                    ))}
                  </td>
                  <td className="px-3 py-2 text-right">{b.on_hand === undefined ? "—" : qtyText(b.on_hand)}</td>
                  <td className="px-3 py-2 text-right">{b.reserved === undefined ? "—" : qtyText(b.reserved)}</td>
                  <td className="px-3 py-2 text-right">
                    <Badge variant={num(b.available) > 0 ? "success" : "secondary"}>{qtyText(b.available)}</Badge>
                  </td>
                  <td className="px-3 py-2 text-right">{b.in_transit === undefined ? "—" : qtyText(b.in_transit)}</td>
                  <td className="px-3 py-2 text-right">
                    {onRequestTransfer && num(b.available) > 0 && (
                      <Button size="sm" variant="secondary"
                        onClick={() => onRequestTransfer(b.branch_id, b.branch_name, Math.min(num(b.available), shortage || 1))}>
                        Request transfer
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!!data.open_transfers?.length && (
        <div className="space-y-1">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Open transfers for this product</div>
          {data.open_transfers.map((t) => (
            <div key={t.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-xs">
              <span>
                {t.request_number} · {t.source_branch_name} → {t.destination_branch_name} · {qtyText(t.quantity_requested)}
              </span>
              <Badge variant={TRANSFER_TONE[t.status] ?? "outline"}>{statusLabel(t.status)}</Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
