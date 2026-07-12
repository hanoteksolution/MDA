import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { usePermissions } from "@/hooks/usePermissions";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { Link } from "react-router-dom";
import {
  Package, AlertTriangle, XCircle, Warehouse, ArrowRightLeft, Plus, PackagePlus,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { QuickActions } from "@/components/data/QuickActions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { inventoryApi } from "@/services/api/catalog";
import { formatCurrency } from "@/utils/cn";
import { cn } from "@/utils/cn";
import type { InventoryItem, InventorySummary } from "@/types/models/catalog";
import { appDialog } from "@/components/feedback/AppDialog";

interface RestockTarget {
  product_id: string;
  product_name: string;
  product_sku: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  minimum_stock: number;
}

function RestockDialog({
  target,
  onClose,
  onDone,
}: {
  target: RestockTarget | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [mode, setMode] = useState<"add" | "set">("add");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!target) return;
    setMode("add");
    setAmount("");
    setError(null);
  }, [target]);

  if (!target) return null;

  const parsed = parseFloat(amount);
  const nextQty =
    mode === "add"
      ? target.quantity + (Number.isFinite(parsed) ? parsed : 0)
      : Number.isFinite(parsed)
        ? parsed
        : target.quantity;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!Number.isFinite(parsed) || parsed < 0) {
      setError("Enter a valid quantity.");
      return;
    }
    if (mode === "add" && parsed <= 0) {
      setError("Add a quantity greater than zero.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await inventoryApi.createAdjustment({
        warehouse_id: target.warehouse_id,
        reason: mode === "add" ? "Quick restock" : "Stock set via restock",
        items: [
          {
            product_id: target.product_id,
            quantity_after: mode === "add" ? target.quantity + parsed : parsed,
          },
        ],
      });
      onDone();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restock failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/40 p-4 sm:items-center"
      onClick={onClose}
      role="presentation"
    >
      <div
        className={cn(
          "w-full max-w-md overflow-hidden rounded-2xl border border-border/60 bg-card shadow-2xl",
          "animate-in fade-in slide-in-from-bottom-4 duration-200"
        )}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="restock-title"
      >
        <div className="border-b border-border/50 px-5 py-4">
          <h2 id="restock-title" className="text-lg font-semibold tracking-tight">
            Restock {target.product_name}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {target.product_sku} · {target.warehouse_name} · on hand {target.quantity}
            {target.minimum_stock > 0 ? ` · min ${target.minimum_stock}` : ""}
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant={mode === "add" ? "default" : "secondary"}
              onClick={() => setMode("add")}
            >
              Add stock
            </Button>
            <Button
              type="button"
              size="sm"
              variant={mode === "set" ? "default" : "secondary"}
              onClick={() => setMode("set")}
            >
              Set quantity
            </Button>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {mode === "add" ? "Quantity to add" : "New on-hand quantity"}
            </label>
            <Input
              autoFocus
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={mode === "add" ? "e.g. 50" : String(target.quantity)}
            />
            {Number.isFinite(parsed) && (
              <p className="text-xs text-muted-foreground">
                New on-hand: <span className="font-medium text-foreground">{nextQty}</span>
              </p>
            )}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              <PackagePlus className="h-4 w-4" />
              Confirm restock
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function toRestockTarget(item: InventoryItem): RestockTarget {
  return {
    product_id: item.product_id,
    product_name: item.product_name,
    product_sku: item.product_sku,
    warehouse_id: item.warehouse_id,
    warehouse_name: item.warehouse_name,
    quantity: item.quantity,
    minimum_stock: item.minimum_stock,
  };
}

export function InventoryDashboardPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [restockTarget, setRestockTarget] = useState<RestockTarget | null>(null);
  const { hasPermission } = usePermissions();
  const canAdjust = hasPermission("inventory.adjust");

  const load = (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    Promise.all([inventoryApi.summary(), inventoryApi.lowStock()])
      .then(([s, l]) => {
        setSummary(s.data);
        setLowStock(l.data.results.slice(0, 10));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(true);
  }, []);

  useAutoRefresh(() => load(false), { intervalMs: 30_000 });

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
    ...(canAdjust
      ? [
          {
            key: "actions",
            header: "",
            cell: (r: InventoryItem) => (
              <Button size="sm" variant="secondary" onClick={() => setRestockTarget(toRestockTarget(r))}>
                <PackagePlus className="h-3.5 w-3.5" />
                Restock
              </Button>
            ),
          } satisfies Column<InventoryItem>,
        ]
      : []),
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

      <ContentSection
        title="Stock Alerts"
        description="Products at or below minimum stock level (includes out of stock)."
        noPadding
      >
        <DataTable embedded columns={columns} data={lowStock} loading={loading} emptyMessage="No stock alerts." />
      </ContentSection>

      <RestockDialog target={restockTarget} onClose={() => setRestockTarget(null)} onDone={load} />
    </PageLayout>
  );
}

export function StockPage() {
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState("");
  const [restockTarget, setRestockTarget] = useState<RestockTarget | null>(null);
  const { hasPermission } = usePermissions();
  const canAdjust = hasPermission("inventory.adjust");

  const { data: items, loading, page, setPage, pageSize, setPageSize, total, reload } = usePaginatedList(
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
    ...(canAdjust
      ? [
          {
            key: "actions",
            header: "Actions",
            cell: (r: InventoryItem) => (
              <Button size="sm" variant="secondary" onClick={() => setRestockTarget(toRestockTarget(r))}>
                <PackagePlus className="h-3.5 w-3.5" />
                Restock
              </Button>
            ),
          } satisfies Column<InventoryItem>,
        ]
      : []),
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
            { label: "Low / Out of Stock", value: "true" },
          ],
        }]}
      />
      <RestockDialog
        target={restockTarget}
        onClose={() => setRestockTarget(null)}
        onDone={reload}
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
      await appDialog.alert(err instanceof Error ? err.message : "Failed");
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
