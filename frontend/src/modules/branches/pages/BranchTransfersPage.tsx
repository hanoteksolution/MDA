import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowRight, Plus, Send } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import type { FilterConfig } from "@/components/data/FilterBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { appDialog } from "@/components/feedback/AppDialog";
import { ALL_BRANCHES } from "@/services/api/branchContext";
import { branchOpsApi, type BranchTransfer, type Paged, type TransferAction } from "@/services/api/branchOps";
import { useBranchStore } from "@/store/branchStore";
import { activeBranchLabel } from "@/components/branch/BranchSwitcher";
import { TRANSFER_STATUSES, TRANSFER_STEPS, TRANSFER_TONE, availableTransferActions, qtyText, statusLabel, when } from "../lib";
import { TransferRequestForm } from "../components/TransferRequestForm";
import { SendStockDialog } from "../components/SendStockDialog";

/** Branch transfers: every request touching a branch the user can act in, with its workflow. */
export function BranchTransfersPage({ embedded = false, branchId }: { embedded?: boolean; branchId?: string }) {
  const [params, setParams] = useSearchParams();
  const { branches, activeBranchId, canInBranch } = useBranchStore();
  const [data, setData] = useState<Paged<BranchTransfer>>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const status = params.get("status") ?? "";
  const direction = params.get("direction") ?? "";
  const page = Number(params.get("page") || 1);
  const scopeBranch = branchId ?? (activeBranchId && activeBranchId !== ALL_BRANCHES ? activeBranchId : "");

  const set = (key: string, value: string) =>
    setParams((cur) => {
      const next = new URLSearchParams(cur);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.delete("page");
      return next;
    });

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    branchOpsApi
      .transfers({ status, branch_id: scopeBranch, page, page_size: 25 })
      .then((r) => active && setData(r.data))
      .catch((e: unknown) => active && setError(e instanceof Error ? e.message : "Could not load transfers."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [status, scopeBranch, page, reload]);

  const rows = (data?.results ?? []).filter((t) =>
    !direction || !scopeBranch ? true : direction === "incoming" ? t.destination_branch_id === scopeBranch : t.source_branch_id === scopeBranch
  );
  const filters: FilterConfig[] = [
    { key: "status", label: "Status", value: status, onChange: (v) => set("status", v),
      options: [{ value: "", label: "All statuses" }, ...TRANSFER_STATUSES.map((s) => ({ value: s, label: statusLabel(s) }))] },
    ...(scopeBranch ? [{ key: "direction", label: "Direction", value: direction, onChange: (v: string) => set("direction", v),
      options: [{ value: "", label: "Incoming & outgoing" }, { value: "incoming", label: "Incoming (to this branch)" }, { value: "outgoing", label: "Outgoing (from this branch)" }] }] : []),
  ];
  const columns: Column<BranchTransfer>[] = [
    { key: "number", header: "Request", exportValue: (t) => t.request_number,
      cell: (t) => <button type="button" className="font-medium text-primary hover:underline" onClick={() => setSelected(t.id)}>{t.request_number}</button> },
    { key: "route", header: "From → To", exportValue: (t) => `${t.source_branch_name} → ${t.destination_branch_name}`,
      cell: (t) => <span className="inline-flex items-center gap-1.5">{t.source_branch_name}<ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />{t.destination_branch_name}</span> },
    { key: "items", header: "Items", exportValue: (t) => String(t.line_count ?? ""), cell: (t) => `${t.line_count ?? "—"} line(s) · ${qtyText(t.total_quantity)} units` },
    { key: "status", header: "Status", exportValue: (t) => t.status, cell: (t) => <Badge variant={TRANSFER_TONE[t.status] ?? "outline"}>{statusLabel(t.status)}</Badge> },
    { key: "requested_by", header: "Requested by", exportValue: (t) => t.requested_by ?? "", cell: (t) => t.requested_by ?? "—" },
    { key: "created_at", header: "Requested", exportValue: (t) => t.created_at, cell: (t) => when(t.created_at) },
    { key: "actions", header: "", className: "text-right", cell: (t) => <Button size="sm" variant="ghost" onClick={() => setSelected(t.id)}>Open</Button> },
  ];
  const canRequest = branches.some((b) => b.permissions.includes("inventory.transfer")) || canInBranch("inventory.transfer");
  const body = (
    <>
      {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">{error}</p>}
      <DataTable
        columns={columns} data={rows} loading={loading} filters={filters}
        page={data?.page ?? page} pageSize={25} total={data?.count ?? 0} onPageChange={(p) => set("page", String(p))}
        exportTitle="Branch transfers"
        actions={canRequest ? (
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setSending(true)}><Send className="mr-1.5 h-4 w-4" />Send stock</Button>
            <Button size="sm" onClick={() => setCreating(true)}><Plus className="mr-1.5 h-4 w-4" />Request stock</Button>
          </div>
        ) : undefined}
        emptyMessage={error ? "Transfers could not be loaded." : "No transfers for this branch scope."}
      />
      <TransferDetailDialog id={selected} onClose={() => setSelected(null)} onChanged={() => setReload((v) => v + 1)} />
      <TransferRequestForm open={creating} onClose={() => setCreating(false)} onCreated={() => setReload((v) => v + 1)} />
      <SendStockDialog open={sending} onClose={() => setSending(false)} onCreated={() => setReload((v) => v + 1)} />
    </>
  );
  if (embedded) return <div className="space-y-4">{body}</div>;
  return (
    <PageLayout
      title="Branch transfers"
      description={`Stock requests between branches. Showing: ${scopeBranch ? activeBranchLabel(scopeBranch, branches) : "all your branches"}.`}
      breadcrumbs={["Branches", "Transfers"]}
    >
      <div className="space-y-4">{body}</div>
    </PageLayout>
  );
}

function TransferDetailDialog({ id, onClose, onChanged }: { id: string | null; onClose: () => void; onChanged: () => void }) {
  const canInBranch = useBranchStore((s) => s.canInBranch);
  const [t, setT] = useState<BranchTransfer | null>(null);
  const [busy, setBusy] = useState<TransferAction | null>(null);
  // Reject needs a reason; cancel takes an optional one. Both are typed inline, then confirmed.
  const [pending, setPending] = useState<"reject" | "cancel" | null>(null);
  const [reason, setReason] = useState("");
  const load = useCallback(() => {
    if (!id) return;
    setT(null);
    branchOpsApi.transfer(id).then((r) => setT(r.data)).catch(async (e: unknown) => {
      onClose();
      await appDialog.alert(e instanceof Error ? e.message : "Transfer not found.", { tone: "danger" });
    });
  }, [id, onClose]);
  useEffect(load, [load]);

  const run = async (action: TransferAction, label: string, danger?: boolean) => {
    if (!t) return;
    let body: Record<string, unknown> = {};
    if (action === "reject" || action === "cancel") {
      if (pending !== action) {
        setPending(action);
        setReason("");
        return;
      }
      if (action === "reject" && !reason.trim()) return;
      if (action === "cancel" && !(await appDialog.confirm(
        `Cancel ${t.request_number}? Any reserved stock returns to ${t.source_branch_name}. This cannot be undone.`,
        { title: "Cancel transfer", confirmLabel: "Cancel transfer", tone: "danger" }))) return;
      body = { reason: reason.trim() };
    } else if (!(await appDialog.confirm(`${label} ${t.request_number}?`, { title: label, confirmLabel: label, tone: danger ? "danger" : "default" }))) {
      return;
    }
    if (action === "receive") body = { idempotency_key: `receive-${t.id}` };
    setBusy(action);
    try {
      const r = await branchOpsApi.transferAction(t.id, action, body);
      setT(r.data);
      setPending(null);
      setReason("");
      onChanged();
    } catch (e) {
      await appDialog.alert(e instanceof Error ? e.message : "Action failed.", { title: `${label} failed`, tone: "danger" });
    } finally {
      setBusy(null);
    }
  };

  const actions = t ? availableTransferActions(t, (p, b) => canInBranch(p, b)) : [];
  const reached = (s: string) => t && TRANSFER_STEPS.findIndex((x) => x.status === s) <= TRANSFER_STEPS.findIndex((x) => x.status === (t.status === "DISPATCHED" ? "IN_TRANSIT" : t.status));
  return (
    <PlatformConfirmDialog
      open={Boolean(id)} wide tone="default"
      title={t ? `${t.request_number} · ${t.source_branch_name} → ${t.destination_branch_name}` : "Transfer"}
      description={t ? `${t.source_warehouse_name ?? "Source"} → ${t.destination_warehouse_name ?? "Destination"}${t.notes ? ` · ${t.notes}` : ""}` : "Loading…"}
      confirmLabel="Close" onConfirm={onClose} onCancel={onClose}
    >
      {t && (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={TRANSFER_TONE[t.status] ?? "outline"}>{statusLabel(t.status)}</Badge>
            {t.rejection_reason && <span className="text-destructive">Rejected: {t.rejection_reason}</span>}
          </div>
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr><th className="px-3 py-2 text-left">Product</th><th className="px-3 py-2 text-right">Requested</th><th className="px-3 py-2 text-right">Reserved</th>
                  <th className="px-3 py-2 text-right">Dispatched</th><th className="px-3 py-2 text-right">Received</th></tr>
              </thead>
              <tbody>
                {(t.lines ?? []).map((l) => (
                  <tr key={l.id} className="border-t">
                    <td className="px-3 py-2"><div className="font-medium">{l.product_name ?? l.product_sku}</div><div className="text-xs text-muted-foreground">{l.product_sku}</div></td>
                    <td className="px-3 py-2 text-right">{qtyText(l.quantity_requested)}</td>
                    <td className="px-3 py-2 text-right">{qtyText(l.quantity_reserved)}</td>
                    <td className="px-3 py-2 text-right">{qtyText(l.quantity_dispatched)}</td>
                    <td className="px-3 py-2 text-right">{qtyText(l.quantity_received)}{l.discrepancy_quantity ? <span className="ml-1 text-destructive">(Δ {qtyText(l.discrepancy_quantity)})</span> : null}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ol className="space-y-2 border-l pl-4">
            {TRANSFER_STEPS.map((step) => {
              const at = t[step.at] as string | null;
              const by = step.by ? (t[step.by] as string | null) : null;
              return (
                <li key={step.status} className={reached(step.status) && at ? "" : "text-muted-foreground"}>
                  <span className="font-medium">{step.label}</span>
                  <span className="ml-2 text-xs">{at ? when(at) : "pending"}{by ? ` · ${by}` : ""}</span>
                </li>
              );
            })}
          </ol>
          {t.status === "CANCELLED" && t.cancelled_by && (
            <p className="rounded-xl border bg-muted/40 px-3 py-2">
              Cancelled by <span className="font-medium">{t.cancelled_by}</span> on {when(t.cancelled_at)}{t.cancel_reason ? ` — ${t.cancel_reason}` : ""}
            </p>
          )}
          {pending && (
            <label className="block space-y-1">
              <span className="font-medium">
                {pending === "reject" ? "Reason for rejecting (sent to the requesting branch)" : "Reason for cancelling (optional, recorded in the audit log)"}
              </span>
              <Input value={reason} maxLength={250} autoFocus onChange={(e) => setReason(e.target.value)} />
            </label>
          )}
          {!!t.history?.length && (
            <details className="rounded-xl border px-3 py-2">
              <summary className="cursor-pointer font-medium">History ({t.history.length})</summary>
              <ul className="mt-2 space-y-1 text-xs">
                {t.history.map((h, i) => (
                  <li key={i}>{when(h.at)} · {h.by ?? "system"} · {h.status ? statusLabel(h.status) : h.action}{h.reason ? ` — ${h.reason}` : ""}</li>
                ))}
              </ul>
            </details>
          )}
          {actions.length > 0 && (
            <div className="flex flex-wrap gap-2 border-t pt-3">
              {actions.map((a) => (
                <Button key={a.action} size="sm" variant={a.tone === "danger" ? "secondary" : "default"} loading={busy === a.action}
                  disabled={busy !== null || (a.action === "reject" && pending === "reject" && !reason.trim())} onClick={() => void run(a.action, a.label, a.tone === "danger")}>
                  {pending === a.action ? (a.action === "reject" ? "Confirm rejection" : "Confirm cancellation") : a.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      )}
    </PlatformConfirmDialog>
  );
}

