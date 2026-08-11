import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAuthStore } from "@/store/authStore";
import {
  restaurantApi,
  type Ingredient,
  type KitchenStation,
  type MenuItem,
  type Modifier,
  type ModifierGroup,
  type Recipe,
  type RestaurantFloor,
} from "@/services/api/restaurant";
import { formatCurrency } from "@/utils/cn";

function LoadingShell({ title }: { title: string }) {
  return (
    <PageLayout title={title} breadcrumbs={["Home", "Restaurant"]}>
      <div className="h-64 animate-pulse rounded-2xl bg-muted" />
    </PageLayout>
  );
}

export function RestaurantFloorFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(Boolean(editId));
  const [form, setForm] = useState({ name: "", code: "", sort_order: "100" });
  useEffect(() => {
    if (!editId) return;
    restaurantApi.floor(editId).then((res) => {
      const r = res.data;
      setForm({ name: r.name, code: r.code, sort_order: String(r.sort_order) });
    }).catch(() => undefined).finally(() => setLoading(false));
  }, [editId]);
  if (loading) return <LoadingShell title="Loading floor..." />;
  return (
    <PageLayout title={editId ? "Edit floor" : "New floor"} breadcrumbs={["Home", "Restaurant", "Floors"]}>
      <form onSubmit={async (e) => {
        e.preventDefault();
        if (!branchId) return;
        try {
          const payload = { branch_id: branchId, name: form.name, code: form.code, sort_order: Number(form.sort_order || 100) };
          if (editId) await restaurantApi.updateFloor(editId, payload);
          else await restaurantApi.createFloor(payload);
          navigate("/restaurant/tables");
        } catch (err) {
          await appDialog.alert(err instanceof Error ? err.message : "Save failed");
        }
      }}>
        <FormPageLayout
          main={<FormSection title="Floor"><FormGrid><FormField label="Name" required><Input required value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /></FormField><FormField label="Code" required><Input required value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} /></FormField></FormGrid></FormSection>}
          actions={<FormActions><div className="flex gap-2"><Button type="submit">{editId ? "Save" : "Create"}</Button><Button type="button" variant="secondary" onClick={() => navigate("/restaurant/tables")}>Cancel</Button></div></FormActions>}
        />
      </form>
    </PageLayout>
  );
}
export function RestaurantFloorEditPage() { const { id } = useParams(); return <RestaurantFloorFormPage editId={id} />; }
export function RestaurantFloorDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [row, setRow] = useState<RestaurantFloor | null>(null);
  useEffect(() => { if (id) restaurantApi.floor(id).then((r) => setRow(r.data)).catch(() => undefined); }, [id]);
  if (!row) return <LoadingShell title="Floor" />;
  return <PageLayout title={row.name} breadcrumbs={["Home", "Restaurant", "Floors", row.name]} actions={<Button onClick={() => navigate(`/restaurant/floors/${row.id}/edit`)}>Edit</Button>}><ContentSection title="Details"><p>Code: {row.code}</p></ContentSection></PageLayout>;
}

export function RestaurantStationFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(Boolean(editId));
  const [form, setForm] = useState({ name: "", code: "" });
  useEffect(() => { if (editId) restaurantApi.station(editId).then((r) => setForm({ name: r.data.name, code: r.data.code })).finally(() => setLoading(false)); }, [editId]);
  if (loading) return <LoadingShell title="Loading station..." />;
  return <PageLayout title={editId ? "Edit station" : "New station"} breadcrumbs={["Home", "Restaurant", "Kitchen Stations"]}><form onSubmit={async (e) => { e.preventDefault(); if (!branchId) return; const payload = { branch_id: branchId, ...form }; if (editId) await restaurantApi.updateStation(editId, payload); else await restaurantApi.createStation(payload); navigate("/restaurant/kitchen"); }}><FormPageLayout main={<FormSection title="Station"><FormGrid><FormField label="Name"><Input value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /></FormField><FormField label="Code"><Input value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} /></FormField></FormGrid></FormSection>} actions={<FormActions><Button type="submit">{editId ? "Save" : "Create"}</Button></FormActions>} /></form></PageLayout>;
}
export function RestaurantStationEditPage() { const { id } = useParams(); return <RestaurantStationFormPage editId={id} />; }
export function RestaurantStationDetailPage() {
  const { id } = useParams(); const [row, setRow] = useState<KitchenStation | null>(null); useEffect(() => { if (id) restaurantApi.station(id).then((r) => setRow(r.data)); }, [id]); if (!row) return <LoadingShell title="Kitchen station" />; return <PageLayout title={row.name} breadcrumbs={["Home", "Restaurant", "Kitchen Stations", row.name]}><ContentSection title="Details"><p>Code: {row.code}</p></ContentSection></PageLayout>;
}

