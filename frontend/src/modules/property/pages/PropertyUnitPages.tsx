import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { FormActions, FormPageLayout } from "@/components/forms/FormPageLayout";
import { ContentSection } from "@/components/layout/ContentSection";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuthStore } from "@/store/authStore";
import { usePermissions } from "@/hooks/usePermissions";
import {
  propertyApi,
  type PropertyBuilding,
  type PropertyUnit,
} from "@/services/api/property";
import { appDialog } from "@/components/feedback/AppDialog";
import { formatCurrency } from "@/utils/cn";

export function PropertyUnitFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const branchId = useAuthStore((s) => s.user?.branch?.id);
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [buildings, setBuildings] = useState<PropertyBuilding[]>([]);
  const [form, setForm] = useState({
    code: "",
    building_id: "",
    kind: "residential",
    status: "vacant",
    floor: "",
    bedrooms: "0",
    bathrooms: "0",
    rent_amount: "",
    deposit_amount: "",
    notes: "",
  });

  useEffect(() => {
    if (!branchId) return;
    propertyApi.buildings(1, branchId).then((res) => setBuildings(res.data.results));
  }, [branchId]);

  useEffect(() => {
    if (!editId) return;
    propertyApi
      .unit(editId)
      .then((res) => {
        const u = res.data;
        setForm({
          code: u.code || "",
          building_id: u.building_id || "",
          kind: u.kind || "residential",
          status: u.status || "vacant",
          floor: u.floor || "",
          bedrooms: String(u.bedrooms || 0),
          bathrooms: String(u.bathrooms || 0),
          rent_amount: String(u.rent_amount || ""),
          deposit_amount: String(u.deposit_amount || ""),
          notes: u.notes || "",
        });
      })
      .catch((err) => appDialog.alert(err instanceof Error ? err.message : "Not found"))
      .finally(() => setLoading(false));
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchId) return;
    setSaving(true);
    try {
      const payload = {
        branch_id: branchId,
        building_id: form.building_id,
        code: form.code.trim(),
        kind: form.kind,
        status: form.status,
        floor: form.floor || undefined,
        bedrooms: Number(form.bedrooms) || 0,
        bathrooms: Number(form.bathrooms) || 0,
        rent_amount: Number(form.rent_amount) || 0,
        deposit_amount: Number(form.deposit_amount) || 0,
        notes: form.notes || undefined,
      };
      if (editId) await propertyApi.updateUnit(editId, payload);
      else await propertyApi.createUnit(payload);
      navigate(editId ? `/property/units/${editId}` : "/property/units");
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Property", "Units"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit unit" : "New unit"}
      breadcrumbs={["Home", "Property", "Units", editId ? "Edit" : "New"]}
    >
      <form onSubmit={handleSubmit}>
        <FormPageLayout
          main={
            <FormSection title="Unit">
              <FormGrid>
                <FormField label="Code" required>
                  <Input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
                </FormField>
                <FormField label="Building" required>
                  <Select value={form.building_id} onValueChange={(v) => setForm({ ...form, building_id: v })}>
                    <SelectTrigger><SelectValue placeholder="Select building" /></SelectTrigger>
                    <SelectContent>
                      {buildings.map((b) => (
                        <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Kind">
                  <Select value={form.kind} onValueChange={(v) => setForm({ ...form, kind: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="residential">Residential</SelectItem>
                      <SelectItem value="office">Office</SelectItem>
                      <SelectItem value="retail">Retail</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Status">
                  <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vacant">Vacant</SelectItem>
                      <SelectItem value="occupied">Occupied</SelectItem>
                      <SelectItem value="maintenance">Maintenance</SelectItem>
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="Floor">
                  <Input value={form.floor} onChange={(e) => setForm({ ...form, floor: e.target.value })} />
                </FormField>
                <FormField label="Bedrooms">
                  <Input type="number" min="0" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })} />
                </FormField>
                <FormField label="Bathrooms">
                  <Input type="number" min="0" value={form.bathrooms} onChange={(e) => setForm({ ...form, bathrooms: e.target.value })} />
                </FormField>
                <FormField label="Rent">
                  <Input type="number" min="0" step="0.01" value={form.rent_amount} onChange={(e) => setForm({ ...form, rent_amount: e.target.value })} />
                </FormField>
                <FormField label="Deposit">
                  <Input type="number" min="0" step="0.01" value={form.deposit_amount} onChange={(e) => setForm({ ...form, deposit_amount: e.target.value })} />
                </FormField>
                <FormField label="Notes" className="sm:col-span-2">
                  <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </FormField>
              </FormGrid>
            </FormSection>
          }
          actions={
            <FormActions>
              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editId ? "Save" : "Create unit"}</Button>
                <Button type="button" variant="secondary" onClick={() => navigate("/property/units")}>
                  Cancel
                </Button>
              </div>
            </FormActions>
          }
        />
      </form>
    </PageLayout>
  );
}

export function PropertyUnitEditPage() {
  const { id } = useParams();
  return <PropertyUnitFormPage editId={id} />;
}

export function PropertyUnitDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasAnyPermission } = usePermissions();
  const canManage = hasAnyPermission("property_management.manage", "property_management.masters.update");
  const [unit, setUnit] = useState<PropertyUnit | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    propertyApi
      .unit(id)
      .then((res) => setUnit(res.data))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !unit) {
    return (
      <PageLayout title={loading ? "Loading..." : "Unit"} breadcrumbs={["Home", "Property", "Units"]}>
        {loading ? <div className="h-64 animate-pulse rounded-2xl bg-muted" /> : null}
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={unit.label || unit.code}
      description={`${unit.building_name} · ${unit.property_name || ""}`}
      breadcrumbs={["Home", "Property", "Units", unit.code]}
      actions={
        <div className="flex gap-2">
          {canManage ? (
            <Button variant="secondary" onClick={() => navigate(`/property/units/${unit.id}/edit`)}>
              Edit
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => navigate("/property/units")}>
            Back
          </Button>
        </div>
      }
    >
      <ContentSection title="Unit">
        <div className="grid gap-3 sm:grid-cols-2 text-sm">
          <p><span className="text-muted-foreground">Code</span> · {unit.code}</p>
          <p><span className="text-muted-foreground">Kind</span> · {unit.kind}</p>
          <p>
            <span className="text-muted-foreground">Status</span> · <Badge variant="secondary">{unit.status}</Badge>
          </p>
          <p><span className="text-muted-foreground">Floor</span> · {unit.floor || "—"}</p>
          <p><span className="text-muted-foreground">Beds / baths</span> · {unit.bedrooms} / {unit.bathrooms}</p>
          <p><span className="text-muted-foreground">Rent</span> · {formatCurrency(unit.rent_amount)}</p>
          <p><span className="text-muted-foreground">Deposit</span> · {formatCurrency(unit.deposit_amount)}</p>
        </div>
      </ContentSection>
    </PageLayout>
  );
}
