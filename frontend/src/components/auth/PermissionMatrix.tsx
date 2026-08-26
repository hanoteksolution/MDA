import { useEffect, useMemo, useState } from "react";
import {
  Boxes,
  Building2,
  ChevronDown,
  ClipboardList,
  Dumbbell,
  FileText,
  Hotel,
  LayoutDashboard,
  Package,
  Pill,
  Search,
  Settings2,
  Shield,
  ShoppingCart,
  Store,
  Truck,
  Users,
  UtensilsCrossed,
  Wallet,
  Warehouse,
  Briefcase,
  Plane,
  Trash2,
  Landmark,
} from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

export interface PermissionItem {
  id: string;
  name: string;
  codename: string;
  module: string;
  description?: string;
}

interface PermissionMatrixProps {
  permissions: Record<string, PermissionItem[]>;
  selected: string[];
  onChange: (ids: string[]) => void;
  /** Permission IDs that come from the user's role (shown with a Role badge). */
  rolePermissionIds?: string[];
  disabled?: boolean;
  readOnly?: boolean;
  className?: string;
}

const MODULE_META: Record<
  string,
  { label: string; category: "operations" | "catalog" | "industry" | "admin"; icon: typeof Shield }
> = {
  dashboard: { label: "Dashboard", category: "operations", icon: LayoutDashboard },
  pos: { label: "Point of Sale", category: "operations", icon: Store },
  sales: { label: "Sales & Receipts", category: "operations", icon: ShoppingCart },
  purchases: { label: "Purchases", category: "operations", icon: Truck },
  finance: { label: "Finance", category: "operations", icon: Wallet },
  reports: { label: "Reports", category: "operations", icon: FileText },
  staff: { label: "Staff", category: "operations", icon: Users },
  products: { label: "Products", category: "catalog", icon: Package },
  inventory: { label: "Inventory", category: "catalog", icon: Warehouse },
  customers: { label: "Customers", category: "catalog", icon: Users },
  suppliers: { label: "Suppliers", category: "catalog", icon: Boxes },
  gym: { label: "Gym", category: "industry", icon: Dumbbell },
  restaurant: { label: "Restaurant", category: "industry", icon: UtensilsCrossed },
  hotel: { label: "Hotel", category: "industry", icon: Hotel },
  pharmacy: { label: "Pharmacy", category: "industry", icon: Pill },
  futsal: { label: "Futsal", category: "industry", icon: Landmark },
  property_management: { label: "Property", category: "industry", icon: Building2 },
  housing_rental: { label: "Housing", category: "industry", icon: Building2 },
  office_rental: { label: "Office", category: "industry", icon: Building2 },
  projects: { label: "Projects", category: "industry", icon: Briefcase },
  project_management: { label: "Projects", category: "industry", icon: Briefcase },
  travel: { label: "Travel", category: "industry", icon: Plane },
  travel_agency: { label: "Travel", category: "industry", icon: Plane },
  users: { label: "Users", category: "admin", icon: Users },
  roles: { label: "Roles", category: "admin", icon: Shield },
  branches: { label: "Branches", category: "admin", icon: Building2 },
  settings: { label: "Settings", category: "admin", icon: Settings2 },
  audit: { label: "Audit", category: "admin", icon: ClipboardList },
  trash: { label: "Trash", category: "admin", icon: Trash2 },
  platform: { label: "Platform", category: "admin", icon: Shield },
};

const CATEGORY_ORDER = ["operations", "catalog", "industry", "admin"] as const;
const CATEGORY_LABELS: Record<(typeof CATEGORY_ORDER)[number], string> = {
  operations: "Operations",
  catalog: "Catalog & Partners",
  industry: "Industry modules",
  admin: "Administration",
};

/** Modules that unlock the Administration workspace / nav item. */
const ADMINISTRATION_NAV_MODULES = new Set(["users", "roles"]);
const ADMIN_MODULE_ORDER = ["users", "roles", "branches", "settings", "audit", "trash", "platform"];

function metaFor(module: string) {
  return (
    MODULE_META[module] || {
      label: module.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      category: "operations" as const,
      icon: Shield,
    }
  );
}

function sortAdminModules(modules: string[]) {
  return [...modules].sort((a, b) => {
    const ai = ADMIN_MODULE_ORDER.indexOf(a);
    const bi = ADMIN_MODULE_ORDER.indexOf(b);
    const av = ai === -1 ? 999 : ai;
    const bv = bi === -1 ? 999 : bi;
    if (av !== bv) return av - bv;
    return a.localeCompare(b);
  });
}

