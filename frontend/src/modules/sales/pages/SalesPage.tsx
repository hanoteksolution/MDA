import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { Receipt, FileText, TrendingUp, DollarSign, Plus, Download, Pencil } from "lucide-react";
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

const INVOICE_STATUS: Record<string, "secondary" | "warning" | "success" | "destructive"> = {
  draft: "secondary", sent: "warning", paid: "success", overdue: "destructive", cancelled: "destructive",
};

export function SalesPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("invoices");
  const [search, setSearch] = useState("");
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  const invoiceList = usePaginatedList(salesApi.invoices, { search });
  const quotationList = usePaginatedList(salesApi.quotations, { search });
  const activeList = tab === "invoices" ? invoiceList : quotationList;
  const docs = activeList.data;
  const loading = activeList.loading;

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
      cell: (r) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(tab === "invoices" ? `/sales/invoices/${r.id}/edit` : `/sales/quotations/${r.id}/edit`)}
        >
          <Pencil className="h-4 w-4" />
        </Button>
      ),
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
          <Button asChild>
            <Link to={newPath}>
              <Plus className="h-4 w-4" />
              {tab === "invoices" ? "New Invoice" : "New Quotation"}
            </Link>
          </Button>
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
            <Button asChild size="sm">
              <Link to={newPath}><Plus className="h-4 w-4" /> Create</Link>
            </Button>
          }
        />
      </ContentSection>
    </PageLayout>
  );
}
