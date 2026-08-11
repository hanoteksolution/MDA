import { useEffect, useState } from "react";
import { usePaginatedList } from "@/hooks/usePaginatedList";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Pencil, Trash2, Package, FileOutput, Download, Loader2, Tag, ImageIcon, Boxes, Sparkles } from "lucide-react";
import { useProductListPrint } from "../hooks/useProductListPrint";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { FormField, FormGrid, FormPanel, FormPanelSection } from "@/components/forms/FormField";
import { FormPageLayout, FormActions } from "@/components/forms/FormPageLayout";
import { CreatableSelect } from "@/components/forms/CreatableSelect";
import { ProductThumbnail } from "@/components/catalog/ProductImage";
import { ProductImageUpload } from "@/components/catalog/ProductImageUpload";
import { ProductPreviewCard } from "../components/ProductPreviewCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { productsApi, inventoryApi } from "@/services/api/catalog";
import { settingsApi } from "@/services/api/admin";
import { formatCurrency } from "@/utils/cn";
import type { AttributeDefinition, Product, ProductFormData } from "@/types/models/catalog";
import { appDialog } from "@/components/feedback/AppDialog";

function attrValueToInput(value: unknown): string {
  if (value == null) return "";
  if (Array.isArray(value)) return value.join(",");
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

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

  const { printing, printProductList, downloadProductList } = useProductListPrint({
    search,
    category: categoryFilter,
  });

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
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to="/categories">
              <Tag className="h-4 w-4" />
              Categories
            </Link>
          </Button>
          <Button variant="secondary" disabled={printing} onClick={() => void printProductList()}>
            {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileOutput className="h-4 w-4" />}
            Print
          </Button>
          <Button variant="secondary" disabled={printing} onClick={() => void downloadProductList()}>
            {printing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Export PDF
          </Button>
          <Button asChild className="shadow-[0_8px_20px_hsl(var(--primary)/0.22)]">
            <Link to="/products/new">
              <Plus className="h-4 w-4" />
              Add Product
            </Link>
          </Button>
        </div>
      }
    >
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Catalog items", value: total, icon: Package },
          { label: "On this page", value: products.length, icon: Boxes },
          { label: "Categories", value: categories.length, icon: Tag },
        ].map(({ label, value, icon: Icon }) => (
          <div
            key={label}
            className="ds-card-premium flex items-center gap-4 px-5 py-4"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
              <p className="text-2xl font-bold tabular-nums tracking-tight">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="ds-card-premium overflow-hidden">
      <DataTable
        exportTitle="Products"
        listPrint={false}
        listPdf={false}
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
      </div>
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
    description: "", image: "", is_active: true, requires_prescription: false,
    initial_stock: "0", warehouse_id: "",
  });
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [applicableAttrs, setApplicableAttrs] = useState<AttributeDefinition[]>([]);
  const [attrValues, setAttrValues] = useState<Record<string, string>>({});

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
    let cancelled = false;
    productsApi
      .applicableAttributes({ category_id: form.category_id || undefined })
      .then((res) => {
        if (!cancelled) setApplicableAttrs(res.data || []);
      })
      .catch(() => {
        if (!cancelled) setApplicableAttrs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [form.category_id]);

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
        requires_prescription: Boolean(p.requires_prescription),
        initial_stock: String(p.total_stock ?? 0),
        warehouse_id: p.warehouse_id || "",
      });
      const vals: Record<string, string> = {};
      for (const a of p.attributes || []) {
        vals[a.definition_id] = attrValueToInput(a.value);
      }
      setAttrValues(vals);
      setImagePreview(null);
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const attributes = applicableAttrs.map((def) => {
        const raw = attrValues[def.id] ?? "";
        let value: unknown = raw;
        if (def.data_type === "bool") {
          value = raw === "true" || raw === "1";
        } else if (def.data_type === "int") {
          value = raw === "" ? null : parseInt(raw, 10);
        } else if (def.data_type === "decimal") {
          value = raw === "" ? null : parseFloat(raw);
        } else if (def.data_type === "multi_select") {
          value = raw
            ? raw.split(",").map((s) => s.trim()).filter(Boolean)
            : [];
        } else if (raw === "") {
          value = null;
        }
        return { definition_id: def.id, value };
      });
      const payload: ProductFormData = {
        sku: form.sku.trim() || undefined,
        barcode: form.barcode || undefined,
        name: form.name,
        category_id: form.category_id,
        brand_id: form.brand_id || undefined,
        unit_id: form.unit_id || undefined,
        cost_price: parseFloat(form.cost_price),
        selling_price: parseFloat(form.selling_price),
        minimum_stock: parseInt(form.minimum_stock, 10),
        description: form.description,
        image: form.image || undefined,
        is_active: form.is_active,
        requires_prescription: form.requires_prescription,
        warehouse_id: form.warehouse_id || undefined,
        initial_stock: parseFloat(form.initial_stock) || 0,
        attributes,
      };
      if (editId) {
        payload.stock = parseFloat(form.initial_stock) || 0;
        await productsApi.update(editId, payload);
      } else {
        await productsApi.create(payload);
      }
      navigate("/products");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
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
      description={editId ? "Update product details, pricing, stock, and visibility." : "Create a polished catalog entry for POS, sales, and inventory."}
      breadcrumbs={["Home", "Products", editId ? "Edit" : "New"]}
      backTo="/products"
      backLabel="Back to products"
    >
      {optionsError && (
        <div className="rounded-2xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {optionsError}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <FormPanel
              title={editId ? "Edit product" : "Product registration"}
              description="Complete each section below. SKU and unit are optional — we assign defaults when left blank."
            >
              <FormPanelSection
                icon={<Tag className="h-4 w-4" />}
                title="General information"
                description="Classification, identity, and internal notes."
              >
                <FormGrid>
                  <FormField label="Category" required className="md:col-span-2 xl:col-span-3">
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
                  <FormField label="Product Name" required>
                    <Input
                      required
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="e.g. Wireless Mouse"
                      className="h-11 rounded-xl"
                    />
                  </FormField>
                  <FormField label="SKU" hint="Optional — auto-generated if empty">
                    <Input
                      value={form.sku}
                      onChange={(e) => setForm({ ...form, sku: e.target.value })}
                      placeholder="e.g. WM-001"
                      className="h-11 rounded-xl font-mono"
                    />
                  </FormField>
                  <FormField label="Barcode" hint="Optional EAN/UPC barcode">
                    <Input
                      value={form.barcode}
                      onChange={(e) => setForm({ ...form, barcode: e.target.value })}
                      placeholder="Scan or enter barcode"
                      className="h-11 rounded-xl font-mono"
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
                  <FormField label="Unit" hint="Optional — defaults to Each">
                    <CreatableSelect
                      value={form.unit_id}
                      onChange={(v) => setForm({ ...form, unit_id: v })}
                      options={units}
                      placeholder={optionsLoading ? "Loading units..." : "Select unit (optional)"}
                      disabled={optionsLoading}
                      createLabel="Create new unit..."
                      allowNone
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
                    rows={4}
                    placeholder="Short internal description for staff and reports..."
                    className="flex w-full resize-none rounded-xl border border-input bg-background/80 px-4 py-3 text-sm shadow-[inset_0_1px_2px_hsl(var(--foreground)/0.03)] focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </FormField>
              </FormPanelSection>

              <FormPanelSection
                icon={<ImageIcon className="h-4 w-4" />}
                title="Product image"
                description="Shown in catalog, POS tiles, receipts, and exports."
              >
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
              </FormPanelSection>

              {applicableAttrs.length > 0 && (
                <FormPanelSection
                  icon={<Sparkles className="h-4 w-4" />}
                  title="Additional attributes"
                  description="Fields from your business type and category."
                >
                  <FormGrid>
                    {applicableAttrs.map((def) => (
                      <FormField
                        key={def.id}
                        label={def.name}
                        required={def.is_required}
                        hint={def.description || undefined}
                      >
                        {def.data_type === "bool" ? (
                          <select
                            value={attrValues[def.id] ?? ""}
                            onChange={(e) =>
                              setAttrValues((v) => ({ ...v, [def.id]: e.target.value }))
                            }
                            className="flex h-11 w-full rounded-xl border border-input bg-background/80 px-3 text-sm"
                            required={def.is_required}
                          >
                            <option value="">—</option>
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                          </select>
                        ) : def.data_type === "select" ? (
                          <select
                            value={attrValues[def.id] ?? ""}
                            onChange={(e) =>
                              setAttrValues((v) => ({ ...v, [def.id]: e.target.value }))
                            }
                            className="flex h-11 w-full rounded-xl border border-input bg-background/80 px-3 text-sm"
                            required={def.is_required}
                          >
                            <option value="">Select…</option>
                            {def.options.map((o) => (
                              <option key={o.id} value={o.value}>
                                {o.label}
                              </option>
                            ))}
                          </select>
                        ) : def.data_type === "multi_select" ? (
                          <Input
                            value={attrValues[def.id] ?? ""}
                            onChange={(e) =>
                              setAttrValues((v) => ({ ...v, [def.id]: e.target.value }))
                            }
                            placeholder="Comma-separated values"
                            className="h-11 rounded-xl"
                            required={def.is_required}
                          />
                        ) : (
                          <Input
                            type={
                              def.data_type === "int" || def.data_type === "decimal"
                                ? "number"
                                : def.data_type === "date"
                                  ? "date"
                                  : def.data_type === "datetime"
                                    ? "datetime-local"
                                    : "text"
                            }
                            step={def.data_type === "decimal" ? "0.0001" : undefined}
                            value={attrValues[def.id] ?? ""}
                            onChange={(e) =>
                              setAttrValues((v) => ({ ...v, [def.id]: e.target.value }))
                            }
                            className="h-11 rounded-xl"
                            required={def.is_required}
                          />
                        )}
                      </FormField>
                    ))}
                  </FormGrid>
                </FormPanelSection>
              )}

              <FormPanelSection
                icon={<Boxes className="h-4 w-4" />}
                title="Pricing & inventory"
                description="Cost structure, retail price, and stock thresholds."
              >
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
                      className="h-11 rounded-xl tabular-nums"
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
                      className="h-11 rounded-xl tabular-nums"
                    />
                  </FormField>
                  <FormField label="Minimum Stock" hint="Low-stock alert threshold">
                    <Input
                      type="number"
                      min="0"
                      value={form.minimum_stock}
                      onChange={(e) => setForm({ ...form, minimum_stock: e.target.value })}
                      className="h-11 rounded-xl tabular-nums"
                    />
                  </FormField>
                  {!editId ? (
                    <>
                      <FormField label="Initial Stock" hint="Creates inventory at this quantity (0 is allowed)">
                        <Input
                          type="number"
                          min="0"
                          step="any"
                          value={form.initial_stock}
                          onChange={(e) => setForm({ ...form, initial_stock: e.target.value })}
                          className="h-11 rounded-xl tabular-nums"
                        />
                      </FormField>
                      <FormField label="Warehouse" hint="Where this stock is held">
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
                  ) : (
                    <>
                      <FormField label="Stock on hand" hint="Updates inventory for the selected warehouse">
                        <Input
                          type="number"
                          min="0"
                          step="any"
                          value={form.initial_stock}
                          onChange={(e) => setForm({ ...form, initial_stock: e.target.value })}
                          className="h-11 rounded-xl tabular-nums"
                        />
                      </FormField>
                      <FormField label="Warehouse" hint="Where this stock is held">
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
              </FormPanelSection>
            </FormPanel>
          }
          aside={
            <>
              <ProductPreviewCard
                image={imagePreview || form.image}
                name={form.name}
                sku={form.sku}
                categoryName={categories.find((c) => c.id === form.category_id)?.name}
                isActive={form.is_active}
                cost={cost}
                price={price}
                margin={margin}
              />

              <div className="ds-card-premium overflow-hidden">
                <div className="border-b border-border/60 px-5 py-4">
                  <p className="text-sm font-semibold tracking-tight">Visibility</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">Control where this product appears</p>
                </div>
                <div className="p-5 space-y-3">
                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/50 bg-background/60 p-4 transition-colors hover:bg-muted/20">
                    <Checkbox
                      checked={form.is_active}
                      onCheckedChange={(v) => setForm({ ...form, is_active: !!v })}
                      className="mt-0.5"
                    />
                    <div>
                      <p className="text-sm font-medium">Active in catalog</p>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        Inactive products are hidden from POS and sales workflows.
                      </p>
                    </div>
                  </label>
                  <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/50 bg-background/60 p-4 transition-colors hover:bg-muted/20">
                    <Checkbox
                      checked={form.requires_prescription}
                      onCheckedChange={(v) => setForm({ ...form, requires_prescription: !!v })}
                      className="mt-0.5"
                    />
                    <div>
                      <p className="text-sm font-medium">Requires prescription</p>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        When the pharmacy module is on, POS checkout needs an active Rx covering this product.
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="rounded-2xl border border-primary/15 bg-primary/5 px-5 py-4">
                <div className="flex gap-3">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Set minimum stock to receive low-inventory alerts on your dashboard and inventory pages.
                  </p>
                </div>
              </div>
            </>
          }
          actions={
            <FormActions>
              <div className="flex flex-wrap gap-3">
                <Button type="submit" loading={saving} className="min-w-[140px] shadow-[0_8px_20px_hsl(var(--primary)/0.2)]">
                  {editId ? "Save Changes" : "Create Product"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/products")}>
                  Cancel
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {editId ? "Updates apply immediately across POS and reports." : "Product will be available in POS after creation."}
              </p>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}
