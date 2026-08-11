import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil, Trash2, Tag, X } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { FormField, FormGrid } from "@/components/forms/FormField";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { productsApi } from "@/services/api/catalog";
import { usePermissions } from "@/hooks/usePermissions";
import type { Category } from "@/types/models/catalog";
import { appDialog } from "@/components/feedback/AppDialog";

type CategoryFormState = {
  name: string;
  description: string;
  is_active: boolean;
};

const emptyForm: CategoryFormState = {
  name: "",
  description: "",
  is_active: true,
};

export function CategoriesPage() {
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("products.create");
  const canUpdate = hasPermission("products.update");
  const canDelete = hasPermission("products.delete");

  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<CategoryFormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await productsApi.categories({ search: search || undefined });
      setCategories(res.data.results);
    } catch {
      setCategories([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setError(null);
    setFormOpen(true);
  };

  const openEdit = (cat: Category) => {
    setEditingId(cat.id);
    setForm({
      name: cat.name,
      description: cat.description || "",
      is_active: cat.is_active,
    });
    setError(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setForm(emptyForm);
    setError(null);
  };

  const handleSave = async () => {
    const name = form.name.trim();
    if (!name) {
      setError("Category name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name,
        description: form.description.trim(),
        is_active: form.is_active,
      };
      if (editingId) {
        await productsApi.updateCategory(editingId, payload);
        await appDialog.alert(`"${name}" was saved.`, { title: "Category updated", tone: "success" });
      } else {
        await productsApi.createCategory(payload);
        await appDialog.alert(`"${name}" was added.`, { title: "Category created", tone: "success" });
      }
      closeForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save category.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (cat: Category) => {
    const ok = await appDialog.confirm(
      `Delete category "${cat.name}"? Products using it may be affected.`,
      { title: "Delete category", tone: "danger", confirmLabel: "Delete" },
    );
    if (!ok) return;
    try {
      await productsApi.deleteCategory(cat.id);
      await appDialog.alert(`"${cat.name}" was removed.`, { title: "Category deleted", tone: "success" });
      if (editingId === cat.id) closeForm();
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete category.", {
        title: "Delete failed",
        tone: "danger",
      });
    }
  };

  const columns: Column<Category>[] = [
    {
      key: "name",
      header: "Category",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.name}</p>
          {r.description ? (
            <p className="text-xs text-muted-foreground line-clamp-1">{r.description}</p>
          ) : null}
        </div>
      ),
      exportValue: (r) => r.name,
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
          {canUpdate && (
            <Button variant="ghost" size="sm" onClick={() => openEdit(r)} title="Edit">
              <Pencil className="h-4 w-4" />
            </Button>
          )}
          {canDelete && (
            <Button variant="ghost" size="sm" onClick={() => void handleDelete(r)} title="Delete">
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="Categories"
      description="Organize products with categories you can create, edit, and delete."
      breadcrumbs={["Home", "Products", "Categories"]}
      backTo="/products"
      backLabel="Products"
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" asChild>
            <Link to="/products">Products</Link>
          </Button>
          {canCreate && (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Add Category
            </Button>
          )}
        </div>
      }
    >
      {formOpen && (
        <div className="mb-6 rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Tag className="h-4 w-4" />
              </div>
              <div>
                <p className="font-semibold">{editingId ? "Edit category" : "New category"}</p>
                <p className="text-xs text-muted-foreground">
                  {editingId ? "Update name, description, or status." : "Add a category for your catalog."}
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={closeForm} aria-label="Close form">
              <X className="h-4 w-4" />
            </Button>
          </div>

          <FormGrid>
            <FormField label="Name" required>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Beverages"
                autoFocus
              />
            </FormField>
            <FormField label="Status">
              <label className="flex h-10 items-center gap-2 text-sm">
                <Checkbox
                  checked={form.is_active}
                  onCheckedChange={(v) => setForm((f) => ({ ...f, is_active: v === true }))}
                />
                Active
              </label>
            </FormField>
            <FormField label="Description" className="md:col-span-2 xl:col-span-3">
              <Input
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Optional notes"
              />
            </FormField>
          </FormGrid>

          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => void handleSave()} disabled={saving}>
              {saving ? "Saving…" : editingId ? "Save changes" : "Create category"}
            </Button>
            <Button variant="secondary" onClick={closeForm} disabled={saving}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <DataTable
        exportTitle="Categories"
        columns={columns}
        data={categories}
        loading={loading}
        emptyMessage="No categories yet. Create one to organize products."
        searchPlaceholder="Search categories..."
        searchValue={search}
        onSearchChange={setSearch}
      />
    </PageLayout>
  );
}
