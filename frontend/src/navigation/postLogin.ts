import type { User } from "@/types/models";
import { filterVisibleWorkspaces, type ModuleWorkspace } from "./moduleWorkspaces";

type PermFn = (code: string) => boolean;

export function isElevatedUser(user: User | null | undefined): boolean {
  return Boolean(
    user?.is_super_admin ||
      user?.is_platform_admin ||
      user?.is_superuser ||
      user?.role?.slug === "super_admin" ||
      user?.role?.slug === "platform_admin"
  );
}

/** Industry + platform workspaces for the hub (no POS/Sales/Inventory peers). */
export function hubWorkspacesForUser(
  user: User | null | undefined,
  hasPermission: PermFn = (code) => Boolean(user?.permissions?.includes(code))
): ModuleWorkspace[] {
  const elevated = isElevatedUser(user);
  return filterVisibleWorkspaces(user?.enabled_modules, {
    elevated,
    hasPermission,
    includeOverview: false,
    includeFinance: elevated || hasPermission("finance.view"),
    businessTypeCode: user?.business_type_code,
  });
}

export function industryWorkspacesForUser(
  user: User | null | undefined,
  hasPermission: PermFn = (code) => Boolean(user?.permissions?.includes(code))
): ModuleWorkspace[] {
  return hubWorkspacesForUser(user, hasPermission).filter((w) => w.kind === "industry");
}

/** Prefer the operational home inside Retail for engine-only staff. */
function retailLandingPath(perm: PermFn): string {
  const hasPos = perm("pos.access");
  const hasInv = perm("inventory.view");
  const hasSales = perm("sales.view");
  const hasDash = perm("dashboard.view");
  if (hasPos && !hasInv && !hasDash) return "/retail/pos";
  if (hasInv && !hasPos) return "/retail/inventory";
  if (hasSales && !hasPos && !hasInv) return "/retail/sales";
  return "/retail";
}

/** Super admin or 2+ industry workspaces → hub. Single vertical → that dashboard. */
export function postLoginPath(
  user: User | null | undefined,
  hasPermission?: PermFn
): string {
  const perm = hasPermission ?? ((code: string) => Boolean(user?.permissions?.includes(code)));
  const industries = industryWorkspacesForUser(user, perm);
  if (isElevatedUser(user) || industries.length > 1) return "/modules";
  if (industries.length === 1) {
    const only = industries[0];
    if (only.code === "retail") return retailLandingPath(perm);
    return only.route;
  }
  // No industry card: land on bare engines before reports/dashboard dead-ends.
  if (perm("pos.access")) return "/pos";
  if (perm("inventory.view")) return "/inventory";
  if (perm("sales.view")) return "/sales";
  const cards = hubWorkspacesForUser(user, perm).filter((w) => w.code !== "reports");
  if (cards.length === 1) return cards[0].route;
  if (perm("reports.view")) return "/reports";
  return "/dashboard";
}

export function shouldShowModuleHub(
  user: User | null | undefined,
  hasPermission?: PermFn
): boolean {
  return postLoginPath(user, hasPermission) === "/modules";
}
