import { useEffect, useMemo, useState } from "react";
import { FlaskConical, Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormField, FormGrid, FormSection } from "@/components/forms/FormField";
import { PlatformCloudNotice } from "@/components/platform/PlatformCloudNotice";
import {
  platformApi,
  type PlatformDemoTenantRow,
  type PlatformShopGroupRow,
  type PlatformTenantRow,
} from "@/services/api/platform";
import { appDialog } from "@/components/feedback/AppDialog";
import { cn } from "@/utils/cn";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  ACTIVE: "default",
  EXPIRED: "destructive",
  SUSPENDED: "secondary",
  CONVERTED: "outline",
};

const SEED_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline" | "warning"> = {
  none: "outline",
  pending: "warning",
  running: "warning",
  done: "default",
  failed: "destructive",
};

/** Industry modules shown in the multi-select (labels for UI). */
const INDUSTRY_OPTIONS: { code: string; label: string; module: string }[] = [
  { code: "gym", label: "Gym", module: "gym" },
  { code: "pharmacy", label: "Pharmacy", module: "pharmacy" },
  { code: "restaurant", label: "Cafeteria / Restaurant", module: "restaurant" },
  { code: "hotel", label: "Hotel", module: "hotel" },
  { code: "property", label: "Property", module: "property_management" },
  { code: "futsal", label: "Futsal", module: "futsal" },
  { code: "retail", label: "Retail", module: "pos" },
  { code: "project", label: "Construction / Project", module: "project_management" },
  { code: "travel", label: "Travel", module: "travel_agency" },
];

const SHARED_ENGINES = ["pos", "inventory", "sales"] as const;

const EMPTY_FORM = {
  linkMode: "new" as "new" | "existing",
  name: "",
  duration_days: "14",
  contact_email: "",
  shop_group_id: "",
  source_tenant_id: "",
  industries: ["gym"] as string[],
  migrate_seed: false,
};

function buildModules(industries: string[]): string[] {
  const set = new Set<string>();
  for (const code of industries) {
    const opt = INDUSTRY_OPTIONS.find((o) => o.code === code);
    if (!opt) continue;
    if (opt.code === "retail") {
      SHARED_ENGINES.forEach((m) => set.add(m));
      continue;
    }
    set.add(opt.module);
    if (opt.code === "property") {
      set.add("housing_rental");
      set.add("office_rental");
    }
  }
  if (industries.some((c) => c !== "project" && c !== "travel")) {
    SHARED_ENGINES.forEach((m) => set.add(m));
  }
  return Array.from(set);
}

function primaryBusinessType(industries: string[]): string {
  const first = industries[0];
  if (!first) return "retail";
  if (first === "project") return "retail";
  if (first === "travel") return "retail";
  return first;
}

function industriesFromModules(modules: string[]): string[] {
  const set = new Set(modules.map((m) => m.toLowerCase()));
  return INDUSTRY_OPTIONS.filter((opt) => {
    if (opt.code === "retail") return set.has("pos") && !set.has("gym") && !set.has("restaurant");
    if (opt.code === "property") return set.has("property_management");
    return set.has(opt.module);
  }).map((o) => o.code);
}

function demoHttpsUrl(row: PlatformDemoTenantRow): string | null {
  const domain = row.primary_domain?.domain || (row.slug ? `${row.slug}.erp.safaritechno.com` : null);
  return domain ? `https://${domain}` : null;
}

