import { useMemo } from "react";
import { Checkbox } from "@/components/ui/checkbox";
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
  disabled?: boolean;
  readOnly?: boolean;
  className?: string;
}

const MODULE_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  pos: "Point of Sale",
  products: "Products",
  inventory: "Inventory",
  purchases: "Purchases",
  sales: "Sales",
  customers: "Customers",
  suppliers: "Suppliers",
  finance: "Finance",
  reports: "Reports",
  users: "Users",
  roles: "Roles",
  branches: "Branches",
  settings: "Settings",
  audit: "Audit",
  platform: "Platform",
  staff: "Staff",
  futsal: "Futsal",
};

export function PermissionMatrix({
  permissions,
  selected,
  onChange,
  disabled,
  readOnly,
  className,
}: PermissionMatrixProps) {
  const modules = useMemo(
    () => Object.keys(permissions).sort(),
    [permissions]
  );

  const toggle = (id: string) => {
    if (readOnly || disabled) return;
    onChange(
      selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]
    );
  };

  const toggleModule = (module: string, checked: boolean) => {
    if (readOnly || disabled) return;
    const ids = permissions[module].map((p) => p.id);
    if (checked) {
      onChange([...new Set([...selected, ...ids])]);
    } else {
      onChange(selected.filter((id) => !ids.includes(id)));
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {modules.map((module) => {
        const perms = permissions[module] ?? [];
        const moduleIds = perms.map((p) => p.id);
        const selectedCount = moduleIds.filter((id) => selected.includes(id)).length;
        const allSelected = selectedCount === perms.length && perms.length > 0;
        const someSelected = selectedCount > 0 && !allSelected;

        return (
          <div key={module} className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-3">
              <div className="flex items-center gap-3">
                {!readOnly && (
                  <Checkbox
                    checked={allSelected ? true : someSelected ? "indeterminate" : false}
                    onCheckedChange={(v) => toggleModule(module, !!v)}
                    disabled={disabled}
                  />
                )}
                <div>
                  <p className="text-sm font-semibold">
                    {MODULE_LABELS[module] ?? module}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {selectedCount}/{perms.length} permissions
                  </p>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-1 p-3 sm:grid-cols-2">
              {perms.map((perm) =>
                readOnly ? (
                  <div key={perm.id} className="rounded-lg px-3 py-2 bg-muted/20">
                    <p className="text-sm font-medium leading-snug">{perm.name}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">{perm.codename}</p>
                  </div>
                ) : (
                  <label
                    key={perm.id}
                    className={cn(
                      "flex items-start gap-3 rounded-lg px-3 py-2 transition-colors",
                      !disabled && "cursor-pointer hover:bg-muted/50",
                      selected.includes(perm.id) && "bg-primary/5"
                    )}
                  >
                    <Checkbox
                      checked={selected.includes(perm.id)}
                      onCheckedChange={() => toggle(perm.id)}
                      disabled={disabled}
                      className="mt-0.5"
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium leading-snug">{perm.name}</p>
                      <p className="font-mono text-[10px] text-muted-foreground">{perm.codename}</p>
                    </div>
                  </label>
                )
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
