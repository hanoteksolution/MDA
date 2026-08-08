import { useCallback, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/** Pure URL → tab mapping (also used by unit tests). */
export function tabFromWorkspacePath<T extends string>(
  pathname: string,
  workspaceRoot: string,
  suffixToTab: Record<string, T>,
  defaultTab: T
): T {
  const root = workspaceRoot.replace(/\/+$/, "") || "/";
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === root || path === `${root}/dashboard`) return defaultTab;
  if (!path.startsWith(`${root}/`)) return defaultTab;
  const suffix = path.slice(root.length + 1);
  return suffixToTab[suffix] ?? defaultTab;
}

/**
 * Syncs industry mega-page tabs to workspace URLs.
 * `/gym/classes` → tab "classes"; clicking Attendance → `/gym/attendance`.
 */
export function useWorkspaceTab<T extends string>(
  workspaceRoot: string,
  suffixToTab: Record<string, T>,
  defaultTab: T
): [T, (tab: T) => void] {
  const location = useLocation();
  const navigate = useNavigate();
  const root = workspaceRoot.replace(/\/+$/, "") || "/";

  const tab = useMemo(
    () => tabFromWorkspacePath(location.pathname, workspaceRoot, suffixToTab, defaultTab),
    [location.pathname, workspaceRoot, suffixToTab, defaultTab]
  );

  const setTab = useCallback(
    (next: T) => {
      const suffix = Object.entries(suffixToTab).find(([, value]) => value === next)?.[0] ?? "";
      const to = suffix ? `${root}/${suffix}` : root;
      const current = location.pathname.replace(/\/+$/, "") || "/";
      if (current !== to) navigate(to);
    },
    [suffixToTab, root, navigate, location.pathname]
  );

  return [tab, setTab];
}
