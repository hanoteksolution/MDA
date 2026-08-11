import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import { restaurantApi, type MenuCategory, type MenuItem } from "@/services/api/restaurant";
import { formatCurrency } from "@/utils/cn";

export function RestaurantMenuItemFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(Boolean(editId));
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [form, setForm] = useState({
    name: "",
    category_id: "",
    sku: "",
    unit_price: "",
    description: "",
    is_available: true,
  });

  useEffect(() => {
    if (!branchId) return;
    restaurantApi.categories(1, branchId).then((res) => setCategories(res.data.results)).catch(() => undefined);
  }, [branchId]);

  useEffect(() => {
    if (!editId) return;
    restaurantApi
      .item(editId)
      .then((res) => {
        const row = res.data;
        setForm({
          name: row.name || "",
          category_id: row.category_id || "",
          sku: row.sku || "",
          unit_price: String(row.unit_price || ""),
          description: row.description || "",
          is_available: row.is_available,
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Menu item not found."))
      .finally(() => setLoading(false));
  }, [editId]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchId) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        category_id: form.category_id,
        branch_id: branchId,
        sku: form.sku.trim() || undefined,
        unit_price: Number(form.unit_price || 0),
        description: form.description || undefined,
        is_available: form.is_available,
      };
      if (editId) await restaurantApi.updateItem(editId, payload);
      else await restaurantApi.createItem(payload);
      navigate("/restaurant/menu");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Restaurant", "Menu"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit menu item" : "New menu item"}
      breadcrumbs={["Home", "Restaurant", "Menu", editId ? "Edit" : "New"]}
    >
      <form onSubmit={onSubmit}>
        <FormPageLayout
          main={
            <FormSection title="Basic information">
              <FormGrid>
                <FormField label="Name" required>
                  <Input required value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
                </FormField>
                <FormField label="Category" required>
                  <Select value={form.category_id} onValueChange={(v) => setForm((s) => ({ ...s, category_id: v }))}>
                    <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                    <SelectContent>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="SKU">
                  <Input value={form.sku} onChange={(e) => setForm((s) => ({ ...s, sku: e.target.value }))} />
                </FormField>
                <FormField label="Unit price">
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.unit_price}
                    onChange={(e) => setForm((s) => ({ ...s, unit_price: e.target.value }))}
                  />
                </FormField>
                <FormField label="Description" className="md:col-span-2 xl:col-span-3">
                  <Input value={form.description} onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))} />
                </FormField>
                <FormField label="Availability">
                  <Select
                    value={form.is_available ? "yes" : "no"}
                    onValueChange={(v) => setForm((s) => ({ ...s, is_available: v === "yes" }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yes">Available</SelectItem>
                      <SelectItem value="no">Unavailable</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
              </FormGrid>
            </FormSection>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save changes" : "Create item"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/restaurant/menu")}>Cancel</Button>
              </div>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}

export function RestaurantMenuItemEditPage() {
  const { id } = useParams();
  return <RestaurantMenuItemFormPage editId={id} />;
}

export function RestaurantMenuItemDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [row, setRow] = useState<MenuItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    restaurantApi
      .item(id)
      .then((res) => setRow(res.data))
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Menu item not found."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !row) {
    return (
      <PageLayout title={loading ? "Loading..." : "Menu item"} breadcrumbs={["Home", "Restaurant", "Menu"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={row.name}
      description={row.category_name}
      breadcrumbs={["Home", "Restaurant", "Menu", row.name]}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate(`/restaurant/menu/items/${row.id}/edit`)}>Edit</Button>
          <Button variant="secondary" onClick={() => navigate("/restaurant/menu")}>Back</Button>
        </div>
      }
    >
      <ContentSection title="Overview">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <p><span className="text-muted-foreground">SKU</span> · {row.sku || "—"}</p>
          <p><span className="text-muted-foreground">Price</span> · {formatCurrency(row.unit_price)}</p>
          <p>
            <span className="text-muted-foreground">Status</span> ·{" "}
            <Badge variant={row.is_available ? "success" : "secondary"}>
              {row.is_available ? "Available" : "Unavailable"}
            </Badge>
          </p>
          <p><span className="text-muted-foreground">Category</span> · {row.category_name}</p>
          <p className="md:col-span-2 xl:col-span-3"><span className="text-muted-foreground">Description</span> · {row.description || "—"}</p>
        </div>
      </ContentSection>
    </PageLayout>
  );
}
