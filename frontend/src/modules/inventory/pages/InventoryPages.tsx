import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link } from "react-router-dom";
import {
  Package, AlertTriangle, XCircle, Warehouse, ArrowRightLeft, Plus,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { QuickActions } from "@/components/data/QuickActions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { inventoryApi } from "@/services/api/catalog";
import { formatCurrency } from "@/utils/cn";
import type { InventoryItem, InventorySummary } from "@/types/models/catalog";

export function InventoryDashboardPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([inventoryApi.summary(), inventoryApi.lowStock()])
      .then(([s, l]) => {
        setSummary(s.data);
        setLowStock(l.data.results.slice(0, 10));
      })
      .finally(() => setLoading(false));
  }, []);

  const columns: Column<InventoryItem>[] = [
    { key: "product", header: "Product", cell: (r) => <span className="font-medium">{r.product_name}</span> },
    { key: "sku", header: "SKU", cell: (r) => <span className="font-mono text-xs text-muted-foreground">{r.product_sku}</span> },
    { key: "warehouse", header: "Warehouse", cell: (r) => r.warehouse_name },
    {
      key: "qty",
      header: "Stock",
      cell: (r) => (
        <Badge variant={r.is_out_of_stock ? "destructive" : "warning"}>
          {r.quantity} / min {r.minimum_stock}
        </Badge>
      ),
    },
  ];

  return (
    <PageLayout
      title="Inventory"
      description="Monitor stock levels, warehouses, and inventory movements."
      breadcrumbs={["Home", "Inventory"]}
      actions={
        <Button asChild>
          <Link to="/inventory/adjustments">
            <Plus className="h-4 w-4" />
            Stock Adjustment
          </Link>
        </Button>
      }
    >
      <KpiGrid columns={5}>
        <KpiCard title="Total SKUs" value={String(summary?.total_items ?? 0)} icon={<Package className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Total Units" value={String(summary?.total_quantity ?? 0)} icon={<Warehouse className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Inventory Value" value={formatCurrency(summary?.inventory_value ?? 0)} icon={<Package className="h-5 w-5" />} loading={loading} />
        <KpiCard title="Low Stock" value={String(summary?.low_stock_count ?? 0)} icon={<AlertTriangle className="h-5 w-5" />} trendUp={false} loading={loading} />
        <KpiCard title="Out of Stock" value={String(summary?.out_of_stock_count ?? 0)} icon={<XCircle className="h-5 w-5" />} trendUp={false} loading={loading} />
      </KpiGrid>

      <ContentSection title="Quick Actions">
        <QuickActions
          actions={[
            { label: "View Stock", description: "All inventory records", icon: <Package className="h-5 w-5" />, to: "/inventory/stock" },
            { label: "Adjustments", description: "Correct stock levels", icon: <ArrowRightLeft className="h-5 w-5" />, to: "/inventory/adjustments" },
            { label: "Warehouses", description: "Manage locations", icon: <Warehouse className="h-5 w-5" />, to: "/inventory/warehouses" },
          ]}
        />
      </ContentSection>

      <ContentSection title="Low Stock Alerts" description="Products at or below minimum stock level" noPadding>
        <DataTable embedded columns={columns} data={lowStock} loading={loading} emptyMessage="No low stock alerts." />
      </ContentSection>
    </PageLayout>
  );
}

export function StockPage() {
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState("");

  const { data: items, loading, page, setPage, pageSize, setPageSize, total } = usePaginatedList(
    inventoryApi.list,
    { search, low_stock: lowOnly === "true" ? "true" : undefined }
  );

  const columns: Column<InventoryItem>[] = [
    { key: "product", header: "Product", cell: (r) => <span className="font-medium">{r.product_name}</span>, exportValue: (r) => r.product_name },
    { key: "sku", header: "SKU", cell: (r) => r.product_sku, exportValue: (r) => r.product_sku },
    { key: "warehouse", header: "Warehouse", cell: (r) => r.warehouse_name, exportValue: (r) => r.warehouse_name },
    { key: "available", header: "Available", cell: (r) => r.available_quantity, exportValue: (r) => String(r.available_quantity) },
    { key: "reserved", header: "Reserved", cell: (r) => r.reserved_quantity, exportValue: (r) => String(r.reserved_quantity) },
    { key: "damaged", header: "Damaged", cell: (r) => r.damaged_quantity, exportValue: (r) => String(r.damaged_quantity) },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.is_out_of_stock ? "destructive" : r.is_low_stock ? "warning" : "success"}>
          {r.is_out_of_stock ? "Out of Stock" : r.is_low_stock ? "Low Stock" : "OK"}
        </Badge>
      ),
      exportValue: (r) => (r.is_out_of_stock ? "Out of Stock" : r.is_low_stock ? "Low Stock" : "OK"),
    },
  ];

  return (
    <PageLayout
      title="Stock Levels"
      description="Current inventory across all warehouses."
      breadcrumbs={["Home", "Inventory", "Stock"]}
      backTo="/inventory"
      backLabel="Inventory"
    >
      <DataTable
        exportTitle="Stock Levels"
        columns={columns}
        data={items}
        loading={loading}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        searchPlaceholder="Search products..."
        searchValue={search}
        onSearchChange={setSearch}
        filters={[{
          key: "low", label: "Filter", value: lowOnly, onChange: setLowOnly,
          options: [
            { label: "All Stock", value: "" },
            { label: "Low Stock Only", value: "true" },
          ],
        }]}
      />
    </PageLayout>
  );
}

