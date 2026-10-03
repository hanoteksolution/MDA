import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Store } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { settingsApi } from "@/services/api/admin";
import { useScopedPath } from "@/hooks/useScopedPath";
import { appDialog } from "@/components/feedback/AppDialog";

export function BranchFormPage({ editId }: { editId?: string }) {
  const navigate = useNavigate();
  const { scoped } = useScopedPath();
  const [loading, setLoading] = useState(!!editId);
  const [saving, setSaving] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [form, setForm] = useState({
    name: "", code: "", address: "", phone: "", email: "", is_active: true,
  });

  useEffect(() => {
    settingsApi.company().then((res) => {
      const name = res.data?.name;
      if (res.data?.id) setCompanyId(res.data.id);
      if (name) setCompanyName((current) => current || name);
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
        // The branch's own company always wins over the caller's default profile,
        // so an elevated admin editing another company's branch still sees the truth.
        if (branch.company_name) setCompanyName(branch.company_name);
        if (branch.company_id) setCompanyId(branch.company_id);
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
      navigate(scoped("/settings"));
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed");
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
        <FormSection title="Shop / Company" description="Every branch belongs to one shop. This is set automatically and cannot be changed here.">
          <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/30 px-4 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Store className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-medium text-foreground">{companyName || "—"}</p>
              <p className="text-xs text-muted-foreground">
                This branch operates under {companyName || "this shop"}.{" "}
                <Link to={scoped("/settings")} className="text-primary hover:underline">Manage Shop / Company</Link>
              </p>
            </div>
          </div>
        </FormSection>
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
            <FormField label="Address" className="md:col-span-2 xl:col-span-3">
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
          <Button type="button" variant="secondary" onClick={() => navigate(scoped("/settings"))}>Cancel</Button>
        </div>
      </form>
    </PageLayout>
  );
}
