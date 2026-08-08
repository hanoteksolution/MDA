import { useEffect, useState } from "react";
import { FlaskConical, Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import { platformApi, type PlatformDemoTenantRow } from "@/services/api/platform";
import { appDialog } from "@/components/feedback/AppDialog";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  ACTIVE: "default",
  EXPIRED: "destructive",
  SUSPENDED: "secondary",
  CONVERTED: "outline",
};

export function PlatformDemosPage() {
  const [rows, setRows] = useState<PlatformDemoTenantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    business_type_code: "gym",
    preset_code: "gym",
    duration_days: "14",
    contact_email: "",
  });

  const load = () => {
    setLoading(true);
    platformApi
      .demoTenants()
      .then((res) => setRows(res.data?.items || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setError(null);
    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }
    setCreating(true);
    try {
      await platformApi.createDemoTenant({
        name: form.name.trim(),
        business_type_code: form.business_type_code,
        preset_code: form.preset_code || form.business_type_code,
        duration_days: Number(form.duration_days) || 14,
        contact_email: form.contact_email,
        generate_data: true,
      });
      setForm({
        name: "",
        business_type_code: "gym",
        preset_code: "gym",
        duration_days: "14",
        contact_email: "",
      });
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create demo.");
    } finally {
      setCreating(false);
    }
  };

  const act = async (id: string, action: "extend" | "suspend" | "convert" | "expire") => {
    try {
      if (action === "extend") {
        await platformApi.demoTenantAction(id, "extend", { days: 14 });
      } else if (action === "convert") {
        const ok = await appDialog.confirm(
          "This marks the demo as a paying customer and keeps existing data.",
          { title: "Convert demo?", confirmLabel: "Convert" }
        );
        if (!ok) return;
        await platformApi.demoTenantAction(id, "convert", { plan_code: "starter" });
      } else {
        await platformApi.demoTenantAction(id, action);
      }
      load();
    } catch (e: unknown) {
      await appDialog.alert(e instanceof Error ? e.message : "Request failed.", {
        title: "Action failed",
        tone: "danger",
      });
    }
  };

  const columns: Column<PlatformDemoTenantRow>[] = [
    {
      key: "name",
      header: "Demo",
      cell: (r) => (
        <div>
          <Link to={`/platform/shops/${r.id}`} className="font-medium text-primary hover:underline">
            {r.name}
          </Link>
          <p className="text-xs text-muted-foreground">{r.slug}</p>
        </div>
      ),
    },
    {
      key: "type",
      header: "Type",
      cell: (r) => r.business_type_code || "—",
    },
    {
      key: "modules",
      header: "Modules",
      cell: (r) => (
        <span className="text-xs text-muted-foreground">{(r.modules || []).slice(0, 5).join(", ")}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (r) => (
        <Badge variant={STATUS_VARIANT[r.demo_status || ""] || "secondary"}>
          {r.demo_status || "—"}
        </Badge>
      ),
    },
    {
      key: "expires",
      header: "Expires",
      cell: (r) =>
        r.demo_expires_at ? new Date(r.demo_expires_at).toLocaleDateString() : "—",
    },
    {
      key: "actions",
      header: "",
      cell: (r) =>
        r.demo_status === "CONVERTED" ? null : (
          <div className="flex flex-wrap gap-1 justify-end">
            <Button size="sm" variant="outline" onClick={() => act(r.id, "extend")}>
              Extend
            </Button>
            <Button size="sm" variant="outline" onClick={() => act(r.id, "suspend")}>
              Suspend
            </Button>
            <Button size="sm" variant="default" onClick={() => act(r.id, "convert")}>
              Convert
            </Button>
          </div>
        ),
    },
  ];

  return (
    <PageLayout
      title="Demo Accounts"
      description="Create trial tenants with module presets, expiration, and convert-to-customer."
      actions={
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <PlatformCloudNotice />

      <FormSection title="New demo" description="Uses the same provision spine as real shops.">
        <FormGrid>
          <FormField label="Name">
            <Input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Demo Gym Co"
            />
          </FormField>
          <FormField label="Business type">
            <Select
              value={
                form.preset_code === "property_residential" ||
                form.preset_code === "property_commercial"
                  ? form.preset_code
                  : form.business_type_code
              }
              onValueChange={(v) => {
                if (v === "property_residential" || v === "property_commercial") {
                  setForm((f) => ({
                    ...f,
                    business_type_code: "property",
                    preset_code: v,
                  }));
                  return;
                }
                setForm((f) => ({ ...f, business_type_code: v, preset_code: v }));
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gym">Gym</SelectItem>
                <SelectItem value="pharmacy">Pharmacy</SelectItem>
                <SelectItem value="retail">Retail</SelectItem>
                <SelectItem value="restaurant">Restaurant</SelectItem>
                <SelectItem value="hotel">Hotel</SelectItem>
                <SelectItem value="property">Property</SelectItem>
                <SelectItem value="property_residential">Property + Housing</SelectItem>
                <SelectItem value="property_commercial">Property + Office</SelectItem>
                <SelectItem value="futsal">Futsal</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Duration (days)">
            <Select
              value={form.duration_days}
              onValueChange={(v) => setForm((f) => ({ ...f, duration_days: v }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7</SelectItem>
                <SelectItem value="14">14</SelectItem>
                <SelectItem value="30">30</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Contact email">
            <Input
              type="email"
              value={form.contact_email}
              onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
            />
          </FormField>
        </FormGrid>
        {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
        <div className="mt-4">
          <Button onClick={create} disabled={creating}>
            <Plus className="h-4 w-4 mr-1.5" />
            {creating ? "Creating…" : "Create demo"}
          </Button>
        </div>
      </FormSection>

      <div className="mt-6">
        {loading && rows.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <FlaskConical className="h-4 w-4" />
            Loading demos…
          </div>
        ) : (
          <DataTable columns={columns} data={rows} emptyMessage="No demo tenants yet." />
        )}
      </div>
    </PageLayout>
  );
}
