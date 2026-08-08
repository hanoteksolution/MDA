import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  CircleCheck,
  CircleDollarSign,
  Download,
  FileText,
  Loader2,
  PauseCircle,
  Pencil,
  Printer,
  Receipt,
  Search,
  Trash2,
  Wallet,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { usePermissions } from "@/hooks/usePermissions";
import { salesApi, type Invoice } from "@/services/api/sales";
import { posApi } from "@/services/api/pos";
import type { HeldSale } from "@/modules/pos/hooks/usePosCart";
import { POS_TAX_RATE, roundMoney } from "@/modules/pos/hooks/usePosCart";
import { invoiceToHeldSale } from "@/modules/pos/utils/heldSales";
import { printHeldSaleSlip } from "@/modules/pos/receipt/printCartSlip";
import { cn, formatCurrency } from "@/utils/cn";
import { useSalesReceipt } from "../hooks/useSalesReceipt";
import { appDialog } from "@/components/feedback/AppDialog";

type StatusTab = "all" | "paid" | "unpaid" | "on_hold";
type PaymentStatus = "paid" | "unpaid" | "on_hold";

const HELD_KEY = "mda_pos_held";
const RECEIPTS_UI_KEY = "mda_receipts_ui_v2";

const PAYMENT_LABELS: Record<string, string> = {
  cash: "Cash",
  mobile: "Mobile",
  on_account: "Pay later",
  invoice: "On account",
  card: "Card",
  bank: "Bank",
  hold: "On hold",
};