export function AdjustmentsPage() {
  const [adjustments, setAdjustments] = useState<Awaited<ReturnType<typeof inventoryApi.adjustments>>["data"]["results"]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [warehouses, setWarehouses] = useState<{ id: string; name: string }[]>([]);
  const [products, setProducts] = useState<{ id: string; name: string; sku: string }[]>([]);
  const [form, setForm] = useState({ warehouse_id: "", reason: "", product_id: "", quantity_after: "" });
  const [saving, setSaving] = useState(false);

  const load = () => {
    inventoryApi.adjustments().then((res) => setAdjustments(res.data.results)).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    inventoryApi.warehouses().then((r) => setWarehouses(r.data.results));
    import("@/services/api/catalog").then(({ productsApi }) =>
      productsApi.list({ page_size: 100 }).then((r) => setProducts(r.data.results))
    );
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await inventoryApi.createAdjustment({
        warehouse_id: form.warehouse_id,
        reason: form.reason,
        items: [{ product_id: form.product_id, quantity_after: parseFloat(form.quantity_after) }],
      });
      setShowForm(false);
      setForm({ warehouse_id: "", reason: "", product_id: "", quantity_after: "" });
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<(typeof adjustments)[0]>[] = [
    { key: "num", header: "Reference", cell: (r) => <span className="font-mono text-xs text-primary">{r.adjustment_number}</span> },
    { key: "warehouse", header: "Warehouse", cell: (r) => r.warehouse_name },
    { key: "items", header: "Items", cell: (r) => r.items_count },
    { key: "status", header: "Status", cell: (r) => <Badge variant="success">{r.status}</Badge> },
    { key: "date", header: "Date", cell: (r) => new Date(r.created_at).toLocaleDateString() },
  ];

  return (
    <PageLayout
      title="Stock Adjustments"
      description="Correct inventory quantities with full audit trail."
      breadcrumbs={["Home", "Inventory", "Adjustments"]}
      actions={<Button onClick={() => setShowForm(!showForm)}><Plus className="h-4 w-4" />New Adjustment</Button>}
    >
      {showForm && (
        <form onSubmit={handleSubmit} className="ds-card p-6 space-y-4 mb-6">
          <h3 className="font-semibold">New Adjustment</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Warehouse</label>
              <select required value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm">
                <option value="">Select warehouse</option>
                {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Product</label>
              <select required value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm">
                <option value="">Select product</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">New Quantity</label>
              <input required type="number" step="0.01" value={form.quantity_after}
                onChange={(e) => setForm({ ...form, quantity_after: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Reason</label>
              <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm" placeholder="e.g. Physical count correction" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" loading={saving}>Confirm Adjustment</Button>
            <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </form>
      )}
      <DataTable exportTitle="Inventory Adjustments" columns={columns} data={adjustments} loading={loading} emptyMessage="No adjustments yet." />
    </PageLayout>
  );
}

export function WarehousesPage() {
  const [warehouses, setWarehouses] = useState<Awaited<ReturnType<typeof inventoryApi.warehouses>>["data"]["results"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    inventoryApi.warehouses().then((r) => setWarehouses(r.data.results)).finally(() => setLoading(false));
  }, []);

  const columns: Column<(typeof warehouses)[0]>[] = [
    { key: "code", header: "Code", cell: (r) => <span className="font-mono text-xs">{r.code}</span> },
    { key: "name", header: "Name", cell: (r) => <span className="font-medium">{r.name}</span> },
    { key: "branch", header: "Branch", cell: (r) => r.branch_name },
    { key: "default", header: "Default", cell: (r) => r.is_default ? <Badge>Default</Badge> : null },
    { key: "status", header: "Status", cell: (r) => <Badge variant={r.is_active ? "success" : "secondary"}>{r.is_active ? "Active" : "Inactive"}</Badge> },
  ];

  return (
    <PageLayout title="Warehouses" description="Manage storage locations and branches." breadcrumbs={["Home", "Inventory", "Warehouses"]}>
      <DataTable exportTitle="Warehouses" columns={columns} data={warehouses} loading={loading} emptyMessage="No warehouses configured." />
    </PageLayout>
  );
}
