import { useEffect } from "react";
import { Building2, Layers } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { appDialog } from "@/components/feedback/AppDialog";
import { ALL_BRANCHES } from "@/services/api/branchContext";
import { useAuthStore } from "@/store/authStore";
import { useBranchStore } from "@/store/branchStore";
import { cn } from "@/utils/cn";
import { branchSwitchWarning, discardBranchBoundWork } from "./branchSwitchGuard";

/** Label for the active branch scope, shown wherever an operation could land in the wrong branch. */
export function activeBranchLabel(activeBranchId: string | null, branches: { id: string; name: string }[], fallback?: string | null) {
  if (activeBranchId === ALL_BRANCHES) return "All branches";
  return branches.find((b) => b.id === activeBranchId)?.name ?? fallback ?? "No branch";
}

/**
 * Global branch switcher (header). Lists only the branches the backend returned for this user;
 * "All branches" appears only when the user can see every branch. The API re-checks every
 * selection, so this is a usability control, never the security boundary.
 */
export function BranchSwitcher({ className }: { className?: string }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const fallbackName = useAuthStore((s) => s.user?.branch?.name ?? null);
  const { branches, activeBranchId, coversAll, loaded, loading, loadBranches, setActiveBranch } = useBranchStore();

  useEffect(() => {
    if (isAuthenticated && !loaded && !loading) void loadBranches();
  }, [isAuthenticated, loaded, loading, loadBranches]);

  if (!isAuthenticated || (!branches.length && !fallbackName)) return null;
  const label = activeBranchLabel(activeBranchId, branches, fallbackName);
  const isAll = activeBranchId === ALL_BRANCHES;

  const change = async (value: string) => {
    if (value === activeBranchId) return;
    const warning = branchSwitchWarning();
    if (warning) {
      if (!(await appDialog.confirm(warning, { title: "Switch branch?", confirmLabel: "Switch branch", tone: "danger" }))) return;
      discardBranchBoundWork();
    }
    setActiveBranch(value);
  };

  if (branches.length <= 1) {
    return (
      <div
        className={cn("hidden items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm md:flex", className)}
        data-testid="active-branch"
      >
        <Building2 className="h-3.5 w-3.5 text-primary" />
        <span className="hidden text-muted-foreground xl:inline">Branch</span>
        <span className="max-w-[140px] truncate font-medium text-foreground xl:max-w-none">{label}</span>
      </div>
    );
  }

  return (
    <Select value={activeBranchId ?? undefined} onValueChange={(v) => void change(v)}>
      <SelectTrigger
        aria-label="Active branch"
        data-testid="active-branch"
        className={cn(
          "h-9 w-auto min-w-[150px] gap-2 rounded-xl text-sm",
          isAll ? "border-warning/50 bg-warning/10" : "border-border",
          className
        )}
      >
        {isAll ? <Layers className="h-3.5 w-3.5 text-warning" /> : <Building2 className="h-3.5 w-3.5 text-primary" />}
        <span className="hidden text-muted-foreground xl:inline">Branch</span>
        <span className="max-w-[140px] truncate font-medium text-foreground">{label}</span>
      </SelectTrigger>
      <SelectContent>
        {coversAll && <SelectItem value={ALL_BRANCHES}>All branches (consolidated)</SelectItem>}
        {branches.map((b) => (
          <SelectItem key={b.id} value={b.id}>
            {b.name}
            {b.is_manager ? " · manager" : ""}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
