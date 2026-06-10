import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Pencil, Trash2, Package, TrendingUp, Info } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { CreatableSelect } from "@/components/forms/CreatableSelect";
import { ProductThumbnail, ProductImagePreview } from "@/components/catalog/ProductImage";
import { ProductImageUpload } from "@/components/catalog/ProductImageUpload";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { productsApi, inventoryApi } from "@/services/api/catalog";
import { settingsApi } from "@/services/api/admin";
import { formatCurrency } from "@/utils/cn";
import type { Product } from "@/types/models/catalog";

export function ProductsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [categories, setCategories] = useState<{ label: string; value: string }[]>([]);

  const {
    data: products,
    loading,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    reload,
  } = usePaginatedList(productsApi.list, { search, category: categoryFilter });

  useEffect(() => {
    productsApi.categories().then((res) => {
      setCategories(res.data.results.map((c) => ({ label: c.name, value: c.id })));
    });
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this product?")) return;
    await productsApi.delete(id);
    reload();
  };

  const columns: Column<Product>[] = [
    { key: "sku", header: "SKU", cell: (r) => <span className="font-mono text-xs">{r.sku}</span>, exportValue: (r) => r.sku },
    {
      key: "name",
      header: "Product",
      cell: (r) => (
        <div className="flex items-center gap-3 min-w-0">
          <ProductThumbnail product={r} size="md" />
          <div className="min-w-0">
            <p className="font-medium truncate">{r.name}</p>
            <p className="text-xs text-muted-foreground truncate">{r.category_name}</p>
          </div>
        </div>
      ),
      exportValue: (r) => r.name,
    },
    { key: "category", header: "Category", cell: (r) => r.category_name, className: "hidden lg:table-cell", exportValue: (r) => r.category_name },
    { key: "cost", header: "Cost", cell: (r) => formatCurrency(r.cost_price), exportValue: (r) => formatCurrency(r.cost_price) },
    { key: "price", header: "Price", cell: (r) => formatCurrency(r.selling_price), exportValue: (r) => formatCurrency(r.selling_price) },
    {
      key: "stock",
      header: "Stock",
      cell: (r) => (
        <Badge variant={(r.total_stock ?? 0) <= r.minimum_stock ? "warning" : "secondary"}>
          {r.total_stock ?? 0}
        </Badge>
      ),
      exportValue: (r) => String(r.total_stock ?? 0),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={r.is_active ? "success" : "secondary"}>
          {r.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
      exportValue: (r) => (r.is_active ? "Active" : "Inactive"),
    },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/products/${r.id}/edit`)}>
            <Pencil className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)}>
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="Products"
      description="Manage your product catalog, pricing, and stock levels."
      breadcrumbs={["Home", "Products"]}
      actions={
        <Button asChild>
          <Link to="/products/new">
            <Plus className="h-4 w-4" />
            Add Product
          </Link>
        </Button>
      }
    >
      <DataTable
        exportTitle="Products"
        columns={columns}
        data={products}
        loading={loading}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        searchPlaceholder="Search by name, SKU, or barcode..."
        searchValue={search}
        onSearchChange={setSearch}
        filters={
          categories.length
            ? [{
                key: "category",
                label: "Category",
                value: categoryFilter,
                onChange: setCategoryFilter,
                options: [{ label: "All Categories", value: "" }, ...categories],
              }]
            : undefined
        }
        emptyMessage="No products found. Add your first product to get started."
      />
    </PageLayout>
  );
}

export function ProductFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState<{ id: string; name: string }[]>([]);
  const [brands, setBrands] = useState<{ id: string; name: string }[]>([]);
  const [units, setUnits] = useState<{ id: string; name: string }[]>([]);
  const [warehouses, setWarehouses] = useState<{ id: string; name: string }[]>([]);
  const [defaultBranchId, setDefaultBranchId] = useState("");
  const [form, setForm] = useState({
    sku: "", barcode: "", name: "", category_id: "", brand_id: "",
    unit_id: "", cost_price: "", selling_price: "", minimum_stock: "5",
    description: "", image: "", is_active: true, initial_stock: "0", warehouse_id: "",
  });
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const [optionsLoading, setOptionsLoading] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      setOptionsLoading(true);
      setOptionsError(null);
      const errors: string[] = [];

      const load = async <T,>(label: string, fn: () => Promise<T>, onOk: (data: T) => void) => {
        try {
          const data = await fn();
          if (!cancelled) onOk(data);
        } catch {
          errors.push(label);
        }
      };

      await Promise.all([
        load("categories", () => productsApi.categories(), (res) => setCategories(res.data.results)),
        load("brands", () => productsApi.brands(), (res) => setBrands(res.data.results)),
        load("units", () => productsApi.units(), (res) => {
          setUnits(res.data);
          if (res.data.length) {
            setForm((f) => ({ ...f, unit_id: f.unit_id || res.data[0].id }));
          }
        }),
        load("warehouses", () => inventoryApi.warehouses(), (res) => {
          setWarehouses(res.data.results);
          if (res.data.results.length) {
            setForm((f) => ({ ...f, warehouse_id: f.warehouse_id || res.data.results[0].id }));
          }
        }),
        load("branches", () => settingsApi.branches(), (res) => {
          const defaultBranch = res.data.find((b) => b.is_default) || res.data[0];
          if (defaultBranch) setDefaultBranchId(defaultBranch.id);
        }),
      ]);

      if (!cancelled) {
        setOptionsLoading(false);
        if (errors.length) {
          setOptionsError(`Could not load: ${errors.join(", ")}. Check that the backend is running.`);
        }
      }
    }

    loadOptions();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!editId) return;
    productsApi.get(editId).then((res) => {
      const p = res.data;
      setForm({
        sku: p.sku, barcode: p.barcode, name: p.name,
        category_id: p.category_id, brand_id: p.brand_id || "",
        unit_id: p.unit_id, cost_price: String(p.cost_price),
        selling_price: String(p.selling_price), minimum_stock: String(p.minimum_stock),
        description: p.description, image: p.image || "", is_active: p.is_active,
        initial_stock: "0", warehouse_id: "",
      });
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        sku: form.sku,
        barcode: form.barcode || undefined,
        name: form.name,
        category_id: form.category_id,
        brand_id: form.brand_id || undefined,
        unit_id: form.unit_id,
        cost_price: parseFloat(form.cost_price),
        selling_price: parseFloat(form.selling_price),
        minimum_stock: parseInt(form.minimum_stock, 10),
        description: form.description,
        image: form.image || undefined,
        is_active: form.is_active,
        ...(!editId && {
          initial_stock: parseFloat(form.initial_stock) || 0,
          warehouse_id: form.warehouse_id || undefined,
        }),
      };
      if (editId) {
        await productsApi.update(editId, payload);
      } else {
        await productsApi.create(payload);
      }
      navigate("/products");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Products"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  const cost = parseFloat(form.cost_price) || 0;
  const price = parseFloat(form.selling_price) || 0;
  const margin = price > 0 ? ((price - cost) / price) * 100 : 0;

  return (
    <PageLayout
      title={editId ? "Edit Product" : "Add Product"}
      description={editId ? "Update product details and pricing." : "Create a new product in your catalog."}
      breadcrumbs={["Home", "Products", editId ? "Edit" : "New"]}
    >
      {optionsError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {optionsError}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <>
              <FormSection title="General Information" description="Basic product identity and classification.">
                <FormGrid>
                  <FormField label="Product Name" required>
                    <Input
                      required
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="e.g. Wireless Mouse"
                    />
                  </FormField>
                  <FormField label="SKU" required hint="Unique stock-keeping unit code">
                    <Input
                      required
                      value={form.sku}
                      onChange={(e) => setForm({ ...form, sku: e.target.value })}
                      placeholder="e.g. WM-001"
                      className="font-mono"
                    />
                  </FormField>
                  <FormField label="Barcode" hint="Optional EAN/UPC barcode">
                    <Input
                      value={form.barcode}
                      onChange={(e) => setForm({ ...form, barcode: e.target.value })}
                      placeholder="Scan or enter barcode"
                      className="font-mono"
                    />
                  </FormField>
                  <FormField label="Category" required>
                    <CreatableSelect
                      value={form.category_id}
                      onChange={(v) => setForm({ ...form, category_id: v })}
                      options={categories}
                      placeholder={optionsLoading ? "Loading categories..." : "Select category"}
                      disabled={optionsLoading}
                      createLabel="Create new category..."
                      onCreate={async (name) => {
                        const res = await productsApi.createCategory(name);
                        const item = { id: res.data.id, name: res.data.name };
                        setCategories((prev) => [...prev, item]);
                        return item;
                      }}
                    />
                  </FormField>
                  <FormField label="Brand">
                    <CreatableSelect
                      value={form.brand_id}
                      onChange={(v) => setForm({ ...form, brand_id: v })}
                      options={brands}
                      placeholder="None / select brand"
                      createLabel="Create new brand..."
                      allowNone
                      onCreate={async (name) => {
                        const res = await productsApi.createBrand(name);
                        const item = { id: res.data.id, name: res.data.name };
                        setBrands((prev) => [...prev, item]);
                        return item;
                      }}
                    />
                  </FormField>
                  <FormField label="Unit" required>
                    <CreatableSelect
                      value={form.unit_id}
                      onChange={(v) => setForm({ ...form, unit_id: v })}
                      options={units}
                      placeholder={optionsLoading ? "Loading units..." : "Select unit"}
                      disabled={optionsLoading}
                      createLabel="Create new unit..."
                      onCreate={async (name) => {
                        const res = await productsApi.createUnit(name);
                        const item = { id: res.data.id, name: res.data.name };
                        setUnits((prev) => [...prev, item]);
                        return item;
                      }}
                    />
                  </FormField>
                </FormGrid>
                <FormField label="Description" className="mt-6">
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    rows={3}
                    placeholder="Product description for internal use..."
                    className="flex w-full rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                  />
                </FormField>
              </FormSection>

              <FormSection title="Product Image" description="Upload a photo for catalog, POS, and receipts.">
                <ProductImageUpload
                  value={form.image}
                  previewUrl={imagePreview ?? undefined}
                  name={form.name}
                  sku={form.sku}
                  categoryName={categories.find((c) => c.id === form.category_id)?.name}
                  onChange={(url) => setForm((f) => ({ ...f, image: url }))}
                  onPreviewChange={setImagePreview}
                  onUpload={async (file) => {
                    const res = await productsApi.uploadImage(file);
                    return res.data.url;
                  }}
                />
              </FormSection>

              <FormSection title="Pricing & Inventory" description="Cost, selling price, and stock configuration.">
                <FormGrid>
                  <FormField label="Cost Price" required>
                    <Input
                      required
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.cost_price}
                      onChange={(e) => setForm({ ...form, cost_price: e.target.value })}
                      placeholder="0.00"
                    />
                  </FormField>
                  <FormField label="Selling Price" required>
                    <Input
                      required
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.selling_price}
                      onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
                      placeholder="0.00"
                    />
                  </FormField>
                  <FormField label="Minimum Stock" hint="Low-stock alert threshold">
                    <Input
                      type="number"
                      min="0"
                      value={form.minimum_stock}
                      onChange={(e) => setForm({ ...form, minimum_stock: e.target.value })}
                    />
                  </FormField>
                  {!editId && (
                    <>
                      <FormField label="Initial Stock">
                        <Input
                          type="number"
                          min="0"
                          value={form.initial_stock}
                          onChange={(e) => setForm({ ...form, initial_stock: e.target.value })}
                        />
                      </FormField>
                      <FormField label="Warehouse">
                        <CreatableSelect
                          value={form.warehouse_id}
                          onChange={(v) => setForm({ ...form, warehouse_id: v })}
                          options={warehouses}
                          placeholder={optionsLoading ? "Loading warehouses..." : "Select warehouse"}
                          disabled={optionsLoading}
                          createLabel="Create new warehouse..."
                          onCreate={async (name) => {
                            if (!defaultBranchId) throw new Error("No branch configured.");
                            const code = name.replace(/\s+/g, "").slice(0, 6).toUpperCase() || "WH";
                            const res = await inventoryApi.createWarehouse({
                              name,
                              code,
                              branch_id: defaultBranchId,
                              is_active: true,
                            });
                            const item = { id: res.data.id, name: res.data.name };
                            setWarehouses((prev) => [...prev, item]);
                            return item;
                          }}
                        />
                      </FormField>
                    </>
                  )}
                </FormGrid>
              </FormSection>
            </>
          }
          aside={
            <>
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Package className="h-4 w-4 text-primary" />
                    Product Preview
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ProductImagePreview
                    image={imagePreview || form.image}
                    name={form.name}
                    sku={form.sku}
                    categoryName={categories.find((c) => c.id === form.category_id)?.name}
                  />
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Name</p>
                    <p className="mt-1 font-semibold">{form.name || "—"}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">SKU</p>
                      <p className="mt-1 font-mono text-sm">{form.sku || "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Status</p>
                      <Badge variant={form.is_active ? "success" : "secondary"} className="mt-1">
                        {form.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Cost</span>
                      <span>{formatCurrency(cost)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Price</span>
                      <span className="font-semibold">{formatCurrency(price)}</span>
                    </div>
                    <div className="flex justify-between text-sm border-t border-border pt-2">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <TrendingUp className="h-3.5 w-3.5" /> Margin
                      </span>
                      <span className={margin >= 0 ? "text-primary font-semibold" : "text-destructive font-semibold"}>
                        {margin.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <Checkbox
                      checked={form.is_active}
                      onCheckedChange={(v) => setForm({ ...form, is_active: !!v })}
                    />
                    <div>
                      <p className="text-sm font-medium">Active product</p>
                      <p className="text-xs text-muted-foreground">Inactive products are hidden from POS and sales</p>
                    </div>
                  </label>
                </CardContent>
              </Card>

              <Card className="border-primary/20 bg-primary/5">
                <CardContent className="pt-6">
                  <div className="flex gap-3">
                    <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-foreground">Tip</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Set minimum stock levels to receive low-stock alerts on your dashboard and inventory pages.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          }
          actions={
            <FormActions>
              <Button type="submit" loading={saving}>
                {editId ? "Save Changes" : "Create Product"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/products")}>
                Cancel
              </Button>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}
