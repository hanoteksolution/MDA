import { useEffect, useMemo, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { usePermissions } from "@/hooks/usePermissions";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { useAuthStore } from "@/store/authStore";
import { Link } from "react-router-dom";
import {
  Package, AlertTriangle, XCircle, Warehouse, ArrowRightLeft, Plus, PackagePlus, PackageMinus,
} from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { KpiCard, KpiGrid } from "@/components/data/KpiCard";
import { ContentSection } from "@/components/layout/ContentSection";
import { DataTable, type Column } from "@/components/data/DataTable";
import { QuickActions } from "@/components/data/QuickActions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProductThumbnail } from "@/components/catalog/ProductImage";
import { CrossBranchAvailability } from "@/modules/inventory/components/CrossBranchAvailability";
import { SendStockDialog, type SendLine } from "@/modules/branches/components/SendStockDialog";
import { useBranchStore } from "@/store/branchStore";
import { inventoryApi } from "@/services/api/catalog";
import { useScopedPath } from "@/hooks/useScopedPath";
import { productModuleCode } from "@/utils/productModuleScope";
import { formatCurrency } from "@/utils/cn";
import { cn } from "@/utils/cn";
import type { InventoryItem, InventorySummary } from "@/types/models/catalog";
import { appDialog } from "@/components/feedback/AppDialog";

interface RestockTarget {
  product_id: string;
  product_name: string;
  product_sku: string;
  product_image?: string;
  warehouse_id: string;
  warehouse_name: string;
  quantity: number;
  minimum_stock: number;
  /** Prefer add-stock when opening from out-of-stock “Make in stock”. */
  preferMakeInStock?: boolean;
}

type StockMode = "add" | "remove" | "set";

function RestockDialog({
  target,
  onClose,
  onDone,
}: {
  target: RestockTarget | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [mode, setMode] = useState<StockMode>("add");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!target) return;
    setMode(target.preferMakeInStock || target.quantity <= 0 ? "add" : "add");
    setAmount(target.preferMakeInStock || target.quantity <= 0
      ? String(Math.max(target.minimum_stock || 10, 10))
      : "");
    setError(null);
  }, [target]);

  if (!target) return null;

  const parsed = parseFloat(amount);
  const safeParsed = Number.isFinite(parsed) ? parsed : 0;
  let nextQty = target.quantity;
  if (mode === "add") nextQty = target.quantity + safeParsed;
  else if (mode === "remove") nextQty = Math.max(0, target.quantity - safeParsed);
  else if (Number.isFinite(parsed)) nextQty = Math.max(0, parsed);

  const willBeOutOfStock = nextQty <= 0;
  const excessRemoved =
    mode === "remove" && Number.isFinite(parsed) && parsed > target.quantity
      ? parsed - target.quantity
      : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!Number.isFinite(parsed) || parsed < 0) {
      setError("Enter a valid quantity.");
      return;
    }
    if ((mode === "add" || mode === "remove") && parsed <= 0) {
      setError(mode === "add" ? "Add a quantity greater than zero." : "Remove a quantity greater than zero.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const quantity_after =
        mode === "add"
          ? target.quantity + parsed
          : mode === "remove"
            ? Math.max(0, target.quantity - parsed)
            : Math.max(0, parsed);
      const reason =
        mode === "add"
          ? target.quantity <= 0
            ? "Make in stock"
            : "Quick restock"
          : mode === "remove"
            ? quantity_after <= 0
              ? "Reduced to out of stock"
              : "Stock reduction"
            : "Stock set via restock";
      await inventoryApi.createAdjustment({
        warehouse_id: target.warehouse_id,
        reason,
        items: [{ product_id: target.product_id, quantity_after }],
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
          <div className="flex items-start gap-3">
            <ProductThumbnail
              product={{
                name: target.product_name,
                sku: target.product_sku,
                image: target.product_image || "",
                category_name: "",
              }}
              size="md"
            />
            <div>
              <h2 id="restock-title" className="text-lg font-semibold tracking-tight">
                {target.quantity <= 0 ? "Make in stock" : "Adjust stock"} · {target.product_name}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {target.product_sku} · {target.warehouse_name} · on hand{" "}
                <span className="font-medium text-foreground">{target.quantity}</span>
                {target.minimum_stock > 0 ? ` · min ${target.minimum_stock}` : ""}
              </p>
            </div>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant={mode === "add" ? "default" : "secondary"} onClick={() => setMode("add")}>
              Add stock
            </Button>
            <Button type="button" size="sm" variant={mode === "remove" ? "default" : "secondary"} onClick={() => setMode("remove")}>
              Reduce stock
            </Button>
            <Button type="button" size="sm" variant={mode === "set" ? "default" : "secondary"} onClick={() => setMode("set")}>
              Set quantity
            </Button>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">
              {mode === "add" ? "Quantity to add" : mode === "remove" ? "Quantity to remove" : "New on-hand quantity"}
            </label>
            <Input
              autoFocus
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={mode === "set" ? String(target.quantity) : "e.g. 50"}
            />
            {Number.isFinite(parsed) && (
              <p className="text-xs text-muted-foreground">
                New on-hand:{" "}
                <span className={cn("font-medium", willBeOutOfStock ? "text-destructive" : "text-foreground")}>
                  {nextQty}
                </span>
                {willBeOutOfStock ? " (out of stock)" : ""}
                {excessRemoved > 0
                  ? ` · only ${target.quantity} on hand; excess ${excessRemoved} already unavailable`
                  : ""}
              </p>
            )}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              {mode === "remove" ? <PackageMinus className="h-4 w-4" /> : <PackagePlus className="h-4 w-4" />}
              {target.quantity <= 0 && mode === "add" ? "Make in stock" : "Confirm"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function toRestockTarget(item: InventoryItem, opts?: { preferMakeInStock?: boolean }): RestockTarget {
  return {
    product_id: item.product_id,
    product_name: item.product_name,
    product_sku: item.product_sku,
    product_image: item.product_image,
    warehouse_id: item.warehouse_id,
    warehouse_name: item.warehouse_name,
    quantity: item.quantity,
    minimum_stock: item.minimum_stock,
    preferMakeInStock: opts?.preferMakeInStock || item.is_out_of_stock,
  };
}

function ProductCell({ item }: { item: InventoryItem }) {
  return (
    <div className="flex items-center gap-2.5">
      <ProductThumbnail
        product={{
          name: item.product_name,
          sku: item.product_sku,
          image: item.product_image || "",
          category_name: "",
        }}
        size="sm"
      />
      <span className="font-medium">{item.product_name}</span>
    </div>
  );
}

export function InventoryDashboardPage() {
  const { scoped, scope } = useScopedPath();
  const moduleCode = productModuleCode(scope);
  const moduleParams = useMemo(
    () => (moduleCode ? { module_code: moduleCode } : {}),
    [moduleCode]
  );
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [restockTarget, setRestockTarget] = useState<RestockTarget | null>(null);
  const { hasPermission } = usePermissions();
  const canAdjust = hasPermission("inventory.adjust");

  const load = (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    Promise.all([inventoryApi.summary(moduleParams), inventoryApi.lowStock(moduleParams)])
      .then(([s, l]) => {
        setSummary(s.data);
        setLowStock(l.data.results.slice(0, 10));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(true);
  }, [moduleCode]);

  useAutoRefresh(() => load(false), { intervalMs: 30_000 });

  const columns: Column<InventoryItem>[] = [
    { key: "product", header: "Product", cell: (r) => <ProductCell item={r} /> },
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
              <Button
                size="sm"
                variant={r.is_out_of_stock ? "default" : "secondary"}
                onClick={() => setRestockTarget(toRestockTarget(r, { preferMakeInStock: r.is_out_of_stock }))}
              >
                <PackagePlus className="h-3.5 w-3.5" />
                {r.is_out_of_stock ? "Make in stock" : "Restock"}
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
          <Link to={scoped("/inventory/adjustments")}>
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
            { label: "View Stock", description: "All inventory records", icon: <Package className="h-5 w-5" />, to: scoped("/inventory/stock") },
            { label: "Adjustments", description: "Correct stock levels", icon: <ArrowRightLeft className="h-5 w-5" />, to: scoped("/inventory/adjustments") },
            { label: "Warehouses", description: "Manage locations", icon: <Warehouse className="h-5 w-5" />, to: scoped("/inventory/warehouses") },
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
  const { scoped, scope } = useScopedPath();
  const moduleCode = productModuleCode(scope);
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState("");
  const [restockTarget, setRestockTarget] = useState<RestockTarget | null>(null);
  const [sendLine, setSendLine] = useState<SendLine | null>(null);
  const { hasPermission } = usePermissions();
  const canAdjust = hasPermission("inventory.adjust");
  // "Send to branch" needs transfer rights in the acting branch (the API re-checks).
  const canSendStock = useBranchStore((s) => Boolean(s.activeBranchId && s.activeBranchId !== "all" && s.canInBranch("inventory.transfer")));

  const { data: items, loading, page, setPage, pageSize, setPageSize, total, reload } = usePaginatedList(
    inventoryApi.list,
    {
      search,
      low_stock: lowOnly === "true" ? "true" : undefined,
      ...(moduleCode ? { module_code: moduleCode } : {}),
    }
  );

  const columns: Column<InventoryItem>[] = [
    { key: "product", header: "Product", cell: (r) => <ProductCell item={r} />, exportValue: (r) => r.product_name },
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
    {
      key: "elsewhere",
      header: "Elsewhere",
      cell: (r) => (
        <div className="flex flex-wrap items-start gap-1">
          {(r.is_out_of_stock || r.is_low_stock) && <CrossBranchAvailability productId={r.product_id} />}
          {canSendStock && Number(r.available_quantity) > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setSendLine({ productId: r.product_id, productName: r.product_name,
              available: Number(r.available_quantity), quantity: "1" })}>
              Send to branch
            </Button>
          )}
        </div>
      ),
      exportValue: () => "",
    },
    ...(canAdjust
      ? [
          {
            key: "actions",
            header: "Actions",
            cell: (r: InventoryItem) => (
              <Button
                size="sm"
                variant={r.is_out_of_stock ? "default" : "secondary"}
                onClick={() => setRestockTarget(toRestockTarget(r, { preferMakeInStock: r.is_out_of_stock }))}
              >
                <PackagePlus className="h-3.5 w-3.5" />
                {r.is_out_of_stock ? "Make in stock" : "Restock"}
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
      backTo={scoped("/inventory")}
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
      <SendStockDialog open={Boolean(sendLine)} initial={sendLine} onClose={() => setSendLine(null)} onCreated={() => reload()} />
    </PageLayout>
  );
}

export function AdjustmentsPage() {
  const { scope } = useScopedPath();
  const moduleCode = productModuleCode(scope);
  const [adjustments, setAdjustments] = useState<Awaited<ReturnType<typeof inventoryApi.adjustments>>["data"]["results"]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [warehouses, setWarehouses] = useState<{ id: string; name: string }[]>([]);
  const [products, setProducts] = useState<
    { id: string; name: string; sku: string; image?: string; total_stock?: number }[]
  >([]);
  const [stockByProduct, setStockByProduct] = useState<Record<string, InventoryItem>>({});
  const [form, setForm] = useState({
    warehouse_id: "",
    reason: "",
    product_id: "",
    mode: "set" as StockMode,
    amount: "",
  });
  const [saving, setSaving] = useState(false);

  const load = () => {
    inventoryApi.adjustments().then((res) => setAdjustments(res.data.results)).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    inventoryApi.warehouses().then((r) => setWarehouses(r.data.results));
  }, []);

  useEffect(() => {
    import("@/services/api/catalog").then(({ productsApi }) =>
      productsApi
        .list({
          page_size: 100,
          ...(moduleCode ? { module_code: moduleCode } : {}),
        })
        .then((r) => setProducts(r.data.results))
    );
    inventoryApi
      .list({
        page_size: 200,
        ...(moduleCode ? { module_code: moduleCode } : {}),
      })
      .then((r) => {
        const map: Record<string, InventoryItem> = {};
        for (const row of r.data.results) {
          const key = `${row.warehouse_id}:${row.product_id}`;
          map[key] = row;
          // Also index by product for first-match when warehouse not yet chosen
          if (!map[row.product_id] || row.quantity > (map[row.product_id]?.quantity ?? 0)) {
            map[row.product_id] = row;
          }
        }
        setStockByProduct(map);
      })
      .catch(() => undefined);
  }, [moduleCode]);

  const currentInv =
    form.warehouse_id && form.product_id
      ? stockByProduct[`${form.warehouse_id}:${form.product_id}`] || stockByProduct[form.product_id]
      : form.product_id
        ? stockByProduct[form.product_id]
        : undefined;
  const onHand = currentInv?.quantity ?? 0;
  const parsed = parseFloat(form.amount);
  const safeParsed = Number.isFinite(parsed) ? parsed : 0;
  let nextQty = onHand;
  if (form.mode === "add") nextQty = onHand + safeParsed;
  else if (form.mode === "remove") nextQty = Math.max(0, onHand - safeParsed);
  else if (Number.isFinite(parsed)) nextQty = Math.max(0, parsed);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!Number.isFinite(parsed) || parsed < 0) {
      await appDialog.alert("Enter a valid quantity.");
      return;
    }
    if ((form.mode === "add" || form.mode === "remove") && parsed <= 0) {
      await appDialog.alert("Enter a quantity greater than zero.");
      return;
    }
    setSaving(true);
    try {
      const quantity_after =
        form.mode === "add"
          ? onHand + parsed
          : form.mode === "remove"
            ? Math.max(0, onHand - parsed)
            : Math.max(0, parsed);
      const reason =
        form.reason.trim() ||
        (form.mode === "add"
          ? onHand <= 0
            ? "Make in stock"
            : "Stock increase"
          : form.mode === "remove"
            ? quantity_after <= 0
              ? "Reduced to out of stock"
              : "Stock reduction"
            : "Physical count correction");
      await inventoryApi.createAdjustment({
        warehouse_id: form.warehouse_id,
        reason,
        items: [{ product_id: form.product_id, quantity_after }],
      });
      setShowForm(false);
      setForm({ warehouse_id: "", reason: "", product_id: "", mode: "set", amount: "" });
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

  const selectedProduct = products.find((p) => p.id === form.product_id);

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
              <select
                required
                value={form.product_id}
                onChange={(e) => {
                  const pid = e.target.value;
                  const inv =
                    (form.warehouse_id && stockByProduct[`${form.warehouse_id}:${pid}`]) ||
                    stockByProduct[pid];
                  setForm({
                    ...form,
                    product_id: pid,
                    mode: inv && inv.quantity <= 0 ? "add" : form.mode,
                    amount: inv && inv.quantity <= 0 ? String(Math.max(inv.minimum_stock || 10, 10)) : form.amount,
                  });
                }}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm"
              >
                <option value="">Select product</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.sku})
                  </option>
                ))}
              </select>
              {selectedProduct && (
                <div className="flex items-center gap-2 pt-1">
                  <ProductThumbnail
                    product={{
                      name: selectedProduct.name,
                      sku: selectedProduct.sku,
                      image: selectedProduct.image || "",
                      category_name: "",
                    }}
                    size="sm"
                  />
                  <span className="text-xs text-muted-foreground">
                    On hand: <span className="font-medium text-foreground">{onHand}</span>
                    {onHand <= 0 ? " · Out of stock" : ""}
                  </span>
                </div>
              )}
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium">Adjustment type</label>
              <div className="flex flex-wrap gap-2">
                <Button type="button" size="sm" variant={form.mode === "add" ? "default" : "secondary"} onClick={() => setForm({ ...form, mode: "add" })}>
                  Add stock
                </Button>
                <Button type="button" size="sm" variant={form.mode === "remove" ? "default" : "secondary"} onClick={() => setForm({ ...form, mode: "remove" })}>
                  Reduce stock
                </Button>
                <Button type="button" size="sm" variant={form.mode === "set" ? "default" : "secondary"} onClick={() => setForm({ ...form, mode: "set" })}>
                  Set quantity
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {form.mode === "add" ? "Quantity to add" : form.mode === "remove" ? "Quantity to remove" : "New quantity"}
              </label>
              <input
                required
                type="number"
                step="0.01"
                min={0}
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm"
              />
              {Number.isFinite(parsed) && (
                <p className="text-xs text-muted-foreground">
                  New on-hand:{" "}
                  <span className={cn("font-medium", nextQty <= 0 ? "text-destructive" : "text-foreground")}>
                    {nextQty}
                  </span>
                  {nextQty <= 0 ? " (out of stock)" : ""}
                  {form.mode === "remove" && parsed > onHand
                    ? ` · only ${onHand} available; remainder already out of stock`
                    : ""}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Reason</label>
              <input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                className="flex h-10 w-full rounded-xl border border-input px-3 text-sm" placeholder="e.g. Physical count correction" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" loading={saving}>
              {onHand <= 0 && form.mode === "add" ? "Make in stock" : "Confirm Adjustment"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </form>
      )}
      <DataTable exportTitle="Inventory Adjustments" columns={columns} data={adjustments} loading={loading} emptyMessage="No adjustments yet." />
    </PageLayout>
  );
}

export function WarehousesPage() {
  const { hasPermission } = usePermissions();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const canCreate = hasPermission("inventory.adjust");
  const [warehouses, setWarehouses] = useState<Awaited<ReturnType<typeof inventoryApi.warehouses>>["data"]["results"]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ code: "", name: "", address: "" });

  const reload = () => {
    setLoading(true);
    inventoryApi.warehouses().then((r) => setWarehouses(r.data.results)).finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
  }, []);

  const createWarehouse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.code.trim() || !form.name.trim()) {
      setError("Code and name are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await inventoryApi.createWarehouse({
        code: form.code.trim(),
        name: form.name.trim(),
        address: form.address.trim(),
        branch_id: branchId,
        is_active: true,
      });
      setForm({ code: "", name: "", address: "" });
      setShowForm(false);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create warehouse.");
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<(typeof warehouses)[0]>[] = [
    { key: "code", header: "Code", cell: (r) => <span className="font-mono text-xs">{r.code}</span> },
    { key: "name", header: "Name", cell: (r) => <span className="font-medium">{r.name}</span> },
    { key: "branch", header: "Branch", cell: (r) => r.branch_name },
    { key: "default", header: "Default", cell: (r) => r.is_default ? <Badge>Default</Badge> : null },
    { key: "status", header: "Status", cell: (r) => <Badge variant={r.is_active ? "success" : "secondary"}>{r.is_active ? "Active" : "Inactive"}</Badge> },
  ];

  return (
    <PageLayout
      title="Warehouses"
      description="Manage storage locations and branches."
      breadcrumbs={["Home", "Inventory", "Warehouses"]}
      actions={
        canCreate ? (
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4 mr-1.5" />
            {showForm ? "Cancel" : "New warehouse"}
          </Button>
        ) : undefined
      }
    >
      {showForm && canCreate ? (
        <form onSubmit={createWarehouse} className="mb-4 rounded-xl border border-border/70 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Code</label>
              <Input value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))} placeholder="MAIN" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Main warehouse" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Address</label>
              <Input value={form.address} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} />
            </div>
          </div>
          {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
          <Button type="submit" size="sm" className="mt-3" disabled={saving}>
            {saving ? "Saving…" : "Create warehouse"}
          </Button>
        </form>
      ) : null}
      <DataTable
        exportTitle="Warehouses"
        columns={columns}
        data={warehouses}
        loading={loading}
        emptyMessage="No warehouses configured. Create one to hold stock."
      />
    </PageLayout>
  );
}