export function PermissionMatrix({
  permissions,
  selected,
  onChange,
  rolePermissionIds = [],
  disabled,
  readOnly,
  className,
}: PermissionMatrixProps) {
  const [query, setQuery] = useState("");
  const [openModules, setOpenModules] = useState<Record<string, boolean>>({});
  const roleSet = useMemo(() => new Set(rolePermissionIds.map(String)), [rolePermissionIds]);
  const selectedSet = useMemo(() => new Set(selected.map(String)), [selected]);

  const modules = useMemo(() => Object.keys(permissions).sort(), [permissions]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out: Record<string, PermissionItem[]> = {};
    for (const module of modules) {
      const perms = permissions[module] ?? [];
      const next = q
        ? perms.filter(
            (p) =>
              p.name.toLowerCase().includes(q) ||
              p.codename.toLowerCase().includes(q) ||
              module.toLowerCase().includes(q) ||
              metaFor(module).label.toLowerCase().includes(q)
          )
        : perms;
      if (next.length) out[module] = next;
    }
    return out;
  }, [modules, permissions, query]);

  const grouped = useMemo(() => {
    const buckets: Record<string, string[]> = {
      operations: [],
      catalog: [],
      industry: [],
      admin: [],
    };
    for (const module of Object.keys(filtered).sort()) {
      buckets[metaFor(module).category].push(module);
    }
    buckets.admin = sortAdminModules(buckets.admin);
    return buckets;
  }, [filtered]);

  const visibleIds = useMemo(
    () => Object.values(filtered).flat().map((p) => p.id),
    [filtered]
  );
  const totalSelected = selected.length;
  const visibleSelected = visibleIds.filter((id) => selected.includes(id)).length;

  const adminNavIds = useMemo(() => {
    return (grouped.admin || [])
      .filter((m) => ADMINISTRATION_NAV_MODULES.has(m))
      .flatMap((m) => (filtered[m] || permissions[m] || []).map((p) => p.id));
  }, [grouped.admin, filtered, permissions]);

  const adminNavSelected = adminNavIds.filter((id) => selectedSet.has(String(id))).length;
  const adminHidden = adminNavIds.length > 0 && adminNavSelected === 0;

  // Keep revoked role permissions visible so they can be granted again.
  useEffect(() => {
    const next: Record<string, boolean> = {};
    for (const [module, perms] of Object.entries(filtered)) {
      const hasRevoked = perms.some(
        (p) => roleSet.has(String(p.id)) && !selectedSet.has(String(p.id))
      );
      if (hasRevoked || (ADMINISTRATION_NAV_MODULES.has(module) && adminHidden)) {
        next[module] = true;
      }
    }
    if (!Object.keys(next).length) return;
    setOpenModules((prev) => ({ ...next, ...prev }));
  }, [filtered, roleSet, selectedSet, adminHidden]);

  const isOpen = (module: string) => {
    if (openModules[module] !== undefined) return openModules[module];
    const perms = filtered[module] || [];
    const hasSel = perms.some((p) => selectedSet.has(String(p.id)));
    const hasRevoked = perms.some(
      (p) => roleSet.has(String(p.id)) && !selectedSet.has(String(p.id))
    );
    return hasSel || hasRevoked || Boolean(query.trim());
  };

  const toggleOpen = (module: string) => {
    setOpenModules((prev) => ({ ...prev, [module]: !isOpen(module) }));
  };

  const toggle = (id: string) => {
    if (readOnly || disabled) return;
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  const toggleModule = (module: string, checked: boolean) => {
    if (readOnly || disabled) return;
    const ids = (filtered[module] || permissions[module] || []).map((p) => p.id);
    if (checked) onChange([...new Set([...selected, ...ids])]);
    else onChange(selected.filter((id) => !ids.includes(id)));
  };

  const selectVisible = () => {
    if (readOnly || disabled) return;
    onChange([...new Set([...selected, ...visibleIds])]);
  };

  const clearVisible = () => {
    if (readOnly || disabled) return;
    onChange(selected.filter((id) => !visibleIds.includes(id)));
  };

  const categoryIds = (category: (typeof CATEGORY_ORDER)[number]) => {
    const mods = grouped[category] || [];
    return mods.flatMap((m) => (filtered[m] || []).map((p) => p.id));
  };

  const setCategoryEnabled = (category: (typeof CATEGORY_ORDER)[number], enabled: boolean) => {
    if (readOnly || disabled) return;
    const ids = categoryIds(category);
    if (!ids.length) return;
    if (enabled) onChange([...new Set([...selected, ...ids])]);
    else onChange(selected.filter((id) => !ids.includes(id)));
  };

  /** Revoke only the permissions that gate the Administration workspace (users + roles). */
  const hideAdministrationModule = () => {
    if (readOnly || disabled) return;
    if (!adminNavIds.length) return;
    onChange(selected.filter((id) => !adminNavIds.includes(id)));
    setOpenModules((prev) => ({
      ...prev,
      users: true,
      roles: true,
    }));
  };

  /** Restore Users + Roles so the Administration workspace returns. */
  const showAdministrationModule = () => {
    if (readOnly || disabled) return;
    if (!adminNavIds.length) return;
    onChange([...new Set([...selected, ...adminNavIds])]);
    setOpenModules((prev) => ({
      ...prev,
      users: true,
      roles: true,
    }));
  };

  if (!modules.length) {
    return (
      <div className={cn("rounded-2xl border border-dashed border-border/80 bg-muted/20 px-5 py-10 text-center", className)}>
        <Shield className="mx-auto h-8 w-8 text-muted-foreground/50" />
        <p className="mt-3 text-sm font-medium">No permissions for this shop</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Enable modules on the shop to unlock related permission groups.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex flex-col gap-3 rounded-2xl border border-border/70 bg-gradient-to-br from-card via-card to-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-tight">Effective access</p>
          <p className="text-xs text-muted-foreground">
            Checked = allowed. Uncheck a role permission to revoke it for this user.
            {` · ${totalSelected} selected`}
            {query.trim() ? ` · ${visibleSelected} match filter` : ` · ${modules.length} modules`}
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-2 py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-foreground/70" /> Role
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-2 py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Extra grant
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-2 py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-destructive/80" /> Revoked
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[180px] flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search permissions…"
              className="h-9 rounded-xl pl-9"
            />
          </div>
          {!readOnly && (
            <>
              <Button type="button" size="sm" variant="secondary" onClick={selectVisible} disabled={disabled || !visibleIds.length}>
                Select visible
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={clearVisible} disabled={disabled || !visibleSelected}>
                Clear
              </Button>
            </>
          )}
        </div>
      </div>

      {CATEGORY_ORDER.map((category) => {
        const catModules = grouped[category] || [];
        if (!catModules.length) return null;
        const catIds = categoryIds(category);
        const catSelected = catIds.filter((id) => selected.includes(id)).length;
        return (
          <div key={category} className="space-y-2.5">
            <div className="flex flex-wrap items-center gap-2 px-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                {CATEGORY_LABELS[category]}
              </p>
              <div className="h-px min-w-[1rem] flex-1 bg-border/60" />
              <Badge variant="secondary" className="rounded-full text-[10px]">
                {catSelected}/{catIds.length}
              </Badge>
              {!readOnly && (
                <div className="flex flex-wrap gap-1.5">
                  {category === "admin" &&
                    (adminHidden ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        className="h-7 rounded-lg text-[11px]"
                        disabled={disabled || !adminNavIds.length}
                        onClick={showAdministrationModule}
                      >
                        Show Administration
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        className="h-7 rounded-lg text-[11px]"
                        disabled={disabled || adminNavSelected === 0}
                        onClick={hideAdministrationModule}
                      >
                        Hide Administration
                      </Button>
                    ))}
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 rounded-lg text-[11px]"
                    disabled={disabled || catSelected === catIds.length}
                    onClick={() => setCategoryEnabled(category, true)}
                  >
                    Allow all
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 rounded-lg text-[11px]"
                    disabled={disabled || catSelected === 0}
                    onClick={() => setCategoryEnabled(category, false)}
                  >
                    Revoke all
                  </Button>
                </div>
              )}
            </div>
            {category === "admin" && !readOnly && (
              <p className="px-1 text-[11px] text-muted-foreground">
                {adminHidden
                  ? "Administration is hidden. Use “Show Administration” (or check Users & Roles) to grant it back, then save."
                  : "“Hide Administration” removes Users & Roles access so the Administration workspace disappears from their menu. Use “Revoke all” to clear settings, branches, and audit as well."}
              </p>
            )}
            <div className="space-y-2">
              {catModules.map((module) => {
                const perms = filtered[module] ?? [];
                const meta = metaFor(module);
                const Icon = meta.icon;
                const moduleIds = perms.map((p) => p.id);
                const selectedCount = moduleIds.filter((id) => selected.includes(id)).length;
                const revokedCount = perms.filter(
                  (p) => roleSet.has(String(p.id)) && !selectedSet.has(String(p.id))
                ).length;
                const allSelected = selectedCount === perms.length && perms.length > 0;
                const someSelected = selectedCount > 0 && !allSelected;
                const open = isOpen(module);
                const pct = perms.length ? Math.round((selectedCount / perms.length) * 100) : 0;

                return (
                  <div
                    key={module}
                    className={cn(
                      "overflow-hidden rounded-2xl border border-border/70 bg-card/80 shadow-sm transition-shadow",
                      open && "shadow-md ring-1 ring-border/40",
                      revokedCount > 0 && selectedCount === 0 && "border-destructive/30"
                    )}
                  >
                    <div className="flex items-center gap-2 px-3 py-3 sm:px-4">
                      {!readOnly && (
                        <Checkbox
                          checked={allSelected ? true : someSelected ? "indeterminate" : false}
                          onCheckedChange={(v) => toggleModule(module, !!v)}
                          disabled={disabled}
                          aria-label={`Select all ${meta.label}`}
                        />
                      )}
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 items-center gap-3 text-left"
                        onClick={() => toggleOpen(module)}
                      >
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/60 text-foreground/80">
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold tracking-tight">{meta.label}</span>
                            <Badge
                              variant={selectedCount ? "default" : "secondary"}
                              className="rounded-full px-2 py-0 text-[10px] font-medium"
                            >
                              {selectedCount}/{perms.length}
                            </Badge>
                            {revokedCount > 0 && (
                              <Badge variant="destructive" className="rounded-full px-2 py-0 text-[10px] font-medium">
                                {revokedCount} revoked
                              </Badge>
                            )}
                          </span>
                          <span className="mt-1.5 block h-1 overflow-hidden rounded-full bg-muted">
                            <span
                              className="block h-full rounded-full bg-foreground/70 transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </span>
                        </span>
                        <ChevronDown
                          className={cn(
                            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
                            open && "rotate-180"
                          )}
                        />
                      </button>
                    </div>

                    {open && (
                      <div className="border-t border-border/50 bg-muted/15 px-3 pb-3 pt-2 sm:px-4">
                        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                          {perms.map((perm) => {
                            const active = selected.includes(perm.id);
                            const fromRole = roleSet.has(String(perm.id));
                            const revoked = fromRole && !active;
                            const extra = active && !fromRole;
                            if (readOnly) {
                              return (
                                <div
                                  key={perm.id}
                                  className="rounded-xl border border-transparent bg-background/60 px-3 py-2.5"
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <p className="text-sm font-medium leading-snug">{perm.name}</p>
                                    {fromRole && (
                                      <Badge variant="secondary" className="shrink-0 rounded-full text-[9px]">
                                        Role
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">{perm.codename}</p>
                                </div>
                              );
                            }
                            return (
                              <label
                                key={perm.id}
                                className={cn(
                                  "flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 transition-colors",
                                  active
                                    ? "border-border/80 bg-background"
                                    : revoked
                                      ? "border-destructive/25 bg-destructive/5"
                                      : "border-transparent bg-background/40 hover:bg-background/70"
                                )}
                              >
                                <Checkbox
                                  checked={active}
                                  onCheckedChange={() => toggle(perm.id)}
                                  disabled={disabled}
                                  className="mt-0.5"
                                />
                                <span className="min-w-0 flex-1">
                                  <span className="flex flex-wrap items-center gap-1.5">
                                    <span className="text-sm font-medium leading-snug">{perm.name}</span>
                                    {fromRole && !revoked ? (
                                      <Badge variant="secondary" className="rounded-full text-[9px]">
                                        Role
                                      </Badge>
                                    ) : null}
                                    {extra ? (
                                      <Badge className="rounded-full bg-emerald-600 text-[9px] hover:bg-emerald-600">
                                        Extra
                                      </Badge>
                                    ) : null}
                                    {revoked ? (
                                      <Badge variant="destructive" className="rounded-full text-[9px]">
                                        Revoked
                                      </Badge>
                                    ) : null}
                                  </span>
                                  <span className="mt-0.5 block font-mono text-[10px] text-muted-foreground">
                                    {perm.codename}
                                  </span>
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
