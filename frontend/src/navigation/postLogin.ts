import type { User } from "@/types/models";
import { MODULE_WORKSPACES, type ModuleWorkspace } from "./moduleWorkspaces";

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

function hasAnyPermission(
  w: ModuleWorkspace,
  hasPermission: PermFn,
  elevated: boolean
): boolean {
  if (elevated) return true;
  if (!w.permission) return true;
  const codes = Array.isArray(w.permission) ? w.permission : [w.permission];
  return codes.some((c) => hasPermission(c));
}

function hasModuleAccess(
  w: ModuleWorkspace,
  enabled: string[] | undefined,
  elevated: boolean
): boolean {
  if (!w.modules.length) return true;
  if (elevated || enabled == null) return true;
  return w.modules.some((m) => enabled.includes(m));
}

export function hubWorkspacesForUser(
  user: User | null | undefined,
  hasPermission: PermFn = (code) => Boolean(user?.permissions?.includes(code))
): ModuleWorkspace[] {
  const elevated = isElevatedUser(user);
  const enabled = user?.enabled_modules;
  return MODULE_WORKSPACES.filter(
    (w) => hasAnyPermission(w, hasPermission, elevated) && hasModuleAccess(w, enabled, elevated)
  );
}

/** Super admin or 2+ modules → hub. Single module → that dashboard. */
export function postLoginPath(
  user: User | null | undefined,
  hasPermission?: PermFn
): string {
  const cards = hubWorkspacesForUser(user, hasPermission);
  if (isElevatedUser(user) || cards.length > 1) return "/modules";
  if (cards.length === 1) return cards[0].route;
  return "/dashboard";
}

export function shouldShowModuleHub(
  user: User | null | undefined,
  hasPermission?: PermFn
): boolean {
  return postLoginPath(user, hasPermission) === "/modules";
}