function loadLocalHeld(): HeldSale[] {
  try {
    const raw = localStorage.getItem(HELD_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HeldSale[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function invoicePaymentStatus(inv: Invoice): PaymentStatus {
  if (inv.status === "on_hold") return "on_hold";
  return inv.status === "paid" ? "paid" : "unpaid";
}

function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const config = {
    paid: {
      label: "Paid",
      className:
        "bg-emerald-500/15 text-emerald-700 ring-1 ring-inset ring-emerald-500/25 dark:text-emerald-400",
      dot: "bg-emerald-500",
    },
    unpaid: {
      label: "Unpaid",
      className:
        "bg-red-500/15 text-red-700 ring-1 ring-inset ring-red-500/25 dark:text-red-400",
      dot: "bg-red-500",
    },
    on_hold: {
      label: "On hold",
      className:
        "bg-orange-500/15 text-orange-700 ring-1 ring-inset ring-orange-500/25 dark:text-orange-400",
      dot: "bg-orange-500",
    },
  }[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide",
        config.className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {config.label}
    </span>
  );
}

type UiState = {
  tab: StatusTab;
  search: string;
  dateFrom: string;
  dateTo: string;
  waiter: string;
  page: number;
  pageSize: number;
};

function readStoredUi(): Partial<UiState> {
  try {
    const raw = sessionStorage.getItem(RECEIPTS_UI_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<UiState>;
  } catch {
    return {};
  }
}

function parseTab(raw: string | null | undefined): StatusTab {
  if (raw === "paid" || raw === "unpaid" || raw === "on_hold" || raw === "all") return raw;
  return "all";
}

export function ReceiptManagementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { hasPermission } = usePermissions();
  const canUpdate = hasPermission("sales.update");
  const canDelete = hasPermission("sales.delete");
  const migratedRef = useRef(false);

  const stored = useMemo(() => readStoredUi(), []);

  const [tab, setTab] = useState<StatusTab>(() =>
    parseTab(searchParams.get("tab") || stored.tab)
  );
  const [search, setSearch] = useState(
    () => searchParams.get("q") || stored.search || ""
  );
  const [searchInput, setSearchInput] = useState(
    () => searchParams.get("q") || stored.search || ""
  );
  const [dateFrom, setDateFrom] = useState(
    () => searchParams.get("from") || stored.dateFrom || ""
  );
  const [dateTo, setDateTo] = useState(
    () => searchParams.get("to") || stored.dateTo || ""
  );
  const [waiter, setWaiter] = useState(
    () => searchParams.get("waiter") || stored.waiter || ""
  );
  const [waiterInput, setWaiterInput] = useState(
    () => searchParams.get("waiter") || stored.waiter || ""
  );
  const [actionId, setActionId] = useState<string | null>(null);
  const [holdCount, setHoldCount] = useState(0);

  const initialPage = Math.max(
    1,
    Number(searchParams.get("page") || stored.page || 1) || 1
  );
  const initialPageSize = Math.max(
    10,
    Number(searchParams.get("size") || stored.pageSize || 20) || 20
  );

  // On-hold tab ignores the date range so held receipts are always visible.
  const invoiceFilters = useMemo(
    () => ({
      search: search || undefined,
      payment_state: tab === "all" ? undefined : tab,
      date_from: tab === "on_hold" ? undefined : dateFrom || undefined,
      date_to: tab === "on_hold" ? undefined : dateTo || undefined,
      waiter: waiter || undefined,
    }),
    [search, tab, dateFrom, dateTo, waiter]
  );

  const list = usePaginatedList(salesApi.invoices, invoiceFilters, {
    pageSize: initialPageSize,
    initialPage,
  });
  const { loadingId, printReceipt, downloadReceipt, markInvoicePaid } = useSalesReceipt();

  // Persist filters / page so refresh restores the same view
  useEffect(() => {
    const next: UiState = {
      tab,
      search,
      dateFrom,
      dateTo,
      waiter,
      page: list.page,
      pageSize: list.pageSize,
    };
    sessionStorage.setItem(RECEIPTS_UI_KEY, JSON.stringify(next));
    const params = new URLSearchParams();
    if (tab !== "all") params.set("tab", tab);
    if (search) params.set("q", search);
    if (dateFrom) params.set("from", dateFrom);
    if (dateTo) params.set("to", dateTo);
    if (waiter) params.set("waiter", waiter);
    if (list.page > 1) params.set("page", String(list.page));
    if (list.pageSize !== 20) params.set("size", String(list.pageSize));
    setSearchParams(params, { replace: true });
  }, [tab, search, dateFrom, dateTo, waiter, list.page, list.pageSize, setSearchParams]);

  const refreshHoldCount = useCallback(async () => {
    try {
      const res = await posApi.listHolds();
      const held = (res.data || []).map(invoiceToHeldSale);
      // Keep the POS cache in sync; preserve genuine offline holds (no server number yet)
      const offline = loadLocalHeld().filter((h) => h.cart?.length && !h.invoiceNumber);
      localStorage.setItem(HELD_KEY, JSON.stringify([...offline, ...held]));
      setHoldCount(held.length + offline.length);
    } catch {
      setHoldCount(0);
    }
  }, []);

  // Upload offline-created holds (held while the API was unreachable) to the server.
  // Cache copies of server holds carry invoiceNumber and are never re-uploaded —
  // otherwise paying/deleting a hold elsewhere would duplicate it here.
  useEffect(() => {
    if (migratedRef.current) return;
    migratedRef.current = true;
    void (async () => {
      const offlineHolds = loadLocalHeld().filter(
        (sale) => sale.cart?.length && !sale.invoiceNumber
      );

      const failed: HeldSale[] = [];
      for (const sale of offlineHolds) {
        try {
          await posApi.createHold({
            customer_id: sale.customerId && sale.customerId !== "walkin" ? sale.customerId : undefined,
            items: sale.cart.map((line) => ({
              product_id: line.id,
              quantity: line.qty,
              unit_price: line.price,
            })),
            discount_pct: sale.discountPct || 0,
            discount_amount: sale.discountAmount || 0,
            tax_rate: POS_TAX_RATE,
            payment_method: "cash",
            waiter_id: sale.waiterId,
            waiter_name: sale.waiterName,
            notes: sale.notes,
            label: sale.label,
          });
        } catch {
          failed.push(sale);
        }
      }

      try {
        const res = await posApi.listHolds();
        const held = (res.data || []).map(invoiceToHeldSale);
        localStorage.setItem(HELD_KEY, JSON.stringify([...failed, ...held]));
        setHoldCount(held.length + failed.length);
      } catch {
        /* keep existing cache when offline */
      }
      if (offlineHolds.length) list.reload();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-time sync on mount
  }, []);

  useEffect(() => {
    void refreshHoldCount();
  }, [refreshHoldCount, list.data]);

  const applySearch = () => {
    setSearch(searchInput.trim());
    setWaiter(waiterInput.trim());
  };

  const handleDeleteInvoice = async (inv: Invoice) => {
    if (!canDelete) return;
    const ok = await appDialog.confirm(
      `Delete receipt ${inv.number}? Stock will be restored and this cannot be undone.`,
      { title: "Delete receipt", tone: "danger", confirmLabel: "Delete" }
    );
    if (!ok) return;
    setActionId(inv.id);
    try {
      await salesApi.deleteInvoice(inv.id);
      list.reload();
      void refreshHoldCount();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete receipt");
    } finally {
      setActionId(null);
    }
  };

  const handleMarkPaid = async (inv: Invoice) => {
    if (!canUpdate || inv.status === "paid") return;
    const ok = await appDialog.confirm(
      `Mark ${inv.number} as paid for ${formatCurrency(inv.total_amount)}?`,
      { title: "Mark as paid", confirmLabel: "Mark paid" }
    );
    if (!ok) return;
    setActionId(inv.id);
    try {
      await markInvoicePaid(inv.id);
      list.reload();
      void refreshHoldCount();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    } finally {
      setActionId(null);
    }
  };

  const handleMarkUnpaid = async (inv: Invoice) => {
    if (!canUpdate || (inv.status !== "paid" && inv.status !== "on_hold")) return;
    const ok = await appDialog.confirm(
      `Mark ${inv.number} as unpaid (pay later)?`,
      { title: "Mark as unpaid", confirmLabel: "Mark unpaid" }
    );
    if (!ok) return;
    setActionId(inv.id);
    try {
      await salesApi.markInvoiceUnpaid(inv.id);
      list.reload();
      void refreshHoldCount();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as unpaid");
    } finally {
      setActionId(null);
    }
  };

  const handlePrintHold = async (inv: Invoice) => {
    setActionId(inv.id);
    try {
      const detail = inv.items?.length ? inv : (await salesApi.getInvoice(inv.id)).data;
      const sale = invoiceToHeldSale(detail);
      const disc = sale.discountAmount || 0;
      const tax = roundMoney(sale.subtotal * POS_TAX_RATE);
      const total = roundMoney(Math.max(0, sale.subtotal - disc) + tax);
      await printHeldSaleSlip({
        label: sale.label,
        customerName: detail.customer_name || "Walk-in Customer",
        waiterName: sale.waiterName,
        branchName: detail.branch_name,
        cart: sale.cart,
        subtotal: sale.subtotal,
        discount: disc,
        tax,
        taxRate: POS_TAX_RATE,
        grandTotal: total,
        notes: sale.notes,
        heldAt: new Date(sale.heldAt).toLocaleString(),
        // Reprints show the invoice's own receipt number
        refNumber: detail.number,
      });
    } finally {
      setActionId(null);
    }
  };

  const pageTotal = list.data.reduce((s, r) => s + r.total_amount, 0);
  const pageDue = list.data.reduce((s, r) => {
    if (invoicePaymentStatus(r) === "paid") return s;
    return s + (r.balance_due ?? Math.max(0, r.total_amount - r.amount_paid));
  }, 0);

  const busyId = loadingId || actionId;

  const columns: Column<Invoice>[] = [
    {
      key: "number",
      header: "Receipt",
      cell: (r) => (
        <div className="min-w-[140px]">
          <p className="font-mono text-sm font-semibold tracking-tight">{r.number}</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            {r.item_count} item{r.item_count === 1 ? "" : "s"}
          </p>
        </div>
      ),
      exportValue: (r) => r.number,
    },
    {
      key: "customer",
      header: "Customer",
      cell: (r) => (
        <div className="min-w-[120px]">
          <p className="text-sm font-medium">{r.customer_name}</p>
          <p className="text-[11px] text-muted-foreground">{r.branch_name}</p>
        </div>
      ),
      exportValue: (r) => r.customer_name,
    },
    {
      key: "date",
      header: "Date",
      cell: (r) => (
        <span className="text-sm tabular-nums text-muted-foreground">
          {r.issue_date || r.date}
        </span>
      ),
      exportValue: (r) => r.issue_date || r.date,
    },
    {
      key: "waiter",
      header: "Waiter",
      cell: (r) => <span className="text-sm">{r.waiter_name || "—"}</span>,
      exportValue: (r) => r.waiter_name || "",
    },
    {
      key: "payment",
      header: "Payment",
      cell: (r) => (
        <span className="text-sm text-muted-foreground">
          {r.payment_method
            ? PAYMENT_LABELS[r.payment_method] || r.payment_method
            : "—"}
        </span>
      ),
      exportValue: (r) => r.payment_method || "",
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => <PaymentStatusBadge status={invoicePaymentStatus(r)} />,
      exportValue: (r) => {
        const s = invoicePaymentStatus(r);
        return s === "on_hold" ? "On hold" : s === "paid" ? "Paid" : "Unpaid";
      },
    },
    {
      key: "total",
      header: "Total",
      className: "text-right",
      cell: (r) => {
        const status = invoicePaymentStatus(r);
        const due = r.balance_due ?? Math.max(0, r.total_amount - r.amount_paid);
        return (
          <div className="text-right">
            <p className="text-sm font-semibold tabular-nums">{formatCurrency(r.total_amount)}</p>
            {status !== "paid" && due > 0 ? (
              <p className="text-[11px] font-medium text-red-600 tabular-nums dark:text-red-400">
                Due {formatCurrency(due)}
              </p>
            ) : status === "paid" ? (
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Settled</p>
            ) : null}
          </div>
        );
      },
      exportValue: (r) => formatCurrency(r.total_amount),
    },
    {
      key: "actions",
      header: "Actions",
      exportable: false,
      cell: (r) => {
        const status = invoicePaymentStatus(r);
        const busy = busyId === r.id;
        return (
          <div className="flex flex-wrap items-center justify-end gap-1">
            {canUpdate && status !== "paid" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1 rounded-lg px-2 text-emerald-700 hover:bg-emerald-500/10 hover:text-emerald-800"
                title="Mark as paid"
                disabled={busy}
                onClick={() => void handleMarkPaid(r)}
              >
                {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CircleCheck className="h-3.5 w-3.5" />}
                <span className="text-xs font-semibold">Paid</span>
              </Button>
            )}
            {canUpdate && status !== "unpaid" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1 rounded-lg px-2 text-red-700 hover:bg-red-500/10 hover:text-red-800"
                title="Mark as unpaid"
                disabled={busy}
                onClick={() => void handleMarkUnpaid(r)}
              >
                <CircleDollarSign className="h-3.5 w-3.5" />
                <span className="text-xs font-semibold">Unpaid</span>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              title="Print"
              disabled={busy}
              onClick={() => {
                if (status === "on_hold") void handlePrintHold(r);
                else void printReceipt(r.id);
              }}
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
            </Button>
            {status !== "on_hold" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                title="Download PDF"
                disabled={busy}
                onClick={() => void downloadReceipt(r.id)}
              >
                <Download className="h-4 w-4" />
              </Button>
            )}
            {canUpdate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                title="Edit"
                onClick={() => navigate(`/sales/invoices/${r.id}/edit`)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
            {status === "on_hold" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-orange-600 hover:text-orange-700"
                title="Resume in POS"
                onClick={() => navigate(`/pos?resume=${r.id}`)}
              >
                <PauseCircle className="h-4 w-4" />
              </Button>
            )}
            {canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                title="Delete"
                disabled={busy}
                onClick={() => void handleDeleteInvoice(r)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <PageLayout
      title="Receipts"
      description="Manage paid, unpaid, and on-hold receipts — print, download, edit, or delete."
      breadcrumbs={["Home", "Receipts"]}
    >
      <KpiGrid>
        <button type="button" className="text-left" onClick={() => setTab("all")} title="Show all receipts">
          <KpiCard
            title="Results"
            value={String(list.total)}
            icon={<Receipt className="h-5 w-5" />}
            loading={list.loading}
            className={cn("cursor-pointer transition hover:-translate-y-0.5", tab === "all" && "ring-2 ring-primary/40")}
          />
        </button>
        <button type="button" className="text-left" onClick={() => setTab("paid")} title="Show paid receipts">
          <KpiCard
            title="Paid (page total)"
            value={formatCurrency(pageTotal)}
            icon={<FileText className="h-5 w-5" />}
            accent="success"
            className={cn("cursor-pointer transition hover:-translate-y-0.5", tab === "paid" && "ring-2 ring-emerald-500/40")}
          />
        </button>
        <button type="button" className="text-left" onClick={() => setTab("unpaid")} title="Show unpaid receipts">
          <KpiCard
            title="Unpaid (still due)"
            value={formatCurrency(pageDue)}
            icon={<Wallet className="h-5 w-5" />}
            accent="warning"
            className={cn("cursor-pointer transition hover:-translate-y-0.5", tab === "unpaid" && "ring-2 ring-red-500/40")}
          />
        </button>
        <button type="button" className="text-left" onClick={() => setTab("on_hold")} title="Show on-hold receipts">
          <KpiCard
            title="On hold"
            value={String(holdCount)}
            icon={<PauseCircle className="h-5 w-5" />}
            accent="warning"
            className={cn("cursor-pointer transition hover:-translate-y-0.5", tab === "on_hold" && "ring-2 ring-orange-500/40")}
          />
        </button>
      </KpiGrid>

      <div className="rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-muted/20 p-4 shadow-sm sm:p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative lg:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
              placeholder="Receipt # or customer"
              className="h-11 rounded-xl border-border/70 bg-background/80 pl-9"
            />
          </div>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-11 rounded-xl border-border/70 bg-background/80"
          />
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-11 rounded-xl border-border/70 bg-background/80"
          />
          <Input
            value={waiterInput}
            onChange={(e) => setWaiterInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applySearch()}
            placeholder="Waiter"
            className="h-11 rounded-xl border-border/70 bg-background/80"
          />
          <div className="flex gap-2">
            <Button className="h-11 flex-1 rounded-xl font-semibold" onClick={applySearch}>
              Apply filters
            </Button>
            {(dateFrom || dateTo) && (
              <Button
                type="button"
                variant="secondary"
                className="h-11 rounded-xl"
                onClick={() => {
                  setDateFrom("");
                  setDateTo("");
                }}
              >
                All dates
              </Button>
            )}
          </div>
        </div>
      </div>

      <TabNav
        tabs={[
          { id: "all", label: "All" },
          { id: "paid", label: "Paid" },
          { id: "unpaid", label: "Unpaid" },
          { id: "on_hold", label: "On hold", count: holdCount },
        ]}
        active={tab}
        onChange={(id) => setTab(id as StatusTab)}
      />

      <ContentSection
        title="Receipt register"
        description="Paid (green) · On hold (orange) · Unpaid (red). Use Paid / Unpaid on each row. Filters and page survive refresh."
        noPadding
      >
        <DataTable
          embedded
          exportTitle="Receipts"
          columns={columns}
          data={list.data}
          loading={list.loading}
          emptyMessage={
            tab === "on_hold"
              ? "No on-hold receipts. Hold a sale from POS — it is saved to the server."
              : dateFrom || dateTo
                ? "No receipts in this date range. Clear the dates to see older sales."
                : "No receipts found."
          }
          searchPlaceholder="Filter this page..."
          page={list.page}
          pageSize={list.pageSize}
          total={list.total}
          onPageChange={list.setPage}
          onPageSizeChange={list.setPageSize}
          clientPagination={false}
          defaultPageSize={20}
        />
      </ContentSection>
    </PageLayout>
  );
}
