import { useCallback, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useUIStore } from "@/store/uiStore";
import { isIndustryPath, workspacePath } from "@/navigation/businessWorkspaces";
import { workspaceFromPath } from "@/theme/workspaceBrand";

const SCOPED_PREFIXES = [
  "/products",
  "/categories",
  "/inventory",
  "/sales",
  "/customers",
  "/purchases",
  "/suppliers",
  "/pos",
  "/finance",
  "/reports",
  "/settings",
  "/medicines",
] as const;

function isSharedEnginePath(path: string): boolean {
  return SCOPED_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

/** Resolve the industry workspace that should own shared-engine navigation. */
export function resolveIndustryScope(pathname: string, activeWorkspace: string): string | null {
  const fromPath = workspaceFromPath(pathname);
  if (isIndustryPath(fromPath)) return fromPath!;
  if (isIndustryPath(activeWorkspace)) return activeWorkspace;
  return null;
}

/** Prefix a shared engine path with the active industry workspace when applicable. */
export function scopePath(path: string, workspace: string | null | undefined): string {
  if (!workspace || !isIndustryPath(workspace)) return path;
  if (!path.startsWith("/")) return path;

  const qIndex = path.search(/[?#]/);
  const pathname = qIndex >= 0 ? path.slice(0, qIndex) : path;
  const suffix = qIndex >= 0 ? path.slice(qIndex) : "";

  if (pathname === `/${workspace}` || pathname.startsWith(`/${workspace}/`)) return path;
  if (!isSharedEnginePath(pathname)) return path;
  // Industry sidebars use /{ws}/purchasing for the PO list
  const normalized =
    pathname === "/purchases" || pathname === "/purchases/"
      ? "/purchasing"
      : pathname;
  return workspacePath(workspace, normalized.replace(/^\//, "")) + suffix;
}

/** Hook: build links that stay inside the current industry workspace. */
export function useScopedPath() {
  const location = useLocation();
  const activeWorkspace = useUIStore((s) => s.activeWorkspace);

  const scope = useMemo(
    () => resolveIndustryScope(location.pathname, activeWorkspace),
    [location.pathname, activeWorkspace]
  );

  const scoped = useCallback((path: string) => scopePath(path, scope), [scope]);

  return { scope, scoped, isIndustry: Boolean(scope) };
}