export function PlatformDemosPage() {
  const [rows, setRows] = useState<PlatformDemoTenantRow[]>([]);
  const [shops, setShops] = useState<PlatformTenantRow[]>([]);
  const [groups, setGroups] = useState<PlatformShopGroupRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [modulesTarget, setModulesTarget] = useState<PlatformDemoTenantRow | null>(null);
  const [modulesPick, setModulesPick] = useState<string[]>([]);
  const [modulesBusy, setModulesBusy] = useState(false);
  const [modulesSeed, setModulesSeed] = useState(false);

  const load = (opts?: { quiet?: boolean }) => {
    if (!opts?.quiet) setLoading(true);
    platformApi
      .demoTenants()
      .then((res) => setRows(res.data?.items || []))
      .catch(() => setRows([]))
      .finally(() => {
        if (!opts?.quiet) setLoading(false);
      });
  };

  useEffect(() => {
    load();
    platformApi
      .tenants()
      .then((res) => setShops(Array.isArray(res.data) ? res.data : []))
      .catch(() => setShops([]));
    platformApi
      .shopGroups()
      .then((res) => setGroups(Array.isArray(res.data) ? res.data : []))
      .catch(() => setGroups([]));
  }, []);

  const seeding = useMemo(
    () => rows.some((r) => r.seed_status === "pending" || r.seed_status === "running"),
    [rows]
  );

  useEffect(() => {
    if (!seeding) return;
    const id = window.setInterval(() => load({ quiet: true }), 4000);
    return () => window.clearInterval(id);
  }, [seeding]);

  const availableShops = useMemo(
    () => shops.filter((s) => !(s as PlatformTenantRow & { is_demo?: boolean }).is_demo),
    [shops]
  );

  const toggleIndustry = (code: string) => {
    setForm((f) => {
      const has = f.industries.includes(code);
      const industries = has ? f.industries.filter((c) => c !== code) : [...f.industries, code];
      return { ...f, industries: industries.length ? industries : f.industries };
    });
  };

  const openModulesEditor = (row: PlatformDemoTenantRow) => {
    setModulesTarget(row);
    setModulesPick(industriesFromModules(row.modules || []));
    setModulesSeed(false);
  };

  const toggleModulesPick = (code: string) => {
    setModulesPick((prev) => {
      const has = prev.includes(code);
      const next = has ? prev.filter((c) => c !== code) : [...prev, code];
      return next.length ? next : prev;
    });
  };

  const saveModules = async () => {
    if (!modulesTarget) return;
    if (!modulesPick.length) {
      await appDialog.alert("Select at least one module.", { title: "Modules", tone: "danger" });
      return;
    }
    setModulesBusy(true);
    try {
      await platformApi.demoTenantAction(modulesTarget.id, "modules", {
        modules: buildModules(modulesPick),
        merge: true,
        seed_new: modulesSeed,
      });
      setModulesTarget(null);
      load();
    } catch (e: unknown) {
      await appDialog.alert(e instanceof Error ? e.message : "Could not update modules.", {
        title: "Modules failed",
        tone: "danger",
      });
    } finally {
      setModulesBusy(false);
    }
  };

  const create = async () => {
    setError(null);
    if (form.linkMode === "new" && !form.name.trim()) {
      setError("Name is required for a new demo shop.");
      return;
    }
    if (form.linkMode === "existing" && !form.source_tenant_id) {
      setError("Select an existing shop to connect.");
      return;
    }
    if (!form.industries.length) {
      setError("Select at least one module / business type.");
      return;
    }
    setCreating(true);
    try {
      const modules = buildModules(form.industries);
      const business_type_code = primaryBusinessType(form.industries);
      const selectedShop = availableShops.find((s) => s.id === form.source_tenant_id);
      await platformApi.createDemoTenant({
        name:
          form.linkMode === "existing"
            ? form.name.trim() || selectedShop?.name || undefined
            : form.name.trim(),
        business_type_code,
        modules,
        duration_days: Number(form.duration_days) || 14,
        contact_email: form.contact_email || undefined,
        shop_group_id:
          form.linkMode === "new" && form.shop_group_id ? form.shop_group_id : undefined,
        source_tenant_id: form.linkMode === "existing" ? form.source_tenant_id : undefined,
        generate_data: form.migrate_seed,
        seed_async: form.migrate_seed,
      });
      setForm(EMPTY_FORM);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create demo.");
    } finally {
      setCreating(false);
    }
  };

  const act = async (id: string, action: "extend" | "suspend" | "convert" | "expire" | "seed") => {
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
      } else if (action === "seed") {
        await platformApi.demoTenantAction(id, "seed", { seed_async: true });
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
      cell: (r) => {
        const url = demoHttpsUrl(r);
        return (
          <div>
            <Link to={`/platform/shops/${r.id}`} className="font-medium text-primary hover:underline">
              {r.name}
            </Link>
            <p className="text-xs text-muted-foreground">{r.slug}</p>
            {url ? (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-primary hover:underline"
              >
                {url.replace(/^https:\/\//, "")}
              </a>
            ) : null}
            {r.shop_group_name ? (
              <p className="text-xs text-muted-foreground">Group: {r.shop_group_name}</p>
            ) : null}
          </div>
        );
      },
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
        <span className="text-xs text-muted-foreground">{(r.modules || []).slice(0, 8).join(", ")}</span>
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
      key: "seed",
      header: "Seed",
      cell: (r) => {
        const status = r.seed_status || "none";
        if (status === "none") return <span className="text-xs text-muted-foreground">—</span>;
        return <Badge variant={SEED_VARIANT[status] || "secondary"}>{status}</Badge>;
      },
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
            <Button size="sm" variant="outline" onClick={() => openModulesEditor(r)}>
              Modules
            </Button>
            <Button size="sm" variant="outline" onClick={() => act(r.id, "extend")}>
              Extend
            </Button>
            <Button size="sm" variant="outline" onClick={() => act(r.id, "suspend")}>
              Suspend
            </Button>
            {(r.seed_status === "none" || r.seed_status === "failed") && (
              <Button size="sm" variant="outline" onClick={() => act(r.id, "seed")}>
                Seed
              </Button>
            )}
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
      description="Create multi-module trial shops, add modules later, and open demos over HTTPS."
      actions={
        <Button variant="outline" size="sm" onClick={() => load()} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <PlatformCloudNotice />

      <FormSection
        title="New demo"
        description="Select modules, link a shop or group, and optionally migrate seed data."
      >
        <FormGrid>
          <FormField label="Link mode" className="md:col-span-2 xl:col-span-3">
            <div className="flex flex-wrap gap-4 pt-1">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="linkMode"
                  checked={form.linkMode === "new"}
                  onChange={() => setForm((f) => ({ ...f, linkMode: "new", source_tenant_id: "" }))}
                />
                New demo shop
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name="linkMode"
                  checked={form.linkMode === "existing"}
                  onChange={() => setForm((f) => ({ ...f, linkMode: "existing", shop_group_id: "" }))}
                />
                Use existing shop
              </label>
            </div>
          </FormField>

          {form.linkMode === "existing" ? (
            <FormField label="Existing shop" className="md:col-span-2">
              <Select
                value={form.source_tenant_id || undefined}
                onValueChange={(v) => setForm((f) => ({ ...f, source_tenant_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select shop tenant…" />
                </SelectTrigger>
                <SelectContent>
                  {availableShops.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name} ({s.slug})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          ) : (
            <FormField label="Shop group (optional)">
              <Select
                value={form.shop_group_id || "__none__"}
                onValueChange={(v) =>
                  setForm((f) => ({ ...f, shop_group_id: v === "__none__" ? "" : v }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {groups.map((g) => (
                    <SelectItem key={g.id} value={g.id}>
                      {g.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          )}

          <FormField label={form.linkMode === "existing" ? "Display name (optional)" : "Name"}>
            <Input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Demo Gym Co"
            />
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

          <FormField label="Modules / business types" className="md:col-span-2 xl:col-span-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1">
              {INDUSTRY_OPTIONS.map((opt) => {
                const checked = form.industries.includes(opt.code);
                return (
                  <label
                    key={opt.code}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm cursor-pointer",
                      checked ? "border-primary bg-primary/5" : "border-border"
                    )}
                  >
                    <Checkbox checked={checked} onCheckedChange={() => toggleIndustry(opt.code)} />
                    {opt.label}
                  </label>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Enabled modules: {buildModules(form.industries).join(", ") || "—"}
            </p>
          </FormField>

          <FormField label="Migrate seed data" className="md:col-span-2 xl:col-span-3">
            <label className="flex items-center gap-3 cursor-pointer pt-1">
              <Checkbox
                checked={form.migrate_seed}
                onCheckedChange={(v) => setForm((f) => ({ ...f, migrate_seed: !!v }))}
              />
              <span className="text-sm">
                Seed sample data for selected modules in the background after create
              </span>
            </label>
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

      {modulesTarget ? (
        <FormSection
          title={`Add modules — ${modulesTarget.name}`}
          description="Enable extra industry modules on this demo without recreating it. Existing modules stay on."
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {INDUSTRY_OPTIONS.map((opt) => {
              const checked = modulesPick.includes(opt.code);
              return (
                <label
                  key={opt.code}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm cursor-pointer",
                    checked ? "border-primary bg-primary/5" : "border-border"
                  )}
                >
                  <Checkbox checked={checked} onCheckedChange={() => toggleModulesPick(opt.code)} />
                  {opt.label}
                </label>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Will enable: {buildModules(modulesPick).join(", ") || "—"}
          </p>
          <label className="mt-3 flex items-center gap-3 cursor-pointer">
            <Checkbox checked={modulesSeed} onCheckedChange={(v) => setModulesSeed(!!v)} />
            <span className="text-sm">Seed sample data after saving</span>
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={saveModules} disabled={modulesBusy}>
              {modulesBusy ? "Saving…" : "Save modules"}
            </Button>
            <Button variant="outline" onClick={() => setModulesTarget(null)} disabled={modulesBusy}>
              Cancel
            </Button>
            <Button variant="ghost" asChild>
              <Link to={`/platform/shops/${modulesTarget.id}`}>Open shop detail</Link>
            </Button>
          </div>
        </FormSection>
      ) : null}

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
