import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { ClipboardList, Truck, Clock, DollarSign, Plus, Pencil, Trash2, Printer, Download, Loader2, FileOutput } from "lucide-react";
import { usePurchaseOrderPrint } from "../hooks/usePurchaseOrderPrint";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { QuickActions } from "@/components/data/QuickActions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { purchasesApi, suppliersApi } from "@/services/api/partners";
import { productsApi } from "@/services/api/catalog";
import { settingsApi } from "@/services/api/admin";
import { formatCurrency } from "@/utils/cn";
import type { PurchaseOrder, PurchaseSummary } from "@/types/models/partners";
import type { Product } from "@/types/models/catalog";

const STATUS_VARIANT: Record<string, "secondary" | "warning" | "success" | "destructive"> = {
  draft: "secondary",
  ordered: "warning",
  received: "success",
  cancelled: "destructive",
};

export function PurchasesPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<PurchaseSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: orders, loading, page, setPage, pageSize, setPageSize, total } = usePaginatedList(
    purchasesApi.list,
    { search, status: statusFilter }
  );
  const { loadingId, printPurchaseOrder, downloadPurchaseOrder } = usePurchaseOrderPrint();

  useEffect(() => {
    purchasesApi.summary()
      .then((sum) => setSummary(sum.data))
      .catch(() => setSummary(null))
      .finally(() => setSummaryLoading(false));
  }, []);

  const columns: Column<PurchaseOrder>[] = [
    { key: "po", header: "PO #", cell: (r) => <span className="font-mono text-xs font-medium">{r.order_number}</span>, exportValue: (r) => r.order_number },
    { key: "supplier", header: "Supplier", cell: (r) => r.supplier_name, exportValue: (r) => r.supplier_name },
    { key: "date", header: "Date", cell: (r) => r.order_date, exportValue: (r) => r.order_date },
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant={STATUS_VARIANT[r.status]} className="capitalize">{r.status}</Badge>,
      exportValue: (r) => r.status,
    },
    { key: "items", header: "Items", cell: (r) => r.item_count, exportValue: (r) => String(r.item_count) },
    { key: "total", header: "Total", cell: (r) => formatCurrency(r.total_amount), exportValue: (r) => formatCurrency(r.total_amount) },
    {
      key: "actions",
      header: "",
      exportable: false,
      cell: (r) => {
        const busy = loadingId === r.id;
        return (
          <div className="flex items-center justify-end gap-0.5">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1 px-2 text-primary"
              title="Print Purchase Order (A4)"
              disabled={busy}
              onClick={() => void printPurchaseOrder(r.id)}
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
              <span className="hidden text-xs font-semibold lg:inline">PO</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              title="Print Purchase Order"
              disabled={busy}
              onClick={() => void printPurchaseOrder(r.id)}
            >
              <Printer className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              title="Download Purchase Order PDF"
              disabled={busy}
              onClick={() => void downloadPurchaseOrder(r.id, r.order_number)}
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => navigate(`/purchases/${r.id}/edit`)}>
              <Pencil className="h-4 w-4" />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <PageLayout
      title="Purchases"
      description="Supplier orders, goods receiving, and purchase management."
      breadcrumbs={["Home", "Purchases"]}
      actions={
        <Button asChild>
          <Link to="/purchases/new"><Plus className="h-4 w-4" /> New Purchase Order</Link>
        </Button>
      }
    >
      <KpiGrid>
        <KpiCard title="Open Orders" value={String(summary?.open_orders ?? 0)} icon={<ClipboardList className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Pending Receipt" value={String(summary?.pending_receipt ?? 0)} icon={<Clock className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Received Total" value={formatCurrency(summary?.month_total ?? 0)} icon={<DollarSign className="h-5 w-5" />} loading={summaryLoading} />
        <KpiCard title="Total POs" value={String(summary?.total_orders ?? 0)} icon={<Truck className="h-5 w-5" />} loading={summaryLoading} />
      </KpiGrid>

      <ContentSection title="Quick Actions">
        <QuickActions
          actions={[
            { label: "New PO", description: "Create purchase order", icon: <Plus className="h-5 w-5" />, to: "/purchases/new", variant: "primary" },
            { label: "Suppliers", description: "Manage vendor list", icon: <Truck className="h-5 w-5" />, to: "/suppliers" },
          ]}
        />
      </ContentSection>

      <ContentSection title="Purchase Orders" noPadding>
        <DataTable
          embedded
          listPrint={false}
          listPdf={false}
          exportTitle="Purchase Orders"
          columns={columns}
          data={orders}
          loading={loading}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          searchPlaceholder="Search PO number or supplier..."
          searchValue={search}
          onSearchChange={setSearch}
          filters={[{
            key: "status", label: "Status", value: statusFilter, onChange: setStatusFilter,
            options: [
              { label: "All Statuses", value: "" },
              { label: "Draft", value: "draft" },
              { label: "Ordered", value: "ordered" },
              { label: "Received", value: "received" },
              { label: "Cancelled", value: "cancelled" },
            ],
          }]}
          emptyMessage="No purchase orders yet. Create your first PO to get started."
        />
      </ContentSection>
    </PageLayout>
  );
}

interface LineItem {
  product_id: string;
  quantity_ordered: string;
  unit_cost: string;
}

export function PurchaseFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [suppliers, setSuppliers] = useState<{ id: string; company_name: string }[]>([]);
  const [branches, setBranches] = useState<{ id: string; name: string }[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState({
    supplier_id: "", branch_id: "", status: "draft",
    expected_date: "", notes: "",
  });
  const [items, setItems] = useState<LineItem[]>([{ product_id: "", quantity_ordered: "1", unit_cost: "0" }]);

  useEffect(() => {
    Promise.all([
      suppliersApi.list({ page_size: 100 }),
      settingsApi.branches(),
      productsApi.list({ page_size: 100 }),
    ]).then(([sup, br, prod]) => {
      setSuppliers(sup.data.results);
      setBranches(br.data);
      setProducts(prod.data.results);
      if (sup.data.results.length) setForm((f) => ({ ...f, supplier_id: f.supplier_id || sup.data.results[0].id }));
      if (br.data.length) setForm((f) => ({ ...f, branch_id: f.branch_id || br.data[0].id }));
    });
  }, []);

  useEffect(() => {
    if (!editId) return;
    purchasesApi.get(editId).then((res) => {
      const po = res.data;
      setForm({
        supplier_id: po.supplier_id, branch_id: po.branch_id,
        status: po.status, expected_date: po.expected_date || "", notes: po.notes,
      });
      if (po.items?.length) {
        setItems(po.items.map((i) => ({
          product_id: i.product_id,
          quantity_ordered: String(i.quantity_ordered),
          unit_cost: String(i.unit_cost),
        })));
      }
      setLoading(false);
    });
  }, [editId]);

  const addLine = () => setItems([...items, { product_id: "", quantity_ordered: "1", unit_cost: "0" }]);
  const removeLine = (idx: number) => setItems(items.filter((_, i) => i !== idx));
  const updateLine = (idx: number, patch: Partial<LineItem>) => {
    setItems(items.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  };

  const onProductSelect = (idx: number, productId: string) => {
    const product = products.find((p) => p.id === productId);
    updateLine(idx, {
      product_id: productId,
      unit_cost: product ? String(product.cost_price) : "0",
    });
  };

  const lineTotal = items.reduce((s, i) => s + (parseFloat(i.quantity_ordered) || 0) * (parseFloat(i.unit_cost) || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        expected_date: form.expected_date || undefined,
        items: items.filter((i) => i.product_id).map((i) => ({
          product_id: i.product_id,
          quantity_ordered: parseFloat(i.quantity_ordered),
          unit_cost: parseFloat(i.unit_cost),
        })),
      };
      if (editId) await purchasesApi.update(editId, payload);
      else await purchasesApi.create(payload);
      navigate("/purchases");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Purchases"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit Purchase Order" : "New Purchase Order"}
      description="Create a supplier purchase order with line items."
      breadcrumbs={["Home", "Purchases", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <>
              <FormSection title="Order Details">
                <FormGrid>
                  <FormField label="Supplier" required>
                    <Select value={form.supplier_id} onValueChange={(v) => setForm({ ...form, supplier_id: v })}>
                      <SelectTrigger><SelectValue placeholder="Select supplier" /></SelectTrigger>
                      <SelectContent>
                        {suppliers.map((s) => <SelectItem key={s.id} value={s.id}>{s.company_name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Branch" required>
                    <Select value={form.branch_id} onValueChange={(v) => setForm({ ...form, branch_id: v })}>
                      <SelectTrigger><SelectValue placeholder="Select branch" /></SelectTrigger>
                      <SelectContent>
                        {branches.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Status">
                    <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="ordered">Ordered</SelectItem>
                        <SelectItem value="received">Received</SelectItem>
                        <SelectItem value="cancelled">Cancelled</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormField>
                  <FormField label="Expected Date">
                    <Input type="date" value={form.expected_date} onChange={(e) => setForm({ ...form, expected_date: e.target.value })} />
                  </FormField>
                  <FormField label="Notes" className="md:col-span-2">
                    <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional notes..." />
                  </FormField>
                </FormGrid>
              </FormSection>

              <FormSection title="Line Items" description="Add products to this purchase order">
                <div className="space-y-3">
                  {items.map((item, idx) => (
                    <div key={idx} className="grid grid-cols-1 gap-3 rounded-xl border border-border p-4 md:grid-cols-12 md:items-end">
                      <FormField label="Product" className="md:col-span-5">
                        <Select value={item.product_id} onValueChange={(v) => onProductSelect(idx, v)}>
                          <SelectTrigger><SelectValue placeholder="Select product" /></SelectTrigger>
                          <SelectContent>
                            {products.map((p) => (
                              <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku})</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormField>
                      <FormField label="Qty" className="md:col-span-2">
                        <Input type="number" min="0.01" step="0.01" value={item.quantity_ordered}
                          onChange={(e) => updateLine(idx, { quantity_ordered: e.target.value })} />
                      </FormField>
                      <FormField label="Unit Cost" className="md:col-span-2">
                        <Input type="number" min="0" step="0.01" value={item.unit_cost}
                          onChange={(e) => updateLine(idx, { unit_cost: e.target.value })} />
                      </FormField>
                      <div className="md:col-span-2 text-sm font-semibold pb-2">
                        {formatCurrency((parseFloat(item.quantity_ordered) || 0) * (parseFloat(item.unit_cost) || 0))}
                      </div>
                      <div className="md:col-span-1 flex justify-end pb-1">
                        {items.length > 1 && (
                          <Button type="button" variant="ghost" size="sm" onClick={() => removeLine(idx)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  <Button type="button" variant="secondary" size="sm" onClick={addLine}>
                    <Plus className="h-4 w-4" /> Add Line
                  </Button>
                </div>
              </FormSection>
            </>
          }
          aside={
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Order Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Line items</span>
                  <span>{items.filter((i) => i.product_id).length}</span>
                </div>
                <div className="flex justify-between text-lg font-bold border-t border-border pt-3">
                  <span>Total</span>
                  <span className="text-primary">{formatCurrency(lineTotal)}</span>
                </div>
              </CardContent>
            </Card>
          }
          actions={
            <FormActions>
              <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create Purchase Order"}</Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/purchases")}>Cancel</Button>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}
