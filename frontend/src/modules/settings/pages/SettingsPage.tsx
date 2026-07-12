import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Save, Plus, Pencil, Upload, X, Loader2, Trash2 } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";
import { TabNav } from "@/components/layout/TabNav";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormField, FormSection, FormGrid } from "@/components/forms/FormField";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { resolveMediaUrl } from "@/config/api";
import { settingsApi } from "@/services/api/admin";
import { PosProfileSettings } from "@/modules/settings/components/PosProfileSettings";
import { ConnectionSettings } from "@/modules/settings/components/ConnectionSettings";
import { clearBrandingCache } from "@/documents/branding";
import type { BranchDetail, Company } from "@/types/models/admin";
import { appDialog } from "@/components/feedback/AppDialog";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";

export function SettingsPage() {
  const navigate = useNavigate();
  const logoInputRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState("company");
  const [company, setCompany] = useState<Partial<Company>>({});
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [branches, setBranches] = useState<BranchDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    try {
      const [c, b] = await Promise.all([settingsApi.company(), settingsApi.branches()]);
      if (c.data) {
        setCompany(c.data);
        setLogoPreview(null);
      }
      setBranches(b.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  useAutoRefresh(() => load(false), { intervalMs: 60_000 });

  const displayLogo = logoPreview || resolveMediaUrl(company.logo) || null;

  const handleLogoFile = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      await appDialog.alert("Please select an image (JPEG, PNG, WebP, or GIF).", { tone: "danger" });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      await appDialog.alert("Logo must be 5 MB or smaller.", { tone: "danger" });
      return;
    }
    const local = URL.createObjectURL(file);
    setLogoPreview(local);
    setUploadingLogo(true);
    try {
      const res = await settingsApi.uploadLogo(file);
      const updated = await settingsApi.updateCompany({ ...company, logo: res.data.url });
      setCompany(updated.data);
      setLogoPreview(null);
      clearBrandingCache();
      window.dispatchEvent(new Event("mda:company-updated"));
    } catch (err) {
      setLogoPreview(null);
      await appDialog.alert(err instanceof Error ? err.message : "Logo upload failed", { tone: "danger" });
    } finally {
      setUploadingLogo(false);
    }
  };

  const clearLogo = async () => {
    setLogoPreview(null);
    if (logoInputRef.current) logoInputRef.current.value = "";
    try {
      const updated = await settingsApi.updateCompany({ ...company, logo: "" });
      setCompany(updated.data);
      clearBrandingCache();
      window.dispatchEvent(new Event("mda:company-updated"));
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not remove logo", { tone: "danger" });
    }
  };

  const saveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      const res = await settingsApi.updateCompany(company);
      setCompany(res.data);
      setLogoPreview(null);
      clearBrandingCache();
      window.dispatchEvent(new Event("mda:company-updated"));
      setSaved(true);
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Save failed", { tone: "danger" });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBranch = async (branch: BranchDetail) => {
    const companyLabel = branch.company_name ? ` (${branch.company_name})` : "";
    const ok = await appDialog.confirm(
      `Delete “${branch.name}”${companyLabel}? Users on this branch will be moved to another branch. This cannot be undone.`,
      { title: "Delete branch", confirmLabel: "Delete", tone: "danger" }
    );
    if (!ok) return;
    setDeletingId(branch.id);
    try {
      await settingsApi.deleteBranch(branch.id);
      await load();
    } catch (err) {
      await appDialog.alert(err instanceof Error ? err.message : "Could not delete branch.", { tone: "danger" });
    } finally {
      setDeletingId(null);
    }
  };

  const showCompanyCol = branches.some((b) => b.company_name && b.company_name !== company.name);

  const branchColumns: Column<BranchDetail>[] = [
    { key: "name", header: "Branch", cell: (r) => <span className="font-medium">{r.name}</span> },
    ...(showCompanyCol
      ? [{
          key: "company",
          header: "Shop / Company",
          cell: (r: BranchDetail) => (
            <span className="text-sm text-muted-foreground">{r.company_name || "—"}</span>
          ),
        } satisfies Column<BranchDetail>]
      : []),
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
                try {
                  await settingsApi.setDefaultBranch(r.id);
                  await load();
                } catch (err) {
                  await appDialog.alert(err instanceof Error ? err.message : "Could not set default.", { tone: "danger" });
                }
              }}
            >
              Set Default
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            loading={deletingId === r.id}
            title="Delete branch"
            onClick={() => handleDeleteBranch(r)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
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

      {tab === "company" && !loading && (
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
          </FormSection>

          <FormSection
            title="Company Logo"
            description="Shown in the sidebar, receipts, PDFs, and printed documents. JPEG, PNG, WebP, or GIF · max 5 MB."
          >
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl border border-border bg-muted/40">
                {displayLogo ? (
                  <img src={displayLogo} alt="Company logo" className="h-full w-full object-contain p-2" />
                ) : (
                  <span className="text-2xl font-bold text-muted-foreground">
                    {(company.name || "M").charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleLogoFile(file);
                  }}
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={uploadingLogo}
                    onClick={() => logoInputRef.current?.click()}
                  >
                    {uploadingLogo ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    {uploadingLogo ? "Uploading…" : "Upload logo"}
                  </Button>
                  {displayLogo && (
                    <Button type="button" variant="ghost" size="sm" onClick={clearLogo}>
                      <X className="h-4 w-4" />
                      Remove
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Logo updates immediately for the sidebar, receipts, and printed documents.
                </p>
              </div>
            </div>
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
          description="Each shop gets its own Main Branch when created. Delete unused duplicates here — you cannot delete a company’s only branch."
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
