import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { settingsApi } from "@/services/api/admin";

export function BranchFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [form, setForm] = useState({
    name: "", code: "", address: "", phone: "", email: "", is_active: true,
  });

  useEffect(() => {
    settingsApi.company().then((res) => {
      if (res.data?.id) setCompanyId(res.data.id);
    });
  }, []);

  useEffect(() => {
    if (!editId) return;
    settingsApi.branches().then((res) => {
      const branch = res.data.find((b) => b.id === editId);
      if (branch) {
        setForm({
          name: branch.name, code: branch.code,
          address: branch.address || "", phone: branch.phone || "",
          email: branch.email || "", is_active: branch.is_active,
        });
      }
      setLoading(false);
    });
  }, [editId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editId) {
        await settingsApi.updateBranch(editId, form);
      } else {
        if (!companyId) throw new Error("Company profile not found.");
        await settingsApi.createBranch({ ...form, company_id: companyId });
      }
      navigate("/settings");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={["Home", "Settings"]}>
        <div className="h-64 animate-pulse rounded-2xl bg-muted" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title={editId ? "Edit Branch" : "Add Branch"}
      description="Configure a store branch location."
      breadcrumbs={["Home", "Settings", editId ? "Edit Branch" : "New Branch"]}
    >
      <form onSubmit={handleSubmit}>
        <FormSection title="Branch Information">
          <FormGrid>
            <FormField label="Branch Name" required>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </FormField>
            <FormField label="Branch Code" required hint="Short unique code, e.g. BR02">
              <Input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} className="font-mono" />
            </FormField>
            <FormField label="Phone">
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </FormField>
            <FormField label="Email">
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </FormField>
            <FormField label="Address" className="md:col-span-2">
              <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </FormField>
          </FormGrid>
          <label className="mt-6 flex items-center gap-3 cursor-pointer">
            <Checkbox checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: !!v })} />
            <span className="text-sm font-medium">Active branch</span>
          </label>
        </FormSection>
        <div className="mt-6 flex gap-3">
          <Button type="submit" loading={saving}>{editId ? "Save Changes" : "Create Branch"}</Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/settings")}>Cancel</Button>
        </div>
      </form>
    </PageLayout>
  );
}
