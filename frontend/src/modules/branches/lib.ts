import type { BadgeProps } from "@/components/ui/badge";
import type { BranchTransfer, TransferAction, TransferStatus } from "@/services/api/branchOps";

type Tone = NonNullable<BadgeProps["variant"]>;

export const TRANSFER_STATUSES: TransferStatus[] = [
  "REQUESTED", "APPROVED", "RESERVED", "IN_TRANSIT", "RECEIVED", "COMPLETED", "REJECTED", "CANCELLED",
];

export const TRANSFER_TONE: Record<string, Tone> = {
  REQUESTED: "warning",
  APPROVED: "default",
  RESERVED: "default",
  DISPATCHED: "default",
  IN_TRANSIT: "default",
  RECEIVED: "success",
  COMPLETED: "success",
  REJECTED: "destructive",
  CANCELLED: "secondary",
};

export const statusLabel = (s: string) => s.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());

/** Workflow steps, in order, with the timestamp that proves each one. */
export const TRANSFER_STEPS: { status: TransferStatus; label: string; at: keyof BranchTransfer; by?: keyof BranchTransfer }[] = [
  { status: "REQUESTED", label: "Requested", at: "created_at", by: "requested_by" },
  { status: "APPROVED", label: "Approved", at: "approved_at", by: "approved_by" },
  { status: "RESERVED", label: "Stock reserved", at: "reserved_at" },
  { status: "IN_TRANSIT", label: "Dispatched / in transit", at: "dispatched_at", by: "dispatched_by" },
  { status: "RECEIVED", label: "Received", at: "received_at", by: "received_by" },
  { status: "COMPLETED", label: "Completed", at: "completed_at" },
];

/**
 * Actions the backend accepts for a status, and which end of the transfer must hold
 * `inventory.transfer` to perform them. The API re-checks both; this only hides dead buttons.
 */
type Side = "source" | "destination" | "either";

const CANCEL = { action: "cancel" as const, side: "either" as Side, label: "Cancel transfer", tone: "danger" as const };

/** Pre-dispatch states: nothing has left the source, so either end may still cancel. */
export const CANCELLABLE: TransferStatus[] = ["REQUESTED", "APPROVED", "RESERVED"];

const ACTIONS: Record<string, { action: TransferAction; side: Side; label: string; tone?: "danger" }[]> = {
  REQUESTED: [
    { action: "approve", side: "source", label: "Approve" },
    { action: "reject", side: "source", label: "Reject", tone: "danger" },
    CANCEL,
  ],
  APPROVED: [
    { action: "reserve", side: "source", label: "Reserve stock" },
    { action: "reject", side: "source", label: "Reject", tone: "danger" },
    CANCEL,
  ],
  RESERVED: [{ action: "dispatch", side: "source", label: "Dispatch" }, CANCEL],
  IN_TRANSIT: [{ action: "receive", side: "destination", label: "Receive" }],
  RECEIVED: [{ action: "complete", side: "destination", label: "Complete" }],
};

export function availableTransferActions(t: Pick<BranchTransfer, "status" | "source_branch_id" | "destination_branch_id">,
  can: (permission: string, branchId: string) => boolean) {
  return (ACTIONS[t.status] ?? []).filter((a) =>
    a.side === "either"
      ? can("inventory.transfer", t.source_branch_id) || can("inventory.transfer", t.destination_branch_id)
      : can("inventory.transfer", a.side === "source" ? t.source_branch_id : t.destination_branch_id)
  );
}

/** Quantities may be decimal strings from the API. */
export const num = (v: unknown) => {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
};

export const qtyText = (v: unknown) => num(v).toLocaleString(undefined, { maximumFractionDigits: 3 });

export const money = (v: unknown) =>
  num(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const when = (v: string | null | undefined) => (v ? new Date(v).toLocaleString() : "—");