export function RestaurantModifierFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [groups, setGroups] = useState<ModifierGroup[]>([]);
  const [form, setForm] = useState({ name: "", code: "", group_id: "", price_delta: "0" });
  useEffect(() => { if (branchId) restaurantApi.modifierGroups(1, branchId).then((r) => setGroups(r.data.results)); }, [branchId]);
  useEffect(() => { if (editId) restaurantApi.modifier(editId).then((r) => setForm({ name: r.data.name, code: r.data.code, group_id: r.data.group_id, price_delta: String(r.data.price_delta) })); }, [editId]);
  return <PageLayout title={editId ? "Edit modifier" : "New modifier"} breadcrumbs={["Home", "Restaurant", "Modifiers"]}><form onSubmit={async (e) => { e.preventDefault(); if (!branchId) return; const payload = { branch_id: branchId, name: form.name, code: form.code, group_id: form.group_id, price_delta: Number(form.price_delta || 0) }; if (editId) await restaurantApi.updateModifier(editId, payload); else await restaurantApi.createModifier(payload); navigate("/restaurant/menu"); }}><FormPageLayout main={<FormSection title="Modifier"><FormGrid><FormField label="Name"><Input value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /></FormField><FormField label="Group"><Select value={form.group_id} onValueChange={(v) => setForm((s) => ({ ...s, group_id: v }))}><SelectTrigger><SelectValue placeholder="Select group" /></SelectTrigger><SelectContent>{groups.map((g) => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}</SelectContent></Select></FormField><FormField label="Code"><Input value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} /></FormField><FormField label="Price delta"><Input value={form.price_delta} onChange={(e) => setForm((s) => ({ ...s, price_delta: e.target.value }))} /></FormField></FormGrid></FormSection>} actions={<FormActions><Button type="submit">{editId ? "Save" : "Create"}</Button></FormActions>} /></form></PageLayout>;
}
export function RestaurantModifierEditPage() { const { id } = useParams(); return <RestaurantModifierFormPage editId={id} />; }
export function RestaurantModifierDetailPage() {
  const { id } = useParams(); const [row, setRow] = useState<Modifier | null>(null); useEffect(() => { if (id) restaurantApi.modifier(id).then((r) => setRow(r.data)); }, [id]); if (!row) return <LoadingShell title="Modifier" />; return <PageLayout title={row.name} breadcrumbs={["Home", "Restaurant", "Modifiers", row.name]}><ContentSection title="Details"><p>Group: {row.group_name}</p><p>Price delta: {formatCurrency(row.price_delta)}</p></ContentSection></PageLayout>;
}

export function RestaurantIngredientFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate(); const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [form, setForm] = useState({ name: "", code: "", unit: "unit", unit_cost: "0" });
  useEffect(() => { if (editId) restaurantApi.ingredient(editId).then((r) => setForm({ name: r.data.name, code: r.data.code, unit: r.data.unit, unit_cost: String(r.data.unit_cost) })); }, [editId]);
  return <PageLayout title={editId ? "Edit ingredient" : "New ingredient"} breadcrumbs={["Home", "Restaurant", "Ingredients"]}><form onSubmit={async (e) => { e.preventDefault(); if (!branchId) return; const payload = { branch_id: branchId, ...form, unit_cost: Number(form.unit_cost || 0) }; if (editId) await restaurantApi.updateIngredient(editId, payload); else await restaurantApi.createIngredient(payload); navigate("/restaurant/inventory"); }}><FormPageLayout main={<FormSection title="Ingredient"><FormGrid><FormField label="Name"><Input value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /></FormField><FormField label="Code"><Input value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} /></FormField><FormField label="Unit"><Input value={form.unit} onChange={(e) => setForm((s) => ({ ...s, unit: e.target.value }))} /></FormField><FormField label="Unit cost"><Input value={form.unit_cost} onChange={(e) => setForm((s) => ({ ...s, unit_cost: e.target.value }))} /></FormField></FormGrid></FormSection>} actions={<FormActions><Button type="submit">{editId ? "Save" : "Create"}</Button></FormActions>} /></form></PageLayout>;
}
export function RestaurantIngredientEditPage() { const { id } = useParams(); return <RestaurantIngredientFormPage editId={id} />; }
export function RestaurantIngredientDetailPage() {
  const { id } = useParams(); const [row, setRow] = useState<Ingredient | null>(null); useEffect(() => { if (id) restaurantApi.ingredient(id).then((r) => setRow(r.data)); }, [id]); if (!row) return <LoadingShell title="Ingredient" />; return <PageLayout title={row.name} breadcrumbs={["Home", "Restaurant", "Ingredients", row.name]}><ContentSection title="Details"><p>Code: {row.code}</p><p>Unit cost: {formatCurrency(row.unit_cost)}</p></ContentSection></PageLayout>;
}

