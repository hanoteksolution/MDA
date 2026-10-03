import { apiRequest } from "@/services/api/http";
import type { ProductAvailability } from "@/types/models/catalog";

/**
 * Multi-branch operations: branch transfers, cross-branch stock search, branch reports and the
 * branch overview. Every figure is computed by the backend (reports reconcile consolidated vs
 * per-branch totals server-side); the UI only renders it.
 */

export type TransferStatus =
  | "REQUESTED" | "APPROVED" | "RESERVED" | "DISPATCHED" | "IN_TRANSIT" | "RECEIVED" | "COMPLETED" | "REJECTED" | "CANCELLED";

export interface TransferLine {
  id: string;
  product_id: string;
  product_sku: string;
  product_name?: string;
  quantity_requested: number;
  quantity_reserved: number;
  quantity_dispatched: number;
  quantity_received: number;
  discrepancy_quantity: number;
  in_transit_quantity: number;
}

export interface BranchTransfer {
  id: string;
  request_number: string;
  status: TransferStatus;
  source_branch_id: string;
  source_branch_name: string;
  destination_branch_id: string;
  destination_branch_name: string;
  source_warehouse_name?: string;
  destination_warehouse_name?: string;
  notes: string;
  rejection_reason: string;
  requested_by: string | null;
  approved_by?: string | null;
  dispatched_by?: string | null;
  received_by?: string | null;
  approved_at: string | null;
  reserved_at: string | null;
  dispatched_at: string | null;
  received_at: string | null;
  completed_at: string | null;
  created_at: string;
  line_count?: number;
  total_quantity?: number;
  lines?: TransferLine[];
  /** Detail only: audit trail and the cancellation record. */
  history?: { at: string; by: string | null; action: string; status: string | null; reason: string }[];
  cancelled_by?: string | null;
  cancelled_at?: string | null;
  cancel_reason?: string;
}

export interface TransferDestination {
  id: string;
  name: string;
  code: string;
  /** null when the caller may not see that branch's warehouses (its default is used). */
  warehouses: { id: string; name: string; is_default: boolean }[] | null;
}

export interface Paged<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

export type TransferAction = "approve" | "reject" | "reserve" | "dispatch" | "receive" | "complete" | "cancel";

export interface CrossBranchSearchResult {
  branch_id: string;
  branch_name: string;
  can_view_other_branches: boolean;
  results: ProductAvailability[];
}

export type BranchReportName =
  | "sales" | "stock-value" | "profit-loss" | "cash" | "purchases" | "inventory" | "expenses" | "transfers";

export type Figures = Record<string, number>;

export interface BranchReport {
  report: BranchReportName;
  mode: "single" | "multi" | "consolidated";
  date_from: string | null;
  date_to: string | null;
  branches: ({ branch_id: string; branch_code: string; branch_name: string } & Record<string, number | string>)[];
  consolidated: Figures;
  unassigned?: Figures;
  reconciles: boolean;
}

export interface BranchOverviewRow {
  branch_id: string;
  code: string;
  name: string;
  status: string;
  is_active: boolean;
  is_default: boolean;
  branch_type: string;
  phone: string;
  address: string;
  company_id: string | null;
  company_name: string;
  managers: string[];
  users: number;
  warehouses: number;
  pos_terminals: number;
  cash_registers: number;
  open_shifts: number;
  sales_net: number;
  sales_invoices: number;
  stock_value: number;
  low_stock: number;
  out_of_stock: number;
  transfers_open: number;
  transfers_awaiting_approval: number;
}

export type Query = Record<string, string | number | undefined | null>;

export function qs(params: Query = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

type Envelope<T> = { data: T; message?: string };

export const branchOpsApi = {
  transfers: (params?: Query) => apiRequest<Envelope<Paged<BranchTransfer>>>(`/inventory/branch-transfers/${qs(params)}`),
  transfer: (id: string) => apiRequest<Envelope<BranchTransfer>>(`/inventory/branch-transfers/${id}/`),
  requestTransfer: (body: {
    source_branch_id: string;
    destination_branch_id: string;
    destination_warehouse_id?: string;
    lines: { product_id: string; quantity: string }[];
    notes?: string;
    /** Push: the source approves its own outgoing transfer at creation. */
    approve?: boolean;
  }) => apiRequest<Envelope<BranchTransfer>>("/inventory/branch-transfers/", { method: "POST", body: JSON.stringify(body) }),
  transferAction: (id: string, action: TransferAction, body: Record<string, unknown> = {}) =>
    apiRequest<Envelope<BranchTransfer>>(`/inventory/branch-transfers/${id}/${action}/`, { method: "POST", body: JSON.stringify(body) }),
  transferDestinations: () => apiRequest<Envelope<TransferDestination[]>>("/inventory/branch-transfers/destinations/"),
  crossBranchSearch: (search: string) =>
    apiRequest<Envelope<CrossBranchSearchResult>>(`/inventory/cross-branch-search/${qs({ search })}`),
  report: (report: BranchReportName, params?: Query) =>
    apiRequest<Envelope<BranchReport>>(`/reports/branch/${report}/${qs(params)}`),
  overview: (params?: Query) =>
    apiRequest<Envelope<{ mode: string; branches: BranchOverviewRow[] }>>(`/reports/branch-overview/${qs(params)}`),
};
