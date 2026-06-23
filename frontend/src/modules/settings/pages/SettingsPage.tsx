import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Save, Plus, Pencil } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { settingsApi } from "@/services/api/admin";
import { PosProfileSettings } from "@/modules/settings/components/PosProfileSettings";
import { ConnectionSettings } from "@/modules/settings/components/ConnectionSettings";
import { clearBrandingCache } from "@/documents/branding";
import type { BranchDetail, Company } from "@/types/models/admin";

export function SettingsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("company");
  const [company, setCompany] = useState<Partial<Company>>({});
  const [branches, setBranches] = useState<BranchDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [c, b] = await Promise.all([settingsApi.company(), settingsApi.branches()]);
      if (c.data) setCompany(c.data);
      setBranches(b.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const saveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      const res = await settingsApi.updateCompany(company);
      setCompany(res.data);
      clearBrandingCache();
      setSaved(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const branchColumns: Column<BranchDetail>[] = [
    { key: "name", header: "Branch", cell: (r) => <span className="font-medium">{r.name}</span> },
    { key: "code", header: "Code", cell: (r) => <span className="font-mono text-xs">{r.code}</span> },
    { key: "phone", header: "Phone", cell: (r) => r.phone || "—" },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <div className="flex gap-2">
          <Badge variant={r.is_active ? "success" : "secondary"}>
            {r.is_active ? "Active" : "Inactive"}
          </Badge>
          {r.is_default && <Badge variant="outline">Default</Badge>}
        </div>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (r) => (
        <div className="flex gap-1 justify-end">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/settings/branches/${r.id}/edit`)}>
            <Pencil className="h-4 w-4" />
          </Button>
          {!r.is_default && (
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await settingsApi.setDefaultBranch(r.id);
                load();
              }}
            >
              Set Default
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="Settings"
      description="Company profile, branches, and system configuration."
      breadcrumbs={["Home", "Settings"]}
    >
      <TabNav
        tabs={[
          { id: "company", label: "Company Profile" },
          { id: "branches", label: "Branches", count: branches.length },
          { id: "pos", label: "POS Profile" },
          { id: "connection", label: "Connection" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "company" && (
        <form onSubmit={saveCompany}>
          <FormSection title="Company Information" description="Legal and contact details for your organization.">
            <FormGrid>
              <FormField label="Company Name" required>
                <Input
                  required
                  value={company.name ?? ""}
                  onChange={(e) => setCompany({ ...company, name: e.target.value })}
                />
              </FormField>
              <FormField label="Legal Name">
                <Input
                  value={company.legal_name ?? ""}
                  onChange={(e) => setCompany({ ...company, legal_name: e.target.value })}
                />
              </FormField>
              <FormField label="Tax ID">
                <Input
                  value={company.tax_id ?? ""}
                  onChange={(e) => setCompany({ ...company, tax_id: e.target.value })}
                />
              </FormField>
              <FormField label="Email">
                <Input
                  type="email"
                  value={company.email ?? ""}
                  onChange={(e) => setCompany({ ...company, email: e.target.value })}
                />
              </FormField>
              <FormField label="Phone">
                <Input
                  value={company.phone ?? ""}
                  onChange={(e) => setCompany({ ...company, phone: e.target.value })}
                />
              </FormField>
              <FormField label="Address" className="md:col-span-2">
                <Input
                  value={company.address ?? ""}
                  onChange={(e) => setCompany({ ...company, address: e.target.value })}
                />
              </FormField>
            </FormGrid>
            <div className="mt-6 flex items-center justify-end gap-3">
              {saved && (
                <span className="text-sm text-emerald-600">Company profile saved.</span>
              )}
              <Button type="submit" loading={saving}>
                <Save className="h-4 w-4" />
                Save Company Profile
              </Button>
            </div>
          </FormSection>
        </form>
      )}

      {tab === "pos" && <PosProfileSettings />}

      {tab === "connection" && <ConnectionSettings />}

      {tab === "branches" && (
        <ContentSection
          title="Branch Locations"
          description="Manage store branches and default location"
          action={
            <Button asChild size="sm">
              <Link to="/settings/branches/new"><Plus className="h-4 w-4" /> Add Branch</Link>
            </Button>
          }
          noPadding
        >
          <DataTable
            embedded
            exportTitle="Branches"
            columns={branchColumns}
            data={branches}
            loading={loading}
            emptyMessage="No branches configured yet."
            defaultPageSize={10}
          />
        </ContentSection>
      )}
    </PageLayout>
  );
}