export function RestaurantRecipeFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate(); const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [form, setForm] = useState({ name: "", menu_item_id: "", version: "v1", yield_qty: "1", waste_percent: "0", ingredient_id: "", ingredient_qty: "1" });
  useEffect(() => { if (!branchId) return; restaurantApi.items(1, branchId).then((r) => setItems(r.data.results)); restaurantApi.ingredients(1, branchId).then((r) => setIngredients(r.data.results)); }, [branchId]);
  useEffect(() => { if (editId) restaurantApi.recipe(editId).then((r) => setForm((s) => ({ ...s, name: r.data.name, menu_item_id: r.data.menu_item_id, version: r.data.version, yield_qty: String(r.data.yield_qty), waste_percent: String(r.data.waste_percent) }))); }, [editId]);
  return <PageLayout title={editId ? "Edit recipe" : "New recipe"} breadcrumbs={["Home", "Restaurant", "Recipes"]}><form onSubmit={async (e) => { e.preventDefault(); if (!branchId) return; const payload = { branch_id: branchId, name: form.name, menu_item_id: form.menu_item_id, version: form.version, yield_qty: Number(form.yield_qty || 1), waste_percent: Number(form.waste_percent || 0) }; if (editId) await restaurantApi.updateRecipe(editId, payload); else { const created = await restaurantApi.createRecipe(payload); if (form.ingredient_id) { await restaurantApi.addRecipeIngredient(created.data.id, { ingredient_id: form.ingredient_id, quantity: Number(form.ingredient_qty || 1) }); } } navigate("/restaurant/menu"); }}><FormPageLayout main={<FormSection title="Recipe"><FormGrid><FormField label="Name"><Input value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} /></FormField><FormField label="Menu item"><Select value={form.menu_item_id} onValueChange={(v) => setForm((s) => ({ ...s, menu_item_id: v }))}><SelectTrigger><SelectValue placeholder="Select menu item" /></SelectTrigger><SelectContent>{items.map((i) => <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>)}</SelectContent></Select></FormField><FormField label="Version"><Input value={form.version} onChange={(e) => setForm((s) => ({ ...s, version: e.target.value }))} /></FormField><FormField label="Yield"><Input value={form.yield_qty} onChange={(e) => setForm((s) => ({ ...s, yield_qty: e.target.value }))} /></FormField><FormField label="Waste %"><Input value={form.waste_percent} onChange={(e) => setForm((s) => ({ ...s, waste_percent: e.target.value }))} /></FormField><FormField label="Initial ingredient"><Select value={form.ingredient_id} onValueChange={(v) => setForm((s) => ({ ...s, ingredient_id: v }))}><SelectTrigger><SelectValue placeholder="Optional" /></SelectTrigger><SelectContent>{ingredients.map((i) => <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>)}</SelectContent></Select></FormField></FormGrid></FormSection>} actions={<FormActions><Button type="submit">{editId ? "Save" : "Create"}</Button></FormActions>} /></form></PageLayout>;
}
export function RestaurantRecipeEditPage() { const { id } = useParams(); return <RestaurantRecipeFormPage editId={id} />; }
export function RestaurantRecipeDetailPage() {
  const { id } = useParams(); const [row, setRow] = useState<Recipe | null>(null); useEffect(() => { if (id) restaurantApi.recipe(id).then((r) => setRow(r.data)); }, [id]); if (!row) return <LoadingShell title="Recipe" />; return <PageLayout title={row.name} description={row.menu_item_name} breadcrumbs={["Home", "Restaurant", "Recipes", row.name]}><ContentSection title="Details"><p>Version: {row.version}</p><p>Total cost: {formatCurrency(row.total_cost)}</p></ContentSection></PageLayout>;
}
