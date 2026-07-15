import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import {
  Receipt,
  FileText,
  TrendingUp,
  DollarSign,
  Plus,
  Download,
  Pencil,
  Printer,
  Eye,
  Loader2,
  FileOutput,
  FileDown,
  Truck,
  CircleCheck,
  Trash2,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { salesApi } from "@/services/api/sales";
import { formatCurrency } from "@/utils/cn";
import type { Invoice, Quotation, SalesSummary } from "@/services/api/sales";
import { SalesReceiptDialog } from "../components/SalesReceiptDialog";
import { useSalesReceipt } from "../hooks/useSalesReceipt";
import { appDialog } from "@/components/feedback/AppDialog";
import { usePermissions } from "@/hooks/usePermissions";

const INVOICE_STATUS: Record<string, "secondary" | "warning" | "success" | "destructive"> = {
  draft: "secondary", sent: "warning", paid: "success", overdue: "destructive", cancelled: "destructive",
};

function canMarkPaid(status: string) {
  return status !== "paid" && status !== "cancelled";
}

export function SalesPage() {
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("sales.create");
  const canUpdate = hasPermission("sales.update");
  const canDelete = hasPermission("sales.delete");
  const [tab, setTab] = useState("invoices");
  const [search, setSearch] = useState("");
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const invoiceList = usePaginatedList(salesApi.invoices, { search });
  const quotationList = usePaginatedList(salesApi.quotations, { search });
  const activeList = tab === "invoices" ? invoiceList : quotationList;
  const docs = activeList.data;
  const loading = activeList.loading;
  const {
    loadingId: receiptLoadingId,
    documentPreview,
    printReceipt,
    printInvoice,
    printDeliveryNote,
    printQuotation,
    downloadReceipt,
    downloadDeliveryNote,
    downloadQuotation,
    viewInvoice,
    viewThermalReceipt,
    closePreview,
    markInvoicePaid,
  } = useSalesReceipt();

  const refreshSummary = () => {
    salesApi.summary()
      .then((sum) => setSummary(sum.data))
      .catch(() => setSummary(null));
  };

  const handleMarkPaid = async (invoice: Invoice) => {
    if (
      !window.confirm(
        `Mark ${invoice.number} as paid for ${formatCurrency(invoice.total_amount)}?`
      )
    ) {
      return;
    }
    try {
      await markInvoicePaid(invoice.id);
      invoiceList.reload();
      refreshSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    }
  };

  const handleMarkPaidFromDialog = async (invoiceId: string) => {
    const inv = invoiceList.data.find((i) => i.id === invoiceId) as Invoice | undefined;
    if (inv && !window.confirm(`Mark ${inv.number} as paid for ${formatCurrency(inv.total_amount)}?`)) {
      return;
    }
    try {
      await markInvoicePaid(invoiceId);
      invoiceList.reload();
      refreshSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not mark as paid");
    }
  };

  const handleDelete = async (doc: Invoice | Quotation) => {
    const label = tab === "invoices" ? "invoice/receipt" : "quotation";
    const ok = await appDialog.confirm(
      `Delete ${label} ${doc.number}? This cannot be undone.`,
      { title: `Delete ${label}`, tone: "danger", confirmLabel: "Delete" },
    );
    if (!ok) return;
    try {
      if (tab === "invoices") await salesApi.deleteInvoice(doc.id);
      else await salesApi.deleteQuotation(doc.id);
      activeList.reload();
      refreshSummary();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : `Could not delete ${label}`);
    }
  };

  useEffect(() => {
    salesApi.summary()
      .then((sum) => setSummary(sum.data))
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, []);

  const columns: Column<Invoice | Quotation>[] = [
    { key: "number", header: tab === "invoices" ? "Invoice #" : "Quote #", cell: (r) => <span className="font-mono text-xs font-medium">{r.number}</span>, exportValue: (r) => r.number },
    { key: "customer", header: "Customer", cell: (r) => r.customer_name, exportValue: (r) => r.customer_name },
    { key: "date", header: "Date", cell: (r) => r.date, exportValue: (r) => r.date },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={INVOICE_STATUS[r.status] ?? "secondary"} className="capitalize">{r.status}</Badge>
      ),
      exportValue: (r) => r.status,
    },
    { key: "total", header: "Total", cell: (r) => formatCurrency(r.total_amount), exportValue: (r) => formatCurrency(r.total_amount) },
    {
      key: "actions",
      header: "",
      exportable: false,
      cell: (r) => {
        const busy = receiptLoadingId === r.id;
        const inv = tab === "invoices" ? (r as Invoice) : null;
        const unpaid = inv && canMarkPaid(inv.status);
        return (
          <div className="flex items-center justify-end gap-0.5">
            {tab === "invoices" ? (
              <>
                {unpaid && canUpdate && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 px-2 text-emerald-600 hover:text-emerald-700"
                    title="Mark as paid"
                    disabled={busy}
                    onClick={() => handleMarkPaid(inv)}
                  >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CircleCheck className="h-4 w-4" />}
                    <span className="hidden text-xs font-semibold lg:inline">Paid</span>
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Preview tax invoice (A4)"
                  disabled={busy}
                  onClick={() => viewInvoice(r.id)}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Preview thermal receipt"
                  disabled={busy}
                  onClick={() => viewThermalReceipt(r.id)}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Receipt className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Print thermal receipt (80mm)"
                  disabled={busy}
                  onClick={() => printReceipt(r.id)}
                >
                  <Printer className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 px-2 text-primary"
                  title="Print Tax Invoice (A4) — premium layout"
                  disabled={busy}
                  onClick={() => printInvoice(r.id)}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
                  <span className="hidden text-xs font-semibold lg:inline">Invoice</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 px-2 text-primary"
                  title="Print Delivery Note (A4) — premium layout"
                  disabled={busy}
                  onClick={() => void printDeliveryNote(r.id)}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Truck className="h-4 w-4" />}
                  <span className="hidden text-xs font-semibold lg:inline">DN</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Download Delivery Note PDF"
                  disabled={busy}
                  onClick={() => void downloadDeliveryNote(r.id)}
                >
                  <FileDown className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Download tax invoice PDF"
                  disabled={busy}
                  onClick={() => downloadReceipt(r.id)}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1 px-2 text-primary"
                  title="Print Quotation (A4) — premium layout"
                  disabled={busy}
                  onClick={() => printQuotation(r.id)}
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
                  <span className="hidden text-xs font-semibold lg:inline">Quote</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  title="Download quotation PDF"
                  disabled={busy}
                  onClick={() => downloadQuotation(r.id)}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            {canUpdate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                title="Edit"
                onClick={() =>
                  navigate(tab === "invoices" ? `/sales/invoices/${r.id}/edit` : `/sales/quotations/${r.id}/edit`)
                }
              >
                <Pencil className="h-4 w-4" />
              </Button>
            )}
            {canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                title="Delete"
                onClick={() => void handleDelete(r)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  const newPath = tab === "invoices" ? "/sales/invoices/new" : "/sales/quotations/new";

  return (
    <PageLayout
      title="Sales"
      description="Invoices, quotations, receipts, and sales history."
      breadcrumbs={["Home", "Sales"]}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" disabled>
            <Download className="h-4 w-4" />
            Export
          </Button>
          {canCreate && (
            <Button asChild>
              <Link to={newPath}>
                <Plus className="h-4 w-4" />
                {tab === "invoices" ? "New Invoice" : "New Quotation"}
              </Link>
            </Button>
          )}
        </div>
      }
    >
      <KpiGrid>
        <KpiCard title="Today's Sales" value={formatCurrency(summary?.today_sales ?? 0)} icon={<DollarSign className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="This Month" value={formatCurrency(summary?.month_sales ?? 0)} icon={<TrendingUp className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Open Invoices" value={String(summary?.open_invoices ?? 0)} icon={<Receipt className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Quotations" value={String(summary?.quotations_count ?? 0)} icon={<FileText className="h-5 w-5" />} loading={summaryLoading} />
      </KpiGrid>

      <TabNav
        tabs={[
          { id: "invoices", label: "Invoices", count: invoiceList.total },
          { id: "quotations", label: "Quotations", count: quotationList.total },
        ]}
        active={tab}
        onChange={setTab}
      />

      <ContentSection
        title={tab === "invoices" ? "Invoices" : "Quotations"}
        description={tab === "invoices" ? "All customer invoices and payment status" : "Pending quotes awaiting conversion"}
        noPadding
      >
        <DataTable
          embedded
          exportTitle={tab === "invoices" ? "Invoices" : "Quotations"}
          listPrint={false}
          listPdf={false}
          columns={columns}
          data={docs}
          loading={loading}
          page={activeList.page}
          pageSize={activeList.pageSize}
          total={activeList.total}
          onPageChange={activeList.setPage}
          onPageSizeChange={activeList.setPageSize}
          searchPlaceholder="Search by number or customer..."
          searchValue={search}
          onSearchChange={setSearch}
          emptyMessage={tab === "invoices" ? "No invoices yet. Create your first invoice." : "No quotations yet. Create your first quotation."}
          actions={
            canCreate ? (
              <Button asChild size="sm">
                <Link to={newPath}><Plus className="h-4 w-4" /> Create</Link>
              </Button>
            ) : undefined
          }
        />
      </ContentSection>

      <SalesReceiptDialog
        preview={documentPreview}
        onClose={closePreview}
        onMarkPaid={canUpdate ? handleMarkPaidFromDialog : undefined}
        markingPaid={!!documentPreview && receiptLoadingId === documentPreview.invoiceId}
      />
    </PageLayout>
  );
}
