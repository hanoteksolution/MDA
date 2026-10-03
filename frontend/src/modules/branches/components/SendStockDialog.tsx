import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { PlatformConfirmDialog } from "@/components/platform/PlatformConfirmDialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { appDialog } from "@/components/feedback/AppDialog";
import { branchOpsApi, type TransferDestination } from "@/services/api/branchOps";
import { ALL_BRANCHES } from "@/services/api/branchContext";
import { useBranchStore } from "@/store/branchStore";
import { activeBranchLabel } from "@/components/branch/BranchSwitcher";
import { num, qtyText } from "../lib";

export interface SendLine {
  productId: string;
  productName: string;
  sku?: string;
  available: number;
  quantity: string;
}

type Step = "compose" | "review";

/** Who may push stock: a single acting branch where the user holds inventory.transfer. */
export function sendStockGate(activeBranchId: string | null, canInBranch: (p: string, b?: string | null) => boolean) {
  const source = activeBranchId && activeBranchId !== ALL_BRANCHES ? activeBranchId : "";
  if (!source) return { source, canSend: false, reason: "Select the sending branch in the header first." };
  if (!canInBranch("inventory.transfer", source)) return { source, canSend: false, reason: "Your role cannot send stock from this branch." };
  return { source, canSend: true, reason: "" };
}

/**
 * "Send stock to branch" (push). Creates an ordinary branch transfer from the active branch,
 * approved by the sender in the same step. Nothing reaches the destination until the sender
 * reserves and dispatches it and the destination receives it — the same lifecycle as a request.
 */
