import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CircleCheck,
  Download,
  FileText,
  Loader2,
  Pencil,
  Printer,
  Receipt,
  Search,
  Trash2,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { usePermissions } from "@/hooks/usePermissions";
import { PosReceiptView } from "@/modules/pos/components/PosReceiptView";
import { salesApi, type Invoice } from "@/services/api/sales";
import type { PosReceipt } from "@/services/api/pos";
import { cn, formatCurrency } from "@/utils/cn";
import { useSalesReceipt } from "../hooks/useSalesReceipt";
import { appDialog } from "@/components/feedback/AppDialog";

type PaymentTab = "all" | "paid" | "unpaid";

const PAYMENT_LABELS: Record<string, string> = {
  cash: "Cash",
  mobile: "Mobile",
  on_account: "Pay later",
  invoice: "On account",
  card: "Card",
  bank: "Bank",
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function monthStartIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function canMarkPaid(status: string) {
  return status !== "paid" && status !== "cancelled";
}

function statusVariant(status: string): "success" | "warning" | "secondary" | "destructive" {
  if (status === "paid") return "success";
  if (status === "overdue" || status === "cancelled") return "destructive";
  if (status === "sent" || status === "draft") return "warning";
  return "secondary";
}

export function ReceiptManagementPage() {
  const { hasPermission } = usePermissions();
  const canUpdate = hasPermission("sales.update");
  const canDelete = hasPermission("sales.delete");
  const [tab, setTab] = useState<PaymentTab>("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [dateFrom, setDateFrom] = useState(monthStartIso);
  const [dateTo, setDateTo] = useState(todayIso);
  const [waiter, setWaiter] = useState("");
  const [waiterInput, setWaiterInput] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [preview, setPreview] = useState<PosReceipt | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [marking, setMarking] = useState(false);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      payment_state: tab === "all" ? undefined : tab,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      waiter: waiter || undefined,
    }),
    [search, tab, dateFrom, dateTo, waiter]
  );

  const list = usePaginatedList(salesApi.invoices, filters, { pageSize: 20 });
  const {
    loadingId,
    printReceipt,
    printInvoice,
    downloadReceipt,
    markInvoicePaid,
  } = useSalesReceipt();

  const selected = list.data.find((r) => r.id === selectedId) ?? null;

  const loadPreview = useCallback(async (invoiceId: string) => {
    setPreviewLoading(true);
    try {
      const res = await salesApi.getInvoiceReceipt(invoiceId);
      setPreview(res.data);
    } catch {
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!list.loading && list.data.length > 0) {
      const stillThere = selectedId && list.data.some((r) => r.id === selectedId);
      if (!stillThere) {
        setSelectedId(list.data[0].id);
      }
    } else if (!list.loading && list.data.length === 0) {
      setSelectedId(null);
      setPreview(null);
    }
  }, [list.loading, list.data, selectedId]);

  useEffect(() => {
    if (selectedId) loadPreview(selectedId);
  }, [selectedId, loadPreview]);

  const applySearch = () => {
    setSearch(searchInput.trim());
    setWaiter(waiterInput.trim());
  };

  const handleSelect = (inv: Invoice) => {
    setSelectedId(inv.id);
  };

  const handleMarkPaid = async () => {
    if (!selected || !canMarkPaid(selected.status) || !canUpdate) return;
    if (
      !window.confirm(
        `Mark ${selected.number} as paid for ${formatCurrency(selected.total_amount)}?`
      )
    ) {
      return;
    }
    setMarking(true);
    try {
      await markInvoicePaid(selected.id);
      list.reload();
      await loadPreview(selected.id);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    } finally {
      setMarking(false);
    }
  };

  const handleDelete = async () => {
    if (!selected || !canDelete) return;
    const ok = await appDialog.confirm(
      `Delete receipt ${selected.number}? This cannot be undone.`,
      { title: "Delete receipt", tone: "danger", confirmLabel: "Delete" },
    );
    if (!ok) return;
    try {
      await salesApi.deleteInvoice(selected.id);
      setSelectedId(null);
      setPreview(null);
      list.reload();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete receipt");
    }
  };

  const unpaidCount = list.data.filter((r) => canMarkPaid(r.status)).length;
  const paidCount = list.data.filter((r) => r.status === "paid").length;
  const pageTotal = list.data.reduce((s, r) => s + r.total_amount, 0);
  const pageDue = list.data.reduce(
    (s, r) => s + (r.balance_due ?? Math.max(0, r.total_amount - r.amount_paid)),
    0
  );

  return (
    <PageLayout
      title="Receipts"
      description="Search, preview, print, and settle receipts in one place."
      breadcrumbs={["Home", "Receipts"]}
    >
      {/* KPI strip */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "On this page", value: String(list.total), sub: `${list.data.length} shown`, icon: Receipt },
          { label: "Page total", value: formatCurrency(pageTotal), sub: "Listed receipts", icon: FileText },
          { label: "Still due", value: formatCurrency(pageDue), sub: `${unpaidCount} unpaid here`, icon: Wallet },
          { label: "Paid here", value: String(paidCount), sub: "On current page", icon: CircleCheck },
        ].map(({ label, value, sub, icon: Icon }) => (
          <div
            key={label}
            className="rounded-2xl border border-border/80 bg-gradient-to-br from-card to-muted/30 px-5 py-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
                <p className="mt-1 text-xl font-semibold tracking-tight">{value}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
              </div>
              <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                <Icon className="h-4 w-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {([
            { id: "all", label: "All" },
            { id: "paid", label: "Paid" },
            { id: "unpaid", label: "Unpaid" },
          ] as const).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "rounded-full px-4 py-1.5 text-sm font-medium transition-all",
                tab === t.id
                  ? "bg-foreground text-background shadow-sm"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative lg:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
              placeholder="Receipt # or customer"
              className="h-11 rounded-xl pl-9"
            />
          </div>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-11 rounded-xl"
          />
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="h-11 rounded-xl"
          />
          <Input
            value={waiterInput}
            onChange={(e) => setWaiterInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applySearch()}
            placeholder="Waiter"
            className="h-11 rounded-xl"
          />
          <Button className="h-11 rounded-xl" onClick={applySearch}>
            Apply
          </Button>
        </div>
      </div>

      {/* Split workspace */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,420px)]">
        {/* List */}
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
            <div>
              <h2 className="text-sm font-semibold">Receipt list</h2>
              <p className="text-xs text-muted-foreground">
                {list.total} result{list.total === 1 ? "" : "s"} · select to preview
              </p>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 rounded-lg text-xs"
                disabled={list.page <= 1}
                onClick={() => list.setPage(list.page - 1)}
              >
                Prev
              </Button>
              <span className="px-2 text-xs text-muted-foreground">
                {list.page}/{list.totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 rounded-lg text-xs"
                disabled={list.page >= list.totalPages}
                onClick={() => list.setPage(list.page + 1)}
              >
                Next
              </Button>
            </div>
          </div>

          <div className="max-h-[min(68vh,720px)] overflow-y-auto scrollbar-thin">
            {list.loading ? (
              <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                Loading receipts…
              </div>
            ) : list.data.length === 0 ? (
              <div className="px-6 py-20 text-center">
                <Receipt className="mx-auto h-10 w-10 text-muted-foreground/40" />
                <p className="mt-3 text-sm font-medium">No receipts found</p>
                <p className="mt-1 text-xs text-muted-foreground">Try another date range or clear filters.</p>
              </div>
            ) : (
              <ul className="divide-y divide-border/70">
                {list.data.map((inv) => {
                  const active = inv.id === selectedId;
                  const due = inv.balance_due ?? Math.max(0, inv.total_amount - inv.amount_paid);
                  const pm = inv.payment_method
                    ? PAYMENT_LABELS[inv.payment_method] || inv.payment_method
                    : null;
                  return (
                    <li key={inv.id}>
                      <button
                        type="button"
                        onClick={() => handleSelect(inv)}
                        className={cn(
                          "group flex w-full items-start gap-4 px-5 py-4 text-left transition-colors",
                          active
                            ? "bg-primary/[0.06] ring-1 ring-inset ring-primary/20"
                            : "hover:bg-muted/40"
                        )}
                      >
                        <div
                          className={cn(
                            "mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                            inv.status === "paid"
                              ? "bg-emerald-500/10 text-emerald-600"
                              : "bg-amber-500/10 text-amber-600"
                          )}
                        >
                          <Receipt className="h-4.5 w-4.5 h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-sm font-semibold tracking-tight">
                              {inv.number}
                            </span>
                            <Badge variant={statusVariant(inv.status)} className="capitalize">
                              {inv.status}
                            </Badge>
                            {pm && (
                              <span className="text-[11px] text-muted-foreground">{pm}</span>
                            )}
                          </div>
                          <p className="mt-0.5 truncate text-sm text-foreground/90">{inv.customer_name}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {inv.issue_date}
                            {inv.waiter_name ? ` · ${inv.waiter_name}` : ""}
                            {` · ${inv.item_count} item${inv.item_count === 1 ? "" : "s"}`}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-sm font-semibold tabular-nums">
                            {formatCurrency(inv.total_amount)}
                          </p>
                          {due > 0 && inv.status !== "paid" ? (
                            <p className="mt-0.5 text-xs font-medium text-amber-600 tabular-nums">
                              Due {formatCurrency(due)}
                            </p>
                          ) : (
                            <p className="mt-0.5 text-xs text-emerald-600">Settled</p>
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

        {/* Preview panel */}
        <div className="flex min-h-[520px] flex-col overflow-hidden rounded-2xl border border-border bg-gradient-to-b from-muted/40 to-card shadow-sm xl:sticky xl:top-4 xl:self-start">
          <div className="border-b border-border px-5 py-3.5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-sm font-semibold">Live preview</h2>
                <p className="truncate font-mono text-xs text-muted-foreground">
                  {selected?.number ?? "Select a receipt"}
                </p>
              </div>
              {selected && canMarkPaid(selected.status) && canUpdate && (
                <Button
                  size="sm"
                  className="h-9 shrink-0 gap-1.5 rounded-xl"
                  disabled={marking || loadingId === selected.id}
                  onClick={handleMarkPaid}
                >
                  {marking ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CircleCheck className="h-3.5 w-3.5" />
                  )}
                  Mark paid
                </Button>
              )}
            </div>

            {selected && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-9 gap-1.5 rounded-xl"
                  disabled={loadingId === selected.id}
                  onClick={() => printReceipt(selected.id)}
                >
                  {loadingId === selected.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Printer className="h-3.5 w-3.5" />
                  )}
                  Thermal
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-9 gap-1.5 rounded-xl"
                  disabled={loadingId === selected.id}
                  onClick={() => printInvoice(selected.id)}
                >
                  <FileText className="h-3.5 w-3.5" />
                  A4
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 gap-1.5 rounded-xl border border-border"
                  disabled={loadingId === selected.id}
                  onClick={() => downloadReceipt(selected.id)}
                >
                  <Download className="h-3.5 w-3.5" />
                  PDF
                </Button>
                {canUpdate && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 gap-1.5 rounded-xl border border-border"
                    asChild
                  >
                    <Link to={`/sales/invoices/${selected.id}/edit`}>
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </Link>
                  </Button>
                )}
                {canDelete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 gap-1.5 rounded-xl border border-border text-destructive hover:text-destructive"
                    onClick={() => void handleDelete()}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </Button>
                )}
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
            {previewLoading ? (
              <div className="flex h-64 items-center justify-center gap-2 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                Loading preview…
              </div>
            ) : preview ? (
              <PosReceiptView
                receipt={preview}
                mode="both"
                defaultPreview="receipt"
                showActions={false}
                compact
              />
            ) : (
              <div className="flex h-64 flex-col items-center justify-center text-center">
                <div className="rounded-2xl border border-dashed border-border bg-muted/30 px-8 py-10">
                  <Receipt className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-3 text-sm font-medium text-muted-foreground">
                    Choose a receipt to preview
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