export function SendStockDialog({ open, initial, onClose, onCreated }: {
  open: boolean;
  initial?: SendLine | null;
  onClose: () => void;
  onCreated?: (requestNumber: string) => void;
}) {
  const { activeBranchId, branches, canInBranch } = useBranchStore();
  const { source, canSend, reason: gateReason } = sendStockGate(activeBranchId, canInBranch);
  const [destinations, setDestinations] = useState<TransferDestination[]>([]);
  const [destination, setDestination] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [lines, setLines] = useState<SendLine[]>([]);
  const [notes, setNotes] = useState("");
  const [term, setTerm] = useState("");
  const [matches, setMatches] = useState<SendLine[]>([]);
  const [step, setStep] = useState<Step>("compose");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setStep("compose");
    setDestination("");
    setWarehouse("");
    setNotes("");
    setTerm("");
    setMatches([]);
    setError("");
    setLines(initial ? [initial] : []);
    if (canSend) branchOpsApi.transferDestinations().then((r) => setDestinations(r.data.filter((d) => d.id !== source))).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load branches."));
  }, [open, initial, canSend, source]);

  useEffect(() => {
    if (!open || !canSend || term.trim().length < 2) {
      setMatches([]);
      return;
    }
    const t = setTimeout(() => {
      branchOpsApi.crossBranchSearch(term.trim())
        .then((r) => setMatches(r.data.results.map((p) => ({ productId: p.product_id, productName: p.product_name, sku: p.product_sku,
          available: num(p.current_branch.available), quantity: "1" }))))
        .catch(() => setMatches([]));
    }, 300);
    return () => clearTimeout(t);
  }, [term, open, canSend]);

  const dest = destinations.find((d) => d.id === destination);
  const valid = Boolean(destination) && lines.length > 0 && lines.every((l) => num(l.quantity) > 0 && num(l.quantity) <= l.available);
  const addLine = (m: SendLine) => {
    setLines((cur) => (cur.some((l) => l.productId === m.productId) ? cur : [...cur, m]));
    setTerm("");
    setMatches([]);
  };

  const submit = async () => {
    if (!valid) return;
    setBusy(true);
    try {
      const r = await branchOpsApi.requestTransfer({
        source_branch_id: source,
        destination_branch_id: destination,
        destination_warehouse_id: warehouse || undefined,
        lines: lines.map((l) => ({ product_id: l.productId, quantity: String(num(l.quantity)) })),
        notes,
        approve: true,
      });
      onClose();
      onCreated?.(r.data.request_number);
      await appDialog.alert(`${r.data.request_number} created and approved. Reserve and dispatch it from Branch transfers; ${dest?.name ?? "the branch"} receives it on arrival.`,
        { title: "Transfer created", tone: "success" });
    } catch (e) {
      await appDialog.alert(e instanceof Error ? e.message : "Could not create the transfer.", { title: "Send failed", tone: "danger" });
    } finally {
      setBusy(false);
    }
  };

  const title = `Send stock from ${activeBranchLabel(source || null, branches)}`;
  if (!canSend) {
    return (
      <PlatformConfirmDialog open={open} tone="default" title="Send stock to branch" confirmLabel="Close" onConfirm={onClose} onCancel={onClose}
        description={gateReason} />
    );
  }
  return (
    <PlatformConfirmDialog
      open={open} wide tone="default" title={title}
      description={step === "compose" ? "Choose the receiving branch and what to send." : "Review before creating the transfer. No stock moves yet."}
      confirmLabel={step === "compose" ? "Review" : "Create transfer"}
      confirmDisabled={!valid}
      loading={busy}
      onConfirm={() => (step === "compose" ? setStep("review") : void submit())}
      onCancel={() => (step === "review" ? setStep("compose") : onClose())}
    >
      {error && <p className="text-sm text-destructive">{error}</p>}
      {step === "compose" ? (
        <div className="space-y-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1">
              <span className="font-medium">Destination branch</span>
              <select aria-label="Destination branch" className="block h-10 w-full rounded-xl border border-input bg-background px-3" value={destination}
                onChange={(e) => { setDestination(e.target.value); setWarehouse(""); }}>
                <option value="">Select a branch…</option>
                {destinations.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.code})</option>)}
              </select>
            </label>
            <label className="space-y-1">
              <span className="font-medium">Destination warehouse</span>
              {dest?.warehouses ? (
                <select aria-label="Destination warehouse" className="block h-10 w-full rounded-xl border border-input bg-background px-3" value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
                  <option value="">Branch default</option>
                  {dest.warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}{w.is_default ? " (default)" : ""}</option>)}
                </select>
              ) : (
                <div className="flex h-10 items-center rounded-xl border border-dashed px-3 text-muted-foreground">{dest ? "Branch default warehouse" : "—"}</div>
              )}
            </label>
          </div>
          <div className="space-y-2">
            <Input placeholder="Add a product: name, SKU or barcode…" value={term} onChange={(e) => setTerm(e.target.value)} aria-label="Add product" />
            {matches.length > 0 && (
              <ul className="max-h-48 overflow-y-auto rounded-xl border">
                {matches.map((m) => (
                  <li key={m.productId}>
                    <button type="button" disabled={m.available <= 0} onClick={() => addLine(m)}
                      className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-muted disabled:opacity-50">
                      <span>{m.productName} <span className="text-xs text-muted-foreground">{m.sku}</span></span>
                      <Badge variant={m.available > 0 ? "success" : "secondary"}>{qtyText(m.available)} available here</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {lines.length === 0 ? (
            <p className="text-muted-foreground">No products added yet.</p>
          ) : (
            <ul className="space-y-2">
              {lines.map((l, i) => {
                const over = num(l.quantity) > l.available;
                return (
                  <li key={l.productId} className="flex flex-wrap items-center gap-3 rounded-xl border px-3 py-2">
                    <span className="min-w-[10rem] flex-1 font-medium">{l.productName}</span>
                    <span className="text-xs text-muted-foreground">{qtyText(l.available)} available</span>
                    <Input className="w-24" type="number" min="0" step="any" aria-label={`Quantity of ${l.productName}`} value={l.quantity}
                      onChange={(e) => setLines((cur) => cur.map((x, j) => (j === i ? { ...x, quantity: e.target.value } : x)))} />
                    {over && <span className="text-xs text-destructive">More than available</span>}
                    <Button size="sm" variant="ghost" aria-label={`Remove ${l.productName}`} onClick={() => setLines((cur) => cur.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
                  </li>
                );
              })}
            </ul>
          )}
          <label className="block space-y-1">
            <span className="font-medium">Note for the receiving branch</span>
            <Input value={notes} maxLength={250} onChange={(e) => setNotes(e.target.value)} />
          </label>
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <dl className="grid gap-2 sm:grid-cols-2">
            <div><dt className="text-xs uppercase text-muted-foreground">From</dt><dd className="font-medium">{activeBranchLabel(source, branches)}</dd></div>
            <div><dt className="text-xs uppercase text-muted-foreground">To</dt><dd className="font-medium">{dest?.name}{warehouse ? ` · ${dest?.warehouses?.find((w) => w.id === warehouse)?.name}` : " · default warehouse"}</dd></div>
          </dl>
          <ul className="divide-y rounded-xl border">
            {lines.map((l) => <li key={l.productId} className="flex justify-between px-3 py-2"><span>{l.productName}</span><span className="tabular-nums">{qtyText(l.quantity)}</span></li>)}
          </ul>
          <p className="text-xs text-muted-foreground">Creates an approved transfer. Stock is reserved and leaves this branch only when you reserve and dispatch it; {dest?.name} adds it only when it receives it.</p>
        </div>
      )}
    </PlatformConfirmDialog>
  );
}
